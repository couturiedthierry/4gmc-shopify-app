import asyncio
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


class InvalidJsonResponse:
    status_code = 200
    def json(self):
        raise ValueError('not json')


class InvalidJsonClient:
    async def __aenter__(self): return self
    async def __aexit__(self, *_): return False
    async def post(self, *args, **kwargs): return InvalidJsonResponse()


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
        assert client.get('/api/state').status_code == 401
        assert client.post('/api/login', json={'password': server.ADMIN_PASSWORD}).status_code == 200

        update = client.put('/api/store', json={
            'name': '  VYROX  ', 'domain': '',
            'business': {
                'domain_name': 'HTTPS://VYROX.US/', 'email': ' contact@vyrox.us ',
                'address': ' 1819 County Rte 512 ', 'country': ' United States ',
                'currency': ' usd ', 'phone': ' +1 971 361 4811 ',
            },
            'brand': {'color': '#2251DC', 'accent': '#6F9CFF'},
        })
        assert update.status_code == 200, update.text
        state = client.get('/api/state').json()['store']
        assert state['name'] == 'VYROX'
        assert state['business']['business_name'] == 'VYROX'
        assert state['business']['domain_name'] == 'vyrox.us'
        assert state['business']['email'] == 'contact@vyrox.us'
        assert state['business']['currency'] == 'USD'
        assert state['business']['live_chat'] == 'Available on the website during business hours'
        assert state['business']['business_hours'] == 'Mon-Fri: 9:00 AM - 5:00 PM (Eastern Time)'

        invalid_cases = [
            ({'name': '   ', 'domain': '', 'business': {}, 'brand': {'color':'#2251dc','accent':'#6f9cff'}}, 'store name'),
            ({'name': 'VYROX', 'domain': '', 'business': {'email':'wrong'}, 'brand': {'color':'#2251dc','accent':'#6f9cff'}}, 'contact email'),
            ({'name': 'VYROX', 'domain': '', 'business': {'currency':'US'}, 'brand': {'color':'#2251dc','accent':'#6f9cff'}}, 'currency code'),
            ({'name': 'VYROX', 'domain': '', 'business': {'domain_name':'bad host'}, 'brand': {'color':'#2251dc','accent':'#6f9cff'}}, 'domain name'),
        ]
        for body, fragment in invalid_cases:
            response = client.put('/api/store', json=body)
            assert response.status_code == 400, response.text
            assert fragment in response.json()['detail'].lower()

        added = client.post('/api/stores', json={'domain':'second-audit.myshopify.com'})
        assert added.status_code == 200, added.text
        store_id = added.json()['id']
        saved = client.put(f'/api/stores/{store_id}/connection', json={'domain':'second-fixed.myshopify.com'})
        assert saved.status_code == 200, saved.text
        selected = client.get('/api/state').json()
        assert selected['active_store_id'] == store_id
        assert selected['store']['domain'] == 'second-fixed.myshopify.com'

        callback = client.get('/api/shopify/callback?state=wrong', follow_redirects=False)
        assert callback.status_code == 303
        assert callback.headers['location'].startswith('/?shopify_error=')
        assert 'authorization+state+mismatch' in callback.headers['location']

        with patch.object(server, 'SMARTAPI_KEY', 'test-key'), patch.object(server.httpx, 'AsyncClient', lambda **kw: InvalidJsonClient()):
            try:
                asyncio.run(server.ai_json('test'))
            except HTTPException as error:
                assert error.status_code == 502
                assert error.detail == 'AI service returned an invalid response'
            else:
                raise AssertionError('Malformed AI response should be rejected clearly')

        assert client.post('/api/logout').status_code == 200
        assert client.get('/api/state').status_code == 401
        print('Whole dashboard workflow regression checks passed')
    finally:
        server.DB, server.PUBLIC_URL = old_db, old_url
        server.SHOPIFY_CLIENT_ID, server.SHOPIFY_CLIENT_SECRET = old_client_id, old_client_secret
