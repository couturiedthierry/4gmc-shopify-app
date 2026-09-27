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
import tempfile

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

    def test_upload_oversized(self):
        cookies = get_auth_cookies(1)
        content = create_mock_image('JPEG', (5000, 5000))
        res = client.put('/api/products/1/image', files={'image': ('test.jpg', content, 'image/jpeg')}, cookies=cookies)
        self.assertEqual(res.status_code, 400)

    @patch('server.db')
    def test_upload_ownership(self, mock_db):
        cookies = get_auth_cookies(2)
        mock_c = MagicMock()
        mock_c.execute.return_value.fetchone.return_value = None
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
            elif 'pages' in args[0]: mock_cursor.__iter__.return_value = [{'title': 'FAQ', 'kind': 'page'}]
            else: mock_cursor.__iter__.return_value = []
            return mock_cursor
        mock_c.execute.side_effect = mock_execute
        mock_db.return_value.__enter__.return_value = mock_c
        
        res = client.post('/api/store/publish', json={'target_theme_id': 'gid://shopify/Theme/999'}, cookies=cookies)
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()['ok'])

    @patch('server.db')
    @patch('server.DRY_RUN', False)
    @patch('server.shopify_graphql')
    @patch('server.shopify_rest')
    @patch('httpx.AsyncClient.post')
    def test_publish_live_mocked(self, mock_httpx_post, mock_rest, mock_gql, mock_db):
        cookies = get_auth_cookies(1)
        mock_c = MagicMock()
        
        def mock_execute(*args):
            mock_cursor = MagicMock()
            if 'stores' in args[0]: mock_cursor.fetchone.return_value = {'shopify_token': 'token', 'domain': 'test.com', 'name': 'My Cool Store', 'brand': '{"logo": {"extension": "png", "content_type": "image/png"}}'}
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
                    {'id': 1, 'images': '[]', 'shopify_id': 'gid://shopify/Product/123'}
                ]
            return mock_cursor
            
        mock_c.execute.side_effect = mock_execute
        mock_db.return_value.__enter__.return_value = mock_c
        
        self.gql_calls = []
        self.rest_calls = []
        
        async def mock_gql_side_effect(domain, token, query, variables=None):
            self.gql_calls.append((query, variables))
            if 'stagedUploadsCreate' in query: return {'stagedUploadsCreate': {'stagedTargets': [{'url': 'http://up', 'resourceUrl': 'http://res', 'parameters': []}], 'userErrors': []}}
            if 'themes' in query: return {'themes': {'edges': [{'node': {'id': 'gid://shopify/Theme/999', 'name': 'Target', 'role': 'UNPUBLISHED'}}]}}
            if 'shop' in query: return {'shop': {'plan': {'displayName': 'Shopify Plus', 'partnerDevelopment': False}}}
            if 'fileCreate' in query: return {'fileCreate': {'files': [{'id': 'gid://shopify/MediaImage/999'}], 'userErrors': []}}
            if 'checkoutBrandingUpsert' in query: return {'checkoutBrandingUpsert': {'checkoutBranding': {}, 'userErrors': []}}
            return {}
        mock_gql.side_effect = mock_gql_side_effect
        
        async def mock_rest_side_effect(domain, token, method, path, data=None):
            self.rest_calls.append((method, path, data))
            if 'GET' == method and 'assets.json' in path and 'asset[key]' not in path:
                return {'assets': [
                    {'key': 'sections/announcement-bar.liquid'},
                    {'key': 'sections/image-banner.liquid'},
                    {'key': 'sections/collection-list.liquid'},
                    {'key': 'sections/rich-text.liquid'},
                    {'key': 'sections/featured-collection.liquid'},
                    {'key': 'sections/image-with-text.liquid'},
                    {'key': 'sections/collapsible_content.liquid'},
                    {'key': 'sections/contact-form.liquid'},
                    {'key': 'sections/header.liquid'},
                    {'key': 'sections/footer.liquid'}
                ]}
            if 'GET' == method and 'assets.json' in path and 'index.json' in path:
                return {'asset': {'value': json.dumps({"sections": {"original": {}}, "order": ["original"]})}}
            if 'GET' == method and 'assets.json' in path and 'product.json' in path:
                return {'asset': {'value': json.dumps({
                    "sections": {
                        "main": {
                            "type": "main-product", 
                            "blocks": {
                                "title_block": {"type": "title"},
                                "share_block": {"type": "share"},
                                "related": {"type": "related-products"},
                                "qty": {"type": "quantity_selector"},
                                "deliv": {"type": "delivery"}
                            },
                            "block_order": ["title_block", "share_block", "qty", "deliv", "related"]
                        }
                    }, 
                    "order": ["main"]
                })}}
            return {}
        mock_rest.side_effect = mock_rest_side_effect
        
        async def async_mock_post(*args, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            return mock_resp
        mock_httpx_post.side_effect = async_mock_post
        
        real_join = os.path.join
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp.write(b"fake_image_bytes")
            tmp_path = tmp.name
            
        with patch('server.brand_asset_directory', return_value=os.path.dirname(tmp_path)):
            with patch('os.path.join', side_effect=lambda *args: tmp_path if 'logo' in args[-1] else real_join(*args)):
                with patch('builtins.open', unittest.mock.mock_open(read_data=b"fake_image_bytes")):
                    with patch('server.FERNET') as mock_fernet:
                        mock_fernet.decrypt.return_value = b'decrypted'
                        res = client.post('/api/store/publish', json={'target_theme_id': 'gid://shopify/Theme/999'}, cookies=cookies)
                    
        os.remove(tmp_path)
        
        self.assertEqual(res.status_code, 200, res.text)
        self.assertTrue(res.json()['ok'])
        
        # Checkout Bytes Assertions
        mock_httpx_post.assert_called_once()
        checkout_vars = next((v for q, v in self.gql_calls if 'checkoutBrandingUpsert' in q), None)
        self.assertEqual(checkout_vars['checkoutBrandingInput']['designSystem']['logo']['imageId'], 'gid://shopify/MediaImage/999')
        
        # Product cleanup assertion (keeps qty and deliv)
        product_put = next((data for m, p, data in self.rest_calls if m == 'PUT' and data['asset']['key'] == 'templates/product.json'), None)
        updated_prod = json.loads(product_put['asset']['value'])
        blocks = updated_prod['sections']['main']['blocks']
        self.assertIn('title_block', blocks) # Kept
        self.assertIn('qty', blocks) # Kept
        self.assertIn('deliv', blocks) # Kept
        self.assertNotIn('share_block', blocks) # Removed
        self.assertNotIn('related', blocks) # Removed
        
        # Homepage complete layout assertion
        index_put = next((data for m, p, data in self.rest_calls if m == 'PUT' and data['asset']['key'] == 'templates/index.json'), None)
        updated_index = json.loads(index_put['asset']['value'])
        self.assertEqual(updated_index['order'][0], 'gmc_announcement')
        self.assertEqual(updated_index['order'][-1], 'original')
        self.assertEqual(len(updated_index['order']), 11)
        self.assertEqual(updated_index['sections']['gmc_hero']['settings']['heading'], 'My Cool Store')

    @patch('server.db')
    @patch('server.DRY_RUN', False)
    @patch('server.shopify_graphql')
    def test_publish_main_theme_rejected(self, mock_gql, mock_db):
        cookies = get_auth_cookies(1)
        mock_c = MagicMock()
        
        def mock_execute(*args):
            mock_cursor = MagicMock()
            if 'stores' in args[0]: mock_cursor.fetchone.return_value = {'shopify_token': 'token', 'domain': 'test.com'}
            elif 'pages' in args[0]: mock_cursor.__iter__.return_value = [{'title': 'Legal Notice', 'kind': 'page'}, {'title': 'Privacy Policy', 'kind': 'page'}, {'title': 'Payment Policy', 'kind': 'page'}, {'title': 'Shipping Policy', 'kind': 'page'}, {'title': 'Terms of Service', 'kind': 'page'}, {'title': 'Refund and Return Policy', 'kind': 'page'}, {'title': 'Order Cancellation Policy', 'kind': 'page'}, {'title': 'FAQ', 'kind': 'page'}, {'title': 'About Us', 'kind': 'page'}, {'title': 'Track Order', 'kind': 'page'}, {'title': 'Contact Us', 'kind': 'page'}, {'title': 'Warranty Policy', 'kind': 'page'}, {'title': 'Contact Information', 'kind': 'legal_setting'}, {'title': 'Legal Notice', 'kind': 'legal_setting'}, {'title': 'Terms of Sale', 'kind': 'legal_setting'}]
            elif 'products' in args[0]: mock_cursor.__iter__.return_value = []
            return mock_cursor
            
        mock_c.execute.side_effect = mock_execute
        mock_db.return_value.__enter__.return_value = mock_c
        
        async def mock_gql_side_effect(domain, token, query, variables=None):
            if 'themes' in query: return {'themes': {'edges': [{'node': {'id': 'gid://shopify/Theme/111', 'name': 'Live', 'role': 'MAIN'}}]}}
            return {}
        mock_gql.side_effect = mock_gql_side_effect
        
        with patch('server.FERNET') as mock_fernet:
            mock_fernet.decrypt.return_value = b'dec'
            res = client.post('/api/store/publish', json={'target_theme_id': 'gid://shopify/Theme/111'}, cookies=cookies)
            
        self.assertEqual(res.status_code, 400)
        self.assertIn("cannot be the live MAIN theme", res.json()['detail'])

if __name__ == '__main__':
    unittest.main()
