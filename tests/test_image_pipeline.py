import asyncio
import base64
import json
import sys
import tempfile
import hashlib
from pathlib import Path
from PIL import Image
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import image_pipeline
import server


async def check_pipeline():
    png = b'\x89PNG\r\n\x1a\n' + b'test-pixels'
    calls = []

    def respond(request):
        calls.append(request)
        if request.method == 'GET':
            assert request.url.host == 'cdn.example.com'
            return httpx.Response(200, content=png, headers={'content-type': 'image/png'})
        if request.url.host == 'generativelanguage.googleapis.com':
            assert request.headers['x-goog-api-key'] == 'test-gemini-key'
            body = json.loads(request.content)
            assert body['generationConfig']['responseModalities'] == ['IMAGE']
            assert '#9b1c58' in body['contents'][0]['parts'][0]['text']
            assert '#ffc3da' in body['contents'][0]['parts'][0]['text']
            assert body['contents'][0]['parts'][1]['inline_data']['data'] == base64.b64encode(png).decode()
            return httpx.Response(200, json={'candidates': [{'content': {'parts': [
                {'text': 'Here is the image'},
                {'inlineData': {'mimeType': 'image/png', 'data': base64.b64encode(png).decode()}},
            ]}}]})
        assert request.url.path == '/admin/api/2024-01/products/123/images.json'
        assert request.headers['x-shopify-access-token'] == 'test-shopify-token'
        payload = json.loads(request.content)
        assert payload['image']['filename'] == 'ai-mockup.png'
        assert bool(payload['image']['attachment'])
        return httpx.Response(201, json={'image': {'id': 456, 'product_id': 123, 'src': 'https://cdn.shopify.com/ai.png'}})

    with patch.object(image_pipeline.socket, 'getaddrinfo', return_value=[(0, 0, 0, '', ('1.1.1.1', 443))]):
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            result = await image_pipeline.generate_and_attach_image(
                gemini_key='test-gemini-key',
                shopify_domain='merchant.myshopify.com',
                shopify_token='test-shopify-token',
                product_gid='gid://shopify/Product/123',
                source_image_url='https://cdn.example.com/item.png',
                product_title='Example item',
                store_name='My Store',
                primary_color='#9b1c58', accent_color='#ffc3da',
                client=client,
            )
    assert result['image_id'] == '456'
    assert [call.method for call in calls] == ['GET', 'POST', 'POST']


async def check_saved_image():
    with tempfile.TemporaryDirectory() as temp:
        old_db = server.DB
        server.DB = Path(temp) / 'test.db'
        try:
            server.init()
            logo_dir = server.brand_asset_directory()
            logo_dir.mkdir(parents=True, exist_ok=True)
            logo_path = logo_dir / 'logo.png'
            Image.new('RGBA', (120, 32), (20, 60, 220, 255)).save(logo_path, format='PNG')
            logo_bytes = logo_path.read_bytes()
            with server.db() as c:
                brand = {'color': '#2251dc', 'accent': '#6f9cff', 'logo': {
                    'filename': 'logo.png', 'extension': 'png', 'content_type': 'image/png',
                    'digest': hashlib.sha256(logo_bytes).hexdigest(), 'size': len(logo_bytes)}}
                c.execute("UPDATE stores SET name='My Store',domain='merchant.myshopify.com',brand=? WHERE id=1", (json.dumps(brand),))
                product_id = c.execute(
                    "INSERT INTO products(store_id,source_url,source_title,title,images,shopify_id) VALUES(1,?,?,?,?,?)",
                    ('https://source.example/products/item', 'Example item', 'My Store Example item',
                     json.dumps(['https://cdn.example.com/item.png']), 'gid://shopify/Product/123'),
                ).lastrowid
            client = TestClient(server.app)
            assert client.post('/api/login', json={'password': server.ADMIN_PASSWORD}).status_code == 200
            cookie = client.cookies.get('gmc_session')
            request = Request({'type': 'http', 'method': 'POST',
                               'headers': [(b'cookie', f'gmc_session={cookie}'.encode())]})
            attempts = []

            async def token(_store):
                return 'test-shopify-token'

            async def generate(**kwargs):
                attempts.append(kwargs)
                return [
                    {'image_id': '456', 'product_id': '123', 'src': 'https://cdn.shopify.com/hero.png', 'role': 'hero', 'corner_logo': True},
                    {'image_id': '457', 'product_id': '123', 'src': 'https://cdn.shopify.com/detail.png', 'role': 'detail', 'corner_logo': True},
                    {'image_id': '458', 'product_id': '123', 'src': 'https://cdn.shopify.com/lifestyle.png', 'role': 'lifestyle', 'corner_logo': True},
                ]

            with patch.object(server, 'token_for', token), \
                 patch.object(server.image_pipeline, 'generate_and_attach_images', generate):
                first = await server.attach_generated_product_image(product_id, request)
                second = await server.attach_generated_product_image(product_id, request)
            assert first['already_attached'] is False
            assert second['already_attached'] is True
            assert len(attempts) == 1
            with server.db() as c:
                row = c.execute('SELECT ai_image_id,ai_image_digest,ai_image_manifest FROM products WHERE id=?', (product_id,)).fetchone()
                assert row['ai_image_id'] == '456' and row['ai_image_digest']
                assert [item['role'] for item in json.loads(row['ai_image_manifest'])] == ['hero', 'detail', 'lifestyle']
                c.execute("UPDATE stores SET product_source_url='https://source.example' WHERE id=1")
                c.execute("UPDATE products SET description=?,price='12.00',status='draft' WHERE id=?",
                          ('A real product description with enough source-supported detail to publish.', product_id))
            order = []

            async def imported(_data, _request):
                return {'id': product_id}

            async def prepared(_id, _request):
                order.append('copy')

            async def uploaded(_id, _request):
                order.append('upload')

            async def attached(_id, _request):
                order.append('image')

            async def published(_id, _request):
                order.append('publish')
                return {'status': 'published', 'url': 'https://merchant.myshopify.com/products/item'}

            with patch.object(server, 'token_for', token),                  patch.object(server, 'import_product', imported),                  patch.object(server, 'prepare_product', prepared),                  patch.object(server, 'upload_product', uploaded),                  patch.object(server, 'attach_generated_product_image', attached),                  patch.object(server, 'publish_source_product', published):
                response = client.post('/api/products/auto-publish',
                                       json={'url': 'https://source.example/products/item'})
            assert response.status_code == 200, response.text
            assert order == ['copy', 'upload', 'image', 'publish']
        finally:
            server.DB = old_db


asyncio.run(check_pipeline())
asyncio.run(check_saved_image())
print('Gemini-to-Shopify attachment checks passed')
