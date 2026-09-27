import sys
import os
import time
import json
import unittest
import subprocess
import shutil
from playwright.sync_api import sync_playwright
import sqlite3

class TestBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = 8210
        cls.test_dir = 'scratch/test_env'
        cls.db_path = os.path.join(cls.test_dir, 'studio.db')
        cls.asset_dir = os.path.join(cls.test_dir, 'assets')
        
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)
        os.makedirs(cls.asset_dir, exist_ok=True)
        
        env = os.environ.copy()
        env['ADMIN_PASSWORD'] = 'testpass'
        env['SESSION_SECRET'] = 'testsecret'
        env['SHOPIFY_API_KEY'] = 'testkey'
        env['SHOPIFY_API_SECRET'] = 'testsec'
        env['DB_PATH'] = cls.db_path
        env['WORKSPACE_DIR'] = cls.asset_dir
        
        # We spawn a python script to initialize the DB and insert the brand to avoid import caching issues
        subprocess.run([sys.executable, '-c', f"""
import sys, os, json
sys.path.insert(0, os.path.abspath('.'))
os.environ['DB_PATH'] = '{cls.db_path.replace(chr(92), '/')}'
os.environ['WORKSPACE_DIR'] = '{cls.asset_dir.replace(chr(92), '/')}'
import server
with server.db() as c:
    c.execute("INSERT OR REPLACE INTO stores (id, shopify_token, domain, shopify_scopes, brand) VALUES (1, ?, ?, ?, ?)", 
              (server.FERNET.encrypt(b'faketoken').decode(), 'test.myshopify.com', server.SHOPIFY_SCOPES, json.dumps({{"logo": {{"extension": "png", "content_type": "image/png"}}}})))
    c.commit()
os.makedirs(server.brand_asset_directory(1), exist_ok=True)
with open(os.path.join(server.brand_asset_directory(1), 'logo.png'), 'w') as f: f.write('fake image')
        """], env=env, check=True)

        cls.log_file = open('scratch/server.log', 'w')
        
        cls.server_proc = subprocess.Popen(
            [sys.executable, '-c', f"""
import sys, os, json
sys.path.insert(0, os.path.abspath('.'))
import uvicorn
import server

server.DRY_RUN = True

async def mock_graphql(*args, **kwargs):
    query = args[2] if len(args)>2 else kwargs.get('query')
    if 'themes' in query: return {{'themes': {{'edges': [{{'node': {{'id': 'gid://shopify/Theme/777', 'name': 'Target', 'role': 'UNPUBLISHED'}}}}]}}}}
    if 'shop' in query: return {{'shop': {{'plan': {{'displayName': 'Shopify Plus', 'partnerDevelopment': False}}}}}}
    if 'stagedUploadsCreate' in query: return {{'stagedUploadsCreate': {{'stagedTargets': [{{'url': 'http://up', 'resourceUrl': 'http://res', 'parameters': []}}], 'userErrors': []}}}}
    if 'fileCreate' in query: return {{'fileCreate': {{'files': [{{'id': 'gid://shopify/MediaImage/999'}}], 'userErrors': []}}}}
    if 'checkoutBrandingUpsert' in query: return {{'checkoutBrandingUpsert': {{'checkoutBranding': {{}}, 'userErrors': []}}}}
    return {{}}
server.shopify_graphql = mock_graphql

async def mock_rest(*args, **kwargs):
    path = args[3] if len(args)>3 else kwargs.get('path')
    if 'assets.json' in path and 'asset[key]' not in path:
        return {{'assets': [
            {{'key': 'sections/announcement-bar.liquid'}},
            {{'key': 'sections/image-banner.liquid'}},
            {{'key': 'sections/collection-list.liquid'}},
            {{'key': 'sections/rich-text.liquid'}},
            {{'key': 'sections/featured-collection.liquid'}},
            {{'key': 'sections/image-with-text.liquid'}},
            {{'key': 'sections/collapsible_content.liquid'}},
            {{'key': 'sections/contact-form.liquid'}},
            {{'key': 'sections/header.liquid'}},
            {{'key': 'sections/footer.liquid'}}
        ]}}
    if 'GET' == args[2] and 'assets.json' in path and 'index.json' in path:
        return {{'asset': {{'value': json.dumps({{"sections": {{"original": {{}}}}, "order": ["original"]}})}}}}
    if 'GET' == args[2] and 'assets.json' in path and 'product.json' in path:
        return {{'asset': {{'value': json.dumps({{"sections": {{"main": {{"type": "main-product", "blocks": {{"title_block": {{"type": "title"}}}}, "block_order": ["title_block"]}}}}, "order": ["main"]}})}}}}
    return {{}}
server.shopify_rest = mock_rest

uvicorn.run(server.app, host='127.0.0.1', port={cls.port}, log_level='debug')
"""], env=env, stderr=cls.log_file, stdout=cls.log_file)
        
        time.sleep(3)
        
    @classmethod
    def tearDownClass(cls):
        cls.server_proc.terminate()
        cls.server_proc.wait()
        cls.log_file.close()
        
    def _run_test(self, expect_success=False):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            console_errors = []
            request_failures = []
            
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == 'error' else None)
            page.on("requestfailed", lambda req: request_failures.append(f"{req.url} - {req.failure}"))
            
            try:
                page.goto(f"http://127.0.0.1:{self.port}/")
                
                # Login
                page.wait_for_selector('input[type="password"]', timeout=5000)
                page.fill('input[type="password"]', 'testpass')
                page.click('button:has-text("Sign in")')
                
                # Wait for Dashboard
                page.wait_for_selector('button[data-view="design"]', timeout=5000)
                
                # Go to Store Design
                page.evaluate("document.querySelector('button[data-view=\"design\"]').click()")
                
                # Wait for selector and populate
                page.wait_for_selector('#target-theme-select', state='visible', timeout=5000)
                page.wait_for_function("Array.from(document.querySelectorAll('#target-theme-select')).some(el => el.options.length > 1)", timeout=5000)
                
                # Verify UNPUBLISHED filter works
                select_inner_html = page.evaluate("document.querySelector('#target-theme-select').innerHTML")
                self.assertIn("UNPUBLISHED", select_inner_html)
                self.assertNotIn("MAIN", select_inner_html)
                
                page.locator('#target-theme-select').last.select_option('gid://shopify/Theme/777')
                
                # Click Publish
                page.evaluate("document.querySelector('button[data-action=\"publish-store-design\"]').click()")
                
                # Check Toast
                page.wait_for_selector('#toast.show', timeout=5000)
                toast_text = page.locator('#toast').last.text_content()
                print(f"Toast text (expect_success={expect_success}):", toast_text)
                
                if expect_success:
                    self.assertIn("Store templates prepared successfully", toast_text)
                else:
                    self.assertIn("Publication blocked", toast_text)
                    self.assertNotIn("Unknown", toast_text)
                
                # Expected errors filtering
                unexpected_console_errors = [e for e in console_errors if "401" not in e and "400" not in e]
                if unexpected_console_errors:
                    print("Unexpected console errors:", unexpected_console_errors)
                self.assertEqual(len(unexpected_console_errors), 0, "Found unexpected browser console errors")
                
                if request_failures:
                    print("Request failures:", request_failures)
                self.assertEqual(len(request_failures), 0, "Found failed requests")
                
            except Exception as e:
                page.screenshot(path=f"scratch/timeout_screenshot_{expect_success}.png")
                raise e
            finally:
                browser.close()

    def test_frontend_rejection(self):
        # Empty DB pages -> should fail preflight
        self._run_test(expect_success=False)

    def test_frontend_success(self):
        # Insert all required pages to pass preflight
        with sqlite3.connect(self.db_path) as c:
            for title in ['Legal Notice', 'Privacy Policy', 'Payment Policy', 'Shipping Policy', 'Terms of Service', 'Refund and Return Policy', 'Order Cancellation Policy', 'FAQ', 'About Us', 'Track Order', 'Contact Us', 'Warranty Policy']:
                c.execute("INSERT INTO pages (store_id, title, kind, status) VALUES (1, ?, 'page', 'published')", (title,))
            for title in ['Contact Information', 'Legal Notice', 'Terms of Sale']:
                c.execute("INSERT INTO pages (store_id, title, kind, status) VALUES (1, ?, 'legal_setting', 'published')", (title,))
            c.commit()
        
        self._run_test(expect_success=True)

if __name__ == '__main__':
    unittest.main()
