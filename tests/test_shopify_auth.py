import asyncio
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self.payload = payload or {}

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, response, calls):
        self.response = response
        self.calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def post(self, url, data, headers):
        self.calls.append((url, data))
        return self.response


async def exercise():
    with tempfile.TemporaryDirectory() as temp:
        server.DB = Path(temp) / 'test.db'
        server.init()
        with server.registry() as c:
            c.execute('UPDATE app_stores SET client_id=?,client_secret=? WHERE id=1',
                      ('test-client', server.FERNET.encrypt(b'test-secret').decode()))
        with server.db() as c:
            c.execute('UPDATE stores SET domain=?,shopify_token=?,shopify_refresh_token=?,shopify_expires_at=?,shopify_refresh_expires_at=?,shopify_scopes=? WHERE id=1', (
                'merchant-test.myshopify.com',
                server.FERNET.encrypt(b'old-access').decode(),
                server.FERNET.encrypt(b'old-refresh').decode(),
                int(time.time()+30),int(time.time()+7200),server.SHOPIFY_SCOPES))
            row = server.store_row(c)
        calls = []
        response = FakeResponse(200, {'access_token':'new-access','refresh_token':'new-refresh',
                                      'expires_in':3600,'refresh_token_expires_in':7200})
        with patch.object(server.httpx, 'AsyncClient', lambda **kw: FakeClient(response, calls)):
            assert await server.token_for(row) == 'new-access'
        assert len(calls) == 1
        assert calls[0][0] == 'https://merchant-test.myshopify.com/admin/oauth/access_token'
        assert calls[0][1]['grant_type'] == 'refresh_token'
        assert calls[0][1]['refresh_token'] == 'old-refresh'
        with server.db() as c:
            row = server.store_row(c)
            assert row['shopify_token'] != 'new-access'
            assert row['shopify_refresh_token'] != 'new-refresh'
            assert row['shopify_expires_at'] > time.time()+3000
            assert server.row_json(row, ('business','brand')).get('shopify_refresh_token') is None
        assert await server.token_for(row) == 'new-access'
        assert len(calls) == 1
        with server.db() as c:
            c.execute('UPDATE stores SET shopify_expires_at=? WHERE id=1', (int(time.time()+30),))
            row = server.store_row(c)
        with patch.object(server.httpx, 'AsyncClient', lambda **kw: FakeClient(FakeResponse(401), calls)):
            try:
                await server.token_for(row)
            except HTTPException as exc:
                assert exc.status_code == 401
            else:
                raise AssertionError('Invalid refresh token must disconnect the store')
        with server.db() as c:
            row = server.store_row(c)
            assert not server.store_connected(row)
            assert row['shopify_token'] == ''
            assert row['shopify_refresh_token'] == ''
    print('Shopify token renewal checks passed')

asyncio.run(exercise())
