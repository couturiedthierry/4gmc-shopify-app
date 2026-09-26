import os
import json
import unittest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from server import app, DRY_RUN

client = TestClient(app)

from PIL import Image
import io
def create_mock_image(format='JPEG', size=(100, 100)):
    img = Image.new('RGB', size, color='red')
    b = io.BytesIO()
    img.save(b, format=format)
    return b.getvalue()

class TestIntegration(unittest.TestCase):
    @patch('server.ACTIVE_STORE_ID')
    @patch('server.require')
    def test_upload_invalid_format(self, mock_require, mock_store_id):
        mock_store_id.get.return_value = 1
        res = client.put('/api/products/1/image', files={'image': ('test.txt', b'not an image', 'text/plain')})
        self.assertEqual(res.status_code, 400)
        self.assertIn('Invalid image format', res.json().get('detail', res.text))

    @patch('server.ACTIVE_STORE_ID')
    @patch('server.require')
    def test_upload_oversized(self, mock_require, mock_store_id):
        mock_store_id.get.return_value = 1
        content = create_mock_image('JPEG', (5000, 5000))
        res = client.put('/api/products/1/image', files={'image': ('test.jpg', content, 'image/jpeg')})
        self.assertEqual(res.status_code, 400)
        self.assertIn('Image dimensions too large', res.json().get('detail', res.text))

    @patch('server.ACTIVE_STORE_ID')
    @patch('server.require')
    @patch('server.db')
    def test_upload_ownership(self, mock_db, mock_require, mock_store_id):
        mock_store_id.get.return_value = 2 # product is in store 1
        mock_c = MagicMock()
        mock_c.execute.return_value.fetchone.return_value = None
        mock_db.return_value.__enter__.return_value = mock_c
        
        content = create_mock_image('JPEG', (100, 100))
        res = client.put('/api/products/1/image', files={'image': ('test.jpg', content, 'image/jpeg')})
        self.assertEqual(res.status_code, 404)

    @patch('server.ACTIVE_STORE_ID')
    @patch('server.require')
    @patch('server.db')
    def test_publish_gate(self, mock_db, mock_require, mock_store_id):
        mock_store_id.get.return_value = 1
        mock_c = MagicMock()
        def mock_execute(*args):
            mock_cursor = MagicMock()
            if 'stores' in args[0]: mock_cursor.fetchone.return_value = {'shopify_token': 'token', 'domain': 'test.com'}
            elif 'pages' in args[0]: mock_cursor.__iter__.return_value = [{'title': 'FAQ', 'kind': 'page'}]
            else: mock_cursor.__iter__.return_value = []
            return mock_cursor
        mock_c.execute.side_effect = mock_execute
        mock_db.return_value.__enter__.return_value = mock_c
        
        res = client.post('/api/store/publish')
        self.assertEqual(res.status_code, 400)
        self.assertIn('Legal Notice', res.json().get('detail', res.text))

    @patch('server.ACTIVE_STORE_ID')
    @patch('server.require')
    @patch('server.db')
    @patch('server.DRY_RUN', False)
    @patch('server.shopify_graphql')
    @patch('server.shopify_rest')
    @patch('httpx.AsyncClient.post')
    @patch('builtins.open', new_callable=MagicMock)
    def test_publish_live_mocked(self, mock_open, mock_httpx_post, mock_rest, mock_gql, mock_db, mock_require, mock_store_id):
        mock_store_id.get.return_value = 1
        mock_c = MagicMock()
        
        def mock_execute(*args):
            mock_cursor = MagicMock()
            if 'stores' in args[0]: mock_cursor.fetchone.return_value = {'shopify_token': 'token', 'domain': 'test.com'}
            elif 'pages' in args[0]: 
                # Provide 12 distinct pages and 3 distinct legal settings to pass gate
                mock_cursor.__iter__.return_value = [
                    {'title': 'Legal Notice', 'kind': 'page'},
                    {'title': 'Privacy Policy', 'kind': 'page'},
                    {'title': 'Payment Policy', 'kind': 'page'},
                    {'title': 'Shipping Policy', 'kind': 'page'},
                    {'title': 'Terms of Service', 'kind': 'page'},
                    {'title': 'Refund and Return Policy', 'kind': 'page'},
                    {'title': 'Order Cancellation Policy', 'kind': 'page'},
                    {'title': 'FAQ', 'kind': 'page'},
                    {'title': 'About Us', 'kind': 'page'},
                    {'title': 'Track Order', 'kind': 'page'},
                    {'title': 'Contact Us', 'kind': 'page'},
                    {'title': 'Warranty Policy', 'kind': 'page'},
                    {'title': 'Contact Information', 'kind': 'legal_setting'},
                    {'title': 'Legal Notice', 'kind': 'legal_setting'},
                    {'title': 'Terms of Sale', 'kind': 'legal_setting'}
                ]
            elif 'products' in args[0]:
                mock_cursor.__iter__.return_value = [
                    {'id': 1, 'images': json.dumps(['/data/product-images/1_123.jpg']), 'shopify_id': 'gid://shopify/Product/123'}
                ]
            return mock_cursor
            
        mock_c.execute.side_effect = mock_execute
        mock_db.return_value.__enter__.return_value = mock_c
        
        async def mock_gql_side_effect(domain, token, query, variables=None):
            if 'stagedUploadsCreate' in query:
                return {'data': {'stagedUploadsCreate': {'stagedTargets': [{'url': 'http://up', 'resourceUrl': 'http://res', 'parameters': []}], 'userErrors': []}}}
            if 'productUpdate' in query:
                return {'data': {'productUpdate': {'product': {'id': '1'}, 'userErrors': []}}}
            if 'themes' in query:
                return {'data': {'themes': {'edges': [{'node': {'id': 'gid://1', 'name': 'Dawn', 'role': 'MAIN'}}]}}}
            if 'shop' in query:
                return {'data': {'shop': {'plan': {'displayName': 'Shopify Plus', 'partnerDevelopment': False}}}}
            return {}
        mock_gql.side_effect = mock_gql_side_effect
        
        async def mock_rest_side_effect(domain, token, method, path, data=None):
            if 'themes.json' in path:
                return {'theme': {'id': 999}}
            return {}
        mock_rest.side_effect = mock_rest_side_effect
        
        async def async_mock_post(*args, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            return mock_resp
        mock_httpx_post.side_effect = async_mock_post
        
        with patch('server.FERNET') as mock_fernet:
            mock_fernet.decrypt.return_value = b'decrypted'
            res = client.post('/api/store/publish')
            
        self.assertEqual(res.status_code, 200, res.text)
        logs = res.json()['logs']
        logs_str = "\\n".join(logs)
        self.assertIn('Executing checkoutBrandingUpsert', logs_str)
        self.assertIn('Duplicating main theme', logs_str)
        self.assertIn('Uploaded file bytes', logs_str)

if __name__ == '__main__':
    unittest.main()
