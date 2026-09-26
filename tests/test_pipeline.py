import os
import json
import time
import hmac
import hashlib
import unittest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Load the app and config
from server import app, DRY_RUN, SESSION_SECRET

client = TestClient(app)

from PIL import Image
import io
def create_mock_image(format='JPEG', size=(100, 100)):
    img = Image.new('RGB', size, color='red')
    b = io.BytesIO()
    img.save(b, format=format)
    return b.getvalue()

def get_auth_cookies(store_id=1):
    stamp = str(int(time.time()) + 3600)
    signature = hmac.new(SESSION_SECRET.encode(), stamp.encode(), hashlib.sha256).hexdigest()
    cookie = f"{stamp}.{signature}"
    return {'gmc_session': cookie, 'gmc_store_id': str(store_id)}

class TestIntegration(unittest.TestCase):

    def test_upload_invalid_format(self):
        cookies = get_auth_cookies(1)
        res = client.put('/api/products/1/image', files={'image': ('test.txt', b'not an image', 'text/plain')}, cookies=cookies)
        self.assertEqual(res.status_code, 400)
        self.assertIn('Invalid image format', res.json().get('detail', res.text))

    def test_upload_oversized(self):
        cookies = get_auth_cookies(1)
        content = create_mock_image('JPEG', (5000, 5000))
        res = client.put('/api/products/1/image', files={'image': ('test.jpg', content, 'image/jpeg')}, cookies=cookies)
        self.assertEqual(res.status_code, 400)
        self.assertIn('Image dimensions too large', res.json().get('detail', res.text))

    @patch('server.db')
    def test_upload_ownership(self, mock_db):
        cookies = get_auth_cookies(2) # Auth as store 2, trying to upload to product 1
        mock_c = MagicMock()
        mock_c.execute.return_value.fetchone.return_value = None # Product not found for store 2
        mock_db.return_value.__enter__.return_value = mock_c
        
        content = create_mock_image('JPEG', (100, 100))
        res = client.put('/api/products/1/image', files={'image': ('test.jpg', content, 'image/jpeg')}, cookies=cookies)
        self.assertEqual(res.status_code, 404)

    @patch('server.db')
    def test_publish_gate(self, mock_db):
        cookies = get_auth_cookies(1)
        mock_c = MagicMock()
        def mock_execute(*args):
            mock_cursor = MagicMock()
            if 'stores' in args[0]: mock_cursor.fetchone.return_value = {'shopify_token': 'token', 'domain': 'test.com'}
            elif 'pages' in args[0]: mock_cursor.__iter__.return_value = [{'title': 'FAQ', 'kind': 'page'}] # Missing everything else
            else: mock_cursor.__iter__.return_value = []
            return mock_cursor
        mock_c.execute.side_effect = mock_execute
        mock_db.return_value.__enter__.return_value = mock_c
        
        res = client.post('/api/store/publish', cookies=cookies)
        self.assertEqual(res.status_code, 200) # Returns 200 with {'ok': False}
        data = res.json()
        self.assertFalse(data['ok'])
        self.assertIn('missing', data)
        self.assertIn('Page: Legal Notice', data['missing'])

    @patch('server.db')
    @patch('server.DRY_RUN', True)
    @patch('server.shopify_graphql')
    @patch('server.shopify_rest')
    @patch('httpx.AsyncClient.post')
    def test_publish_dry_run_zero_writes(self, mock_httpx_post, mock_rest, mock_gql, mock_db):
        cookies = get_auth_cookies(1)
        mock_c = MagicMock()
        
        def mock_execute(*args):
            mock_cursor = MagicMock()
            if 'stores' in args[0]: mock_cursor.fetchone.return_value = {'shopify_token': 'token', 'domain': 'test.com', 'logo_url': 'test.png'}
            elif 'pages' in args[0]: 
                mock_cursor.__iter__.return_value = [
                    {'title': 'Legal Notice', 'kind': 'page'}, {'title': 'Privacy Policy', 'kind': 'page'},
                    {'title': 'Payment Policy', 'kind': 'page'}, {'title': 'Shipping Policy', 'kind': 'page'},
                    {'title': 'Terms of Service', 'kind': 'page'}, {'title': 'Refund and Return Policy', 'kind': 'page'},
                    {'title': 'Order Cancellation Policy', 'kind': 'page'}, {'title': 'FAQ', 'kind': 'page'},
                    {'title': 'About Us', 'kind': 'page'}, {'title': 'Track Order', 'kind': 'page'},
                    {'title': 'Contact Us', 'kind': 'page'}, {'title': 'Warranty Policy', 'kind': 'page'},
                    {'title': 'Contact Information', 'kind': 'legal_setting'}, {'title': 'Legal Notice', 'kind': 'legal_setting'},
                    {'title': 'Terms of Sale', 'kind': 'legal_setting'}
                ]
            elif 'products' in args[0]:
                mock_cursor.__iter__.return_value = [
                    {'id': 1, 'images': json.dumps(['/data/product-images/1_123.jpg']), 'shopify_id': 'gid://shopify/Product/123'}
                ]
            return mock_cursor
            
        mock_c.execute.side_effect = mock_execute
        mock_db.return_value.__enter__.return_value = mock_c
        
        with patch('server.FERNET') as mock_fernet:
            mock_fernet.decrypt.return_value = b'decrypted'
            res = client.post('/api/store/publish', cookies=cookies)
            
        self.assertEqual(res.status_code, 200, res.text)
        self.assertTrue(res.json()['ok'])
        # Assert ZERO external writes occurred
        mock_httpx_post.assert_not_called()
        mock_gql.assert_not_called()
        mock_rest.assert_not_called()

    @patch('server.db')
    @patch('server.DRY_RUN', False)
    @patch('server.shopify_graphql')
    @patch('server.shopify_rest')
    @patch('httpx.AsyncClient.post')
    @patch('builtins.open', new_callable=MagicMock)
    def test_publish_live_mocked(self, mock_open, mock_httpx_post, mock_rest, mock_gql, mock_db):
        cookies = get_auth_cookies(1)
        mock_c = MagicMock()
        
        def mock_execute(*args):
            mock_cursor = MagicMock()
            if 'stores' in args[0]: mock_cursor.fetchone.return_value = {'shopify_token': 'token', 'domain': 'test.com', 'logo_url': 'test.png'}
            elif 'pages' in args[0]: 
                mock_cursor.__iter__.return_value = [
                    {'title': 'Legal Notice', 'kind': 'page'}, {'title': 'Privacy Policy', 'kind': 'page'},
                    {'title': 'Payment Policy', 'kind': 'page'}, {'title': 'Shipping Policy', 'kind': 'page'},
                    {'title': 'Terms of Service', 'kind': 'page'}, {'title': 'Refund and Return Policy', 'kind': 'page'},
                    {'title': 'Order Cancellation Policy', 'kind': 'page'}, {'title': 'FAQ', 'kind': 'page'},
                    {'title': 'About Us', 'kind': 'page'}, {'title': 'Track Order', 'kind': 'page'},
                    {'title': 'Contact Us', 'kind': 'page'}, {'title': 'Warranty Policy', 'kind': 'page'},
                    {'title': 'Contact Information', 'kind': 'legal_setting'}, {'title': 'Legal Notice', 'kind': 'legal_setting'},
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
                return {'stagedUploadsCreate': {'stagedTargets': [{'url': 'http://up', 'resourceUrl': 'http://res', 'parameters': []}], 'userErrors': []}}
            if 'productUpdate' in query:
                return {'productUpdate': {'product': {'id': '1'}, 'userErrors': []}}
            if 'themes' in query:
                return {'themes': {'edges': [{'node': {'id': 'gid://1', 'name': 'Dawn', 'role': 'MAIN'}}]}}
            if 'shop' in query:
                return {'shop': {'plan': {'displayName': 'Shopify Plus', 'partnerDevelopment': False}}}
            if 'fileCreate' in query:
                return {'fileCreate': {'files': [{'id': 'gid://shopify/MediaImage/1'}], 'userErrors': []}}
            if 'checkoutBrandingUpsert' in query:
                # Store the payload to assert against it later
                self.last_checkout_vars = variables
                return {'checkoutBrandingUpsert': {'checkoutBranding': {}, 'userErrors': []}}
            return {}
        mock_gql.side_effect = mock_gql_side_effect
        
        async def mock_rest_side_effect(domain, token, method, path, data=None):
            return {}
        mock_rest.side_effect = mock_rest_side_effect
        
        async def async_mock_post(*args, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            return mock_resp
        mock_httpx_post.side_effect = async_mock_post
        
        with patch('server.FERNET') as mock_fernet:
            mock_fernet.decrypt.return_value = b'decrypted'
            res = client.post('/api/store/publish', cookies=cookies)
            
        self.assertEqual(res.status_code, 200, res.text)
        self.assertTrue(res.json()['ok'])
        
        # Verify GraphQL payload structure
        self.assertIsNotNone(self.last_checkout_vars)
        self.assertEqual(self.last_checkout_vars['checkoutBrandingInput']['designSystem']['logo']['imageId'], 'gid://shopify/MediaImage/1')
        
        # Verify bytes uploaded
        mock_httpx_post.assert_called()

if __name__ == '__main__':
    unittest.main()
