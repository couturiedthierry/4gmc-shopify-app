import asyncio
import base64
import json
import sys
import tempfile
from pathlib import Path
from io import BytesIO
from unittest.mock import patch

import httpx
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import catalog_rules
import image_pipeline
import server


def product(index, category, *, title=None, available=True, quantity=None):
    variant = {'id': index, 'title': 'Default', 'available': available, 'sku': f'SOURCE-{index}'}
    if quantity is not None:
        variant['inventory_quantity'] = quantity
    return {
        'title': title or f'Physical item {index}',
        'product_type': category,
        'description': 'Verified physical product facts ' * 8,
        'images': [f'https://cdn.example.com/{index}-{n}.jpg' for n in range(4)],
        'variants': [dict(variant, available=False), variant],
        '_4gmc_url': f'https://source.example/products/item-{index}',
    }


items = [product(i, f'Category {i % 5}') for i in range(28)]
items.append(product(99, 'Services', title='Gift Card'))
curated = catalog_rules.curate_catalog(items)
assert len(curated) == 20
assert len({item['_4gmc_category'] for item in curated}) <= 4
assert all(len(item['_4gmc_variant']) and item['_4gmc_variant']['available'] for item in curated)
assert all('gift card' not in item['title'].casefold() for item in curated)

assert catalog_rules.valid_gtin('4006381333931')
assert not catalog_rules.valid_gtin('4006381333932')
source = product(1, 'Dog Walking Gear', quantity=7)
source['vendor'] = 'Other maker'
source['variants'][1]['barcode'] = '4006381333931'
gmc = catalog_rules.product_gmc_data(source, 'Zyplan', source['_4gmc_url'])
assert gmc['gtin'] == ''
assert gmc['source_gtin_candidate'] == '4006381333931'
assert gmc['source_gtin_candidate_valid'] is True
assert gmc['brand'] == 'Zyplan' and gmc['mpn'].startswith('ZYPLAN-')
assert gmc['identifier_exists'] is True and gmc['inventory_quantity'] == 7
assert gmc['inventory_tracked'] is True and gmc['availability'] == 'in_stock'
assert catalog_rules.validate_gmc_data(gmc) == []
same_brand = dict(source, vendor='Zyplan')
verified = catalog_rules.product_gmc_data(same_brand, 'Zyplan', source['_4gmc_url'])
assert verified['gtin'] == '4006381333931' and verified['mpn'] == ''


async def image_gallery_check():
    generated_io = BytesIO()
    Image.new('RGB', (512, 512), '#d8dde8').save(generated_io, format='PNG')
    png = generated_io.getvalue()
    logo_io = BytesIO()
    Image.new('RGBA', (160, 40), (210, 20, 50, 255)).save(logo_io, format='PNG')
    logo = logo_io.getvalue()
    prompts, uploads, uploaded_images = [], [], []

    def respond(request):
        if request.method == 'GET':
            if request.url.host == 'cdn.example.com':
                return httpx.Response(200, content=png, headers={'content-type': 'image/png'})
            if request.url.host == 'merchant.myshopify.com':
                return httpx.Response(200, json={'images': []})
        if request.url.host == 'generativelanguage.googleapis.com':
            body = json.loads(request.content)
            prompts.append(body['contents'][0]['parts'][0]['text'])
            return httpx.Response(200, json={'candidates': [{'content': {'parts': [
                {'inlineData': {'mimeType': 'image/png', 'data': base64.b64encode(png).decode()}}
            ]}}]})
        payload = json.loads(request.content)['image']
        uploads.append(payload['filename'])
        uploaded_images.append(base64.b64decode(payload['attachment']))
        number = len(uploads)
        return httpx.Response(201, json={'image': {'id': 500 + number, 'product_id': 123,
                                                   'src': f'https://cdn.shopify.com/{number}.png'}})

    with patch.object(image_pipeline.socket, 'getaddrinfo', return_value=[(0, 0, 0, '', ('1.1.1.1', 443))]):
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            result = await image_pipeline.generate_and_attach_images(
                gemini_key='test', shopify_domain='merchant.myshopify.com',
                shopify_token='token', product_gid='gid://shopify/Product/123',
                source_image_urls=['https://cdn.example.com/item.png'],
                product_title='Zyplan Product', source_title='Supplier Product',
                store_name='Zyplan', primary_color='#211b1a', accent_color='#ff6753',
                product_facts='Waterproof strap and metal clasp.',
                logo_mime='image/png', logo_bytes=logo, client=client)
    assert [item['role'] for item in result] == ['hero', 'detail', 'lifestyle']
    assert all(item['corner_logo'] is True for item in result)
    assert uploads == ['4gmc-hero.png', '4gmc-detail.png', '4gmc-lifestyle.png']
    assert len(prompts) >= 1
    assert any('photograph' in prompt.lower() or 'mower' in prompt.lower() for prompt in prompts)
    assert all('supplier marks' in prompt.lower() or 'no other logo' in prompt.lower() or 'watermark' in prompt.lower() for prompt in prompts)
    for uploaded in uploaded_images:
        with Image.open(BytesIO(uploaded)) as branded:
            assert branded.size == (512, 512)
            # Red logo pixels must exist inside the top-left badge area.
            crop = branded.crop((0, 0, 210, 100)).convert('RGB')
            assert any(r > 170 and g < 70 and b < 90 for r, g, b in crop.getdata())


async def inventory_check():
    calls = []

    async def graph(domain, token, query, variables=None):
        calls.append((query, variables))
        if 'inventoryLevels(first:50)' in query:
            return {'productByIdentifier': {'variants': {'nodes': [{
                'id': 'gid://shopify/ProductVariant/1',
                'inventoryItem': {'id': 'gid://shopify/InventoryItem/2', 'tracked': True,
                                  'inventoryLevels': {'nodes': [{
                                      'location': {'id': 'gid://shopify/Location/3', 'isActive': True},
                                      'quantities': [{'name': 'available', 'quantity': 2}],
                                  }]}}
            }]}}}
        if 'locations(first:20)' in query:
            return {'locations': {'nodes': [{'id': 'gid://shopify/Location/3', 'name': 'Main', 'isActive': True}]}}
        if 'inventorySetQuantities' in query:
            assert variables['input']['quantities'][0]['quantity'] == 7
            assert variables['input']['quantities'][0]['changeFromQuantity'] == 2
            return {'inventorySetQuantities': {'inventoryAdjustmentGroup': {'changes': []}, 'userErrors': []}}
        raise AssertionError(query)

    with patch.object(server, 'shopify_graphql', graph):
        await server.sync_product_inventory('merchant.myshopify.com', 'token',
                                            'gid://shopify/Product/1',
                                            {'inventory_tracked': 1, 'inventory_quantity': 7})
    assert any('inventorySetQuantities' in query for query, _ in calls)


asyncio.run(image_gallery_check())
asyncio.run(inventory_check())
print('Catalog curation, GMC identification, branded gallery, and inventory checks passed')
