import hashlib
import hmac
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


with tempfile.TemporaryDirectory() as temp:
    old_db, old_url = server.DB, server.PUBLIC_URL
    old_client_id, old_client_secret = server.SHOPIFY_CLIENT_ID, server.SHOPIFY_CLIENT_SECRET
    server.DB = Path(temp) / 'test.db'
    server.PUBLIC_URL = 'https://app.example.test'
    server.SHOPIFY_CLIENT_ID = 'shared-client'
    server.SHOPIFY_CLIENT_SECRET = 'shared-secret'
    try:
        server.init()
        client = TestClient(server.app, base_url='https://app.example.test')
        assert client.post('/api/login', json={'password': server.ADMIN_PASSWORD}).status_code == 200
        original = client.get('/api/state').json()
        assert original['active_store_id'] == 1
        response = client.post('/api/stores', json={
            'domain': 'second-test.myshopify.com',
        })
        assert response.status_code == 200, response.text
        second_id = response.json()['id']
        second = client.get('/api/state').json()
        assert second['active_store_id'] == second_id
        assert second['store']['domain'] == 'second-test.myshopify.com'
        assert second['products'] == [] and second['pages'] == []
        assert second['shopify_ready']
        with server.registry() as c:
            saved = c.execute('SELECT client_secret FROM app_stores WHERE id=?', (second_id,)).fetchone()['client_secret']
            assert saved == ''
        with patch.object(server, 'PUBLIC_URL', 'https://app.example.test'):
            oauth = client.get('/api/shopify/connect', follow_redirects=False)
        assert oauth.status_code in (302, 307), oauth.text
        redirect = urlparse(oauth.headers['location'])
        assert redirect.hostname == 'second-test.myshopify.com'
        assert parse_qs(redirect.query)['client_id'] == ['shared-client']
        assert 'shopify_oauth_state' in oauth.cookies
        assert oauth.cookies['shopify_oauth_state'].startswith(str(second_id) + '.')
        assert client.post('/api/stores/1/select').status_code == 200
        state = oauth.cookies['shopify_oauth_state'].split('.', 1)[1]
        callback_params = {'code': 'test-code', 'shop': 'second-test.myshopify.com', 'state': state}
        signature_base = '&'.join(f'{key}={value}' for key, value in sorted(callback_params.items()))
        callback_params['hmac'] = hmac.new(
            b'shared-secret', signature_base.encode(), hashlib.sha256
        ).hexdigest()
        class OAuthResponse:
            status_code = 200
            def json(self):
                return {'access_token': 'second-token', 'refresh_token': 'second-refresh',
                        'expires_in': 3600, 'refresh_token_expires_in': 7200,
                        'scope': server.SHOPIFY_SCOPES}
        class OAuthClient:
            async def __aenter__(self): return self
            async def __aexit__(self, *_): return False
            async def post(self, url, data, headers):
                assert url == 'https://second-test.myshopify.com/admin/oauth/access_token'
                assert data['client_id'] == 'shared-client'
                assert data['client_secret'] == 'shared-secret'
                return OAuthResponse()
        with patch.object(server.httpx, 'AsyncClient', lambda **kw: OAuthClient()):
            callback = client.get('/api/shopify/callback', params=callback_params,
                                  follow_redirects=False)
        assert callback.status_code in (302, 307), callback.text
        callback_state = client.get('/api/state').json()
        assert callback_state['active_store_id'] == second_id
        assert callback_state['store']['connected'] is True
        context = server.ACTIVE_STORE_ID.set(1)
        try:
            with server.db() as c:
                assert server.store_row(c)['shopify_token'] == ''
        finally:
            server.ACTIVE_STORE_ID.reset(context)
        context = server.ACTIVE_STORE_ID.set(second_id)
        try:
            with server.db() as c:
                assert server.FERNET.decrypt(server.store_row(c)['shopify_token'].encode()) == b'second-token'
        finally:
            server.ACTIVE_STORE_ID.reset(context)
        update = client.put('/api/store', json={
            'name': 'Second Brand', 'domain': 'second-test.myshopify.com',
            'business': {'email': 'second@example.test'},
            'brand': {'color': '#2251dc', 'accent': '#6f9cff'},
        })
        assert update.status_code == 200, update.text
        context = server.ACTIVE_STORE_ID.set(second_id)
        try:
            with server.db() as c:
                c.execute("INSERT INTO products(store_id,source_url,source_title,title) VALUES(1,'https://source.test/p','Original','Second product')")
                c.execute("INSERT INTO pages(store_id,kind,title) VALUES(1,'contact','Second contact')")
        finally:
            server.ACTIVE_STORE_ID.reset(context)
        assert client.post('/api/stores/1/select').status_code == 200
        first = client.get('/api/state').json()
        assert first['active_store_id'] == 1
        assert first['store']['name'] == original['store']['name']
        assert first['store']['domain'] == original['store']['domain']
        assert first['products'] == [] and first['pages'] == []
        assert client.post('/api/stores/' + str(second_id) + '/select').status_code == 200
        second = client.get('/api/state').json()
        assert second['store']['name'] == 'Second Brand'
        assert len(second['products']) == 1 and len(second['pages']) == 1
        assert client.put('/api/stores/' + str(second_id) + '/connection', json={
            'domain': 'second-test.myshopify.com',
        }).status_code == 200
        third = client.post('/api/stores', json={
            'domain': 'third-test.myshopify.com',
        })
        assert third.status_code == 200, third.text
        assert len(client.get('/api/state').json()['stores']) == 3
        assert client.post('/api/stores/' + str(second_id) + '/select').status_code == 200
        assert len(client.get('/api/state').json()['products']) == 1
        print('Multi-store isolation and OAuth binding checks passed')
    finally:
        server.DB, server.PUBLIC_URL = old_db, old_url
        server.SHOPIFY_CLIENT_ID, server.SHOPIFY_CLIENT_SECRET = old_client_id, old_client_secret
