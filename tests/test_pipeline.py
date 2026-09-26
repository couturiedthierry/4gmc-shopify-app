import os
import json
import time
import hmac
import hashlib
import unittest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

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
    @patch('server.db')
    @patch('server.DRY_RUN', False)
    @patch('server.shopify_graphql')
    @patch('server.shopify_rest')
    @patch('httpx.AsyncClient.post')
    @patch('builtins.open', new_callable=MagicMock)
    @patch('os.path.exists')
    def test_publish_live_mocked(self, mock_exists, mock_open, mock_httpx_post, mock_rest, mock_gql, mock_db):
        mock_exists.return_value = True # Make os.path.exists return True so it finds our mocked logo file
        cookies = get_auth_cookies(1)
        mock_c = MagicMock()
        
        def mock_execute(*args):
            mock_cursor = MagicMock()
            if 'stores' in args[0]: mock_cursor.fetchone.return_value = {'shopify_token': 'token', 'domain': 'test.com', 'brand': '{"logo": {"extension": "png", "content_type": "image/png"}}'}
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
                    {'id': 1, 'images': '[]', 'shopify_id': 'gid://shopify/Product/123'} # NO IMAGES
                ]
            return mock_cursor
            
        mock_c.execute.side_effect = mock_execute
        mock_db.return_value.__enter__.return_value = mock_c
        
        self.gql_calls = []
        self.rest_calls = []
        
        async def mock_gql_side_effect(domain, token, query, variables=None):
            self.gql_calls.append((query, variables))
            if 'stagedUploadsCreate' in query: return {'stagedUploadsCreate': {'stagedTargets': [{'url': 'http://up', 'resourceUrl': 'http://res', 'parameters': []}], 'userErrors': []}}
            if 'themes' in query: return {'themes': {'edges': [{'node': {'id': 'gid://1', 'name': 'Dawn', 'role': 'MAIN'}}]}}
            if 'shop' in query: return {'shop': {'plan': {'displayName': 'Shopify Plus', 'partnerDevelopment': False}}}
            if 'fileCreate' in query: return {'fileCreate': {'files': [{'id': 'gid://shopify/MediaImage/999'}], 'userErrors': []}}
            if 'checkoutBrandingUpsert' in query: return {'checkoutBrandingUpsert': {'checkoutBranding': {}, 'userErrors': []}}
            return {}
        mock_gql.side_effect = mock_gql_side_effect
        
        async def mock_rest_side_effect(domain, token, method, path, data=None):
            self.rest_calls.append((method, path, data))
            if 'GET' == method and 'assets.json' in path and 'index.json' in path:
                return {'asset': {'value': json.dumps({"sections": {"original": {}}, "order": ["original"]})}}
            if 'GET' == method and 'assets.json' in path and 'product.json' in path:
                return {'asset': {'value': json.dumps({"sections": {"main": {}}, "order": ["main"]})}}
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
        
        mock_httpx_post.assert_called_once()
        
        checkout_vars = next((v for q, v in self.gql_calls if 'checkoutBrandingUpsert' in q), None)
        self.assertIsNotNone(checkout_vars)
        self.assertEqual(checkout_vars['checkoutBrandingInput']['designSystem']['logo']['imageId'], 'gid://shopify/MediaImage/999')
        
        # Test index.json injection
        index_put = next((data for m, p, data in self.rest_calls if m == 'PUT' and data['asset']['key'] == 'templates/index.json'), None)
        self.assertIsNotNone(index_put)
        updated_index = json.loads(index_put['asset']['value'])
        self.assertIn('gmc_hero', updated_index['sections'])
        self.assertIn('gmc_featured_collection', updated_index['sections'])
        self.assertIn('original', updated_index['sections'])
        
        # Test product.json clean template
        product_put = next((data for m, p, data in self.rest_calls if m == 'PUT' and data['asset']['key'] == 'templates/product.json'), None)
        self.assertIsNotNone(product_put)
        
        # Test static header/footer
        header_put = next((data for m, p, data in self.rest_calls if m == 'PUT' and data['asset']['key'] == 'sections/header.json'), None)
        self.assertIsNotNone(header_put)
        footer_put = next((data for m, p, data in self.rest_calls if m == 'PUT' and data['asset']['key'] == 'sections/footer.json'), None)
        self.assertIsNotNone(footer_put)

if __name__ == '__main__':
    unittest.main()
