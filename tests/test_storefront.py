import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


with tempfile.TemporaryDirectory() as temp:
    previous_db = server.DB
    server.DB = Path(temp) / 'test.db'
    try:
        server.init()
        business = {
            'business_name': 'Example Store', 'domain_name': 'example-store.com',
            'email': 'hello@example-store.com', 'address': '123 Main St, New York, NY',
            'country': 'United States', 'currency': 'USD', 'phone': '+1 212 555 0100',
            'live_chat': 'Available on the website during business hours',
            'business_hours': 'Mon-Fri: 9:00 AM - 5:00 PM (Eastern Time)',
            'shipping_cost': 'Free shipping in the United States (USD 0.00)',
        }
        with server.db() as c:
            brand = c.execute('SELECT brand FROM stores WHERE id=1').fetchone()['brand']
            c.execute('UPDATE stores SET name=?,domain=?,business=?,policy_source_url=?,product_source_url=?,'
                      'site_kit_facts_hash=?,shopify_token=?,shopify_refresh_token=?,shopify_expires_at=?,'
                      'shopify_refresh_expires_at=?,shopify_scopes=? WHERE id=1', (
                          'Example Store', 'example-test.myshopify.com', json.dumps(business),
                          'https://source.example', 'https://source.example',
                          server.business_identity_hash(business),
                          server.FERNET.encrypt(b'test-access').decode(),
                          server.FERNET.encrypt(b'test-refresh').decode(),
                          int(time.time()+3600), int(time.time()+7200), server.SHOPIFY_SCOPES,
                      ))
            page_ids = []
            for kind in server.SITE_KIT_ORDER:
                body = 'Example Store details and customer support information. ' * 3
                if kind == 'contact':
                    body += '\nhello@example-store.com\n123 Main St, New York, NY\n+1 212 555 0100'
                title = server.SITE_KIT_TITLES[kind]
                guard = json.dumps({
                    'version': 2, 'identity_hash': server.business_identity_hash(business),
                    'content_hash': server.guarded_page_hash(title, body),
                    'source_host': 'source.example',
                    'source_digest': hashlib.sha256(('source ' + kind).encode()).hexdigest(),
                })
                page_ids.append(c.execute(
                    'INSERT INTO pages(store_id,kind,title,body,status,shopify_id,source_url,source_handle,brand_guard) '
                    'VALUES(1,?,?,?,?,?,?,?,?)',
                    (kind, title, body, 'published', 'gid://shopify/Page/1',
                     'https://source.example/' + kind, kind, guard),
                ).lastrowid)
            c.execute('UPDATE stores SET site_kit_page_ids=? WHERE id=1', (json.dumps(page_ids),))
            image_values = ['https://cdn.example.com/item.jpg']
            images = json.dumps(image_values)
            product_title = 'Example Store Item'
            source_data = {'title': 'Item', 'product_type': 'Featured Products',
                           'images': image_values,
                           'variants': [{'id': 1, 'title': 'Default', 'available': True}]}
            gmc = server.catalog_rules.product_gmc_data(
                source_data, 'Example Store', 'https://source.example/products/item')
            manifest = [
                {'role': 'hero', 'corner_logo': True, 'image_id': '12', 'src': 'https://cdn.shopify.com/ai-blue.png'},
                {'role': 'detail', 'corner_logo': True, 'image_id': '13', 'src': 'https://cdn.shopify.com/ai-detail.png'},
                {'role': 'lifestyle', 'corner_logo': True, 'image_id': '14', 'src': 'https://cdn.shopify.com/ai-life.png'},
            ]
            digest = hashlib.sha256(json.dumps([
                product_title, 'Item', image_values[:3],
                server.catalog_rules.brand_fingerprint('Example Store', json.loads(brand)),
                gmc['rules_version']], ensure_ascii=False).encode()).hexdigest()
            c.execute('INSERT INTO collections(store_id,title,handle,shopify_id,status) VALUES(1,?,?,?,?)',
                      ('Featured Products', 'featured-products', 'gid://shopify/Collection/2', 'published'))
            product_id = c.execute(
                'INSERT INTO products(store_id,source_url,source_title,title,description,price,sku,gtin,images,source_data,status,'
                'shopify_id,ai_image_id,ai_image_digest,ai_image_url,ai_image_manifest,gmc_data,collection_title,shopify_collection_id,inventory_tracked) '
                'VALUES(1,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                ('https://source.example/products/item', 'Item', product_title,
                 'A factual product description with sufficient detail for publication.', '12.00',
                 gmc['sku'], gmc['gtin'], images, json.dumps(source_data), 'published',
                 'gid://shopify/Product/1', '12', digest, 'https://cdn.shopify.com/ai-blue.png',
                 json.dumps(manifest), json.dumps(gmc), 'Featured Products',
                 'gid://shopify/Collection/2', 0),
            ).lastrowid
        client = TestClient(server.app)
        assert client.post('/api/login', json={'password': server.ADMIN_PASSWORD}).status_code == 200
        assert client.get('/api/state').json()['storefront'] is None

        async def copy(_prompt, max_tokens=700):
            assert max_tokens == 350
            return {'headline': 'Welcome to Example Store', 'intro': 'Discover our available products.'}

        with patch.object(server, 'ai_json', copy):
            response = client.post('/api/storefront/generate')
        assert response.status_code == 200, response.text
        snapshot = client.get('/api/state').json()['storefront']
        assert len(snapshot['pages']) == 10 and len(snapshot['products']) == 1
        assert snapshot['products'][0]['image_url'] == 'https://cdn.shopify.com/ai-blue.png'
        assert any(page['kind'] == 'contact' and 'hello@example-store.com' in page['body']
                   for page in snapshot['pages'])

        current = client.get('/api/state').json()['store']
        revised_brand = {'color': '#9b1c58', 'accent': '#ffc3da'}
        response = client.put('/api/store', json={'name': current['name'], 'domain': current['domain'],
                                                   'business': current['business'], 'brand': revised_brand})
        assert response.status_code == 200, response.text
        after = client.get('/api/state').json()
        assert after['storefront'] is None
        assert all(page['status'] == 'published' for page in after['pages'])
        assert after['products'][0]['status'] == 'published'
        with patch.object(server, 'ai_json', copy):
            assert client.post('/api/storefront/generate').status_code == 400

        with server.db() as c:
            brand = c.execute('SELECT brand FROM stores WHERE id=1').fetchone()['brand']
            gmc = json.loads(c.execute('SELECT gmc_data FROM products WHERE id=?', (product_id,)).fetchone()['gmc_data'])
            digest = hashlib.sha256(json.dumps([
                product_title, 'Item', ['https://cdn.example.com/item.jpg'],
                server.catalog_rules.brand_fingerprint('Example Store', json.loads(brand)),
                gmc['rules_version']], ensure_ascii=False).encode()).hexdigest()
            c.execute('UPDATE products SET ai_image_digest=?,ai_image_url=? WHERE id=?',
                      (digest, 'https://cdn.shopify.com/ai-pink.png', product_id))
        with patch.object(server, 'ai_json', copy):
            assert client.post('/api/storefront/generate').status_code == 200
        regenerated = client.get('/api/state').json()['storefront']
        assert regenerated['brand'] == revised_brand
        assert regenerated['products'][0]['image_url'].endswith('ai-pink.png')
    finally:
        server.DB = previous_db

print('Complete storefront generation checks passed')
