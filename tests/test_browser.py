import sys
import os
import time
import json
import unittest
import subprocess
from playwright.sync_api import sync_playwright
import sqlite3

class TestBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = 8180
        
        # Prepare DB
        os.makedirs('data', exist_ok=True)
        
        env = os.environ.copy()
        env['ADMIN_PASSWORD'] = 'testpass'
        env['SESSION_SECRET'] = 'testsecret'
        env['SHOPIFY_API_KEY'] = 'testkey'
        env['SHOPIFY_API_SECRET'] = 'testsec'
        
        cls.log_file = open('scratch/server.log', 'w')
        
        cls.server_proc = subprocess.Popen(
            [sys.executable, '-c', f"""
import uvicorn
import server
import json
import os
server.DRY_RUN = True
with server.db() as c:
    c.execute("UPDATE stores SET shopify_token=?, domain=?, shopify_scopes=? WHERE id=1", (server.FERNET.encrypt(b'faketoken').decode(), 'test.myshopify.com', server.SHOPIFY_SCOPES))
    c.execute("UPDATE stores SET brand=? WHERE id=1", (json.dumps({{"logo": {{"extension": "png", "content_type": "image/png"}}}}),))
    os.makedirs(server.brand_asset_directory(1), exist_ok=True)
    with open(os.path.join(server.brand_asset_directory(1), 'logo.png'), 'w') as f: f.write('fake image')
    c.execute("INSERT INTO pages (store_id, title, kind, status) VALUES (1, 'FAQ', 'page', 'published')")

async def mock_graphql(*args, **kwargs):
    query = args[2] if len(args)>2 else kwargs.get('query')
    if 'themes' in query: return {{'themes': {{'edges': [{{'node': {{'id': 'gid://shopify/Theme/777', 'name': 'Target', 'role': 'UNPUBLISHED'}}}}]}}}}
    if 'shop' in query: return {{'shop': {{'plan': {{'displayName': 'Shopify Plus', 'partnerDevelopment': False}}}}}}
    return {{}}
server.shopify_graphql = mock_graphql

async def mock_rest(*args, **kwargs):
    path = args[3] if len(args)>3 else kwargs.get('path')
    if 'assets.json' in path and 'asset[key]' not in path:
        return {{'assets': [{{'key': 'sections/announcement-bar.liquid'}}]}} 
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
        
    def test_frontend_flow(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            page.on("console", lambda msg: print(f"Browser console [{msg.type}]: {msg.text}"))
            
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
                page.locator('#target-theme-select').last.select_option('gid://shopify/Theme/777')
                
                # Click Publish
                page.evaluate("document.querySelector('button[data-action=\"publish-store-design\"]').click()")
                
                # Check Toast
                page.wait_for_selector('#toast.show', timeout=5000)
                toast_text = page.locator('#toast').last.text_content()
                print("Toast text:", toast_text)
                self.assertIn("Publication blocked", toast_text)
                self.assertNotIn("Unknown", toast_text) # Prove we didn't hit the bug!
                
            except Exception as e:
                os.makedirs('scratch', exist_ok=True)
                page.screenshot(path="scratch/timeout_screenshot.png")
                raise e
            finally:
                browser.close()

if __name__ == '__main__':
    unittest.main()
