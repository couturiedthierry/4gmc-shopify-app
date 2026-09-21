import asyncio
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


async def exercise():
    with tempfile.TemporaryDirectory() as temp:
        server.DB = Path(temp) / 'test.db'
        server.init()
        with server.db() as c:
            c.execute('UPDATE stores SET domain=?,business=?,shopify_token=?,shopify_refresh_token=?,shopify_expires_at=?,shopify_refresh_expires_at=?,shopify_scopes=? WHERE id=1', (
                'merchant-test.myshopify.com',
                json.dumps({'business_name':'Example Co','email':'help@example.com','shipping_time':'5 days','shipping_cost':'Free','return_window':'30 days'}),
                server.FERNET.encrypt(b'fake-test-token').decode(),
                server.FERNET.encrypt(b'fake-refresh-token').decode(),
                int(time.time()+3600),int(time.time()+7200),server.SHOPIFY_SCOPES,
            ))
        client = TestClient(server.app)
        assert client.post('/api/login', json={'password':server.ADMIN_PASSWORD}).status_code == 200
        body = 'We ship orders within five business days. Contact help@example.com for delivery questions.'
        page_id = client.post('/api/pages', json={'kind':'shipping','title':'Shipping policy','body':body}).json()['id']
        assert client.post(f'/api/pages/{page_id}/publish').status_code == 400
        assert client.post(f'/api/pages/{page_id}/review').status_code == 200
        calls = []
        async def graph(domain, token, query, variables=None):
            calls.append((query,variables))
            if 'shopPolicyUpdate' in query:
                assert variables['input']['type'] == 'SHIPPING_POLICY'
                return {'shopPolicyUpdate':{'shopPolicy':{'id':'gid://shopify/ShopPolicy/1','url':'https://example.com/policies/shipping-policy'},'userErrors':[]}}
            return {'shop':{'shopPolicies':[{'id':'gid://shopify/ShopPolicy/1','type':'SHIPPING_POLICY','body':server.page_html(body)}]}}
        with patch.object(server, 'shopify_graphql', graph):
            response = client.post(f'/api/pages/{page_id}/publish')
        assert response.status_code == 200, response.text
        assert len(calls) == 2
        state = client.get('/api/state').json()
        assert state['pages'][0]['status'] == 'published'
        assert state['pages'][0]['reviewed'] is True
        assert client.put(f'/api/pages/{page_id}',json={'kind':'shipping','title':'Shipping policy','body':body+' Updated.'}).status_code == 200
        assert client.get('/api/state').json()['pages'][0]['reviewed'] is False
        assert client.post(f'/api/pages/{page_id}/publish').status_code == 400

        page_id = client.post('/api/pages', json={'kind':'about','title':'About us','body':body}).json()['id']
        assert client.post(f'/api/pages/{page_id}/review').status_code == 200
        calls=[]
        async def graph_page(domain, token, query, variables=None):
            calls.append((query,variables))
            if 'pages(first:' in query:
                return {'pages':{'nodes':[]}}
            if 'pageCreate' in query:
                assert variables['page']['isPublished'] is True
                return {'pageCreate':{'page':{'id':'gid://shopify/Page/2','title':'About us','handle':'gmc-studio-about-2'},'userErrors':[]}}
            if 'pageUpdate' in query:
                return {'pageUpdate':{'page':{'id':'gid://shopify/Page/2','title':'About us','handle':'gmc-studio-about-2'},'userErrors':[]}}
            return {'page':{'id':'gid://shopify/Page/2','title':'About us','body':server.page_html(body),'isPublished':True,'handle':'gmc-studio-about-2'}}
        with patch.object(server, 'shopify_graphql', graph_page):
            assert client.post(f'/api/pages/{page_id}/publish').status_code == 200
            assert client.post(f'/api/pages/{page_id}/publish').status_code == 200
        assert sum('pageCreate' in q for q,_ in calls)==1
        assert sum('pageUpdate' in q for q,_ in calls)==1
        assert client.get('/api/state').json()['pages'][0]['status']=='published'
        collision_id = client.post('/api/pages',json={'kind':'faq','title':'FAQ','body':body}).json()['id']
        assert client.post(f'/api/pages/{collision_id}/review').status_code==200
        async def unrelated_page(domain, token, query, variables=None):
            if 'pages(first:' in query:
                return {'pages':{'nodes':[{'id':'gid://shopify/Page/999','handle':f'gmc-studio-faq-{collision_id}','title':'Other page','body':'Unrelated merchant text'}]}}
            raise AssertionError('An unrelated page must not be changed')
        with patch.object(server,'shopify_graphql',unrelated_page):
            assert client.post(f'/api/pages/{collision_id}/publish').status_code==409
        current_store = client.get('/api/state').json()['store']
        changed_business = dict(current_store['business'], return_window='14 days')
        update = {'name':current_store['name'],'domain':current_store['domain'],'business':changed_business,'brand':current_store['brand']}
        assert client.put('/api/store',json=update).status_code==200
        after_business = client.get('/api/state').json()
        assert after_business['store']['connected'] is True
        assert all(p['status']=='draft' and p['reviewed'] is False for p in after_business['pages'])
        update['domain']='another-test.myshopify.com'
        assert client.put('/api/store',json=update).status_code==200
        after_domain = client.get('/api/state').json()
        assert after_domain['store']['connected'] is False
        assert all(not p['shopify_id'] for p in after_domain['pages'])
    print('Publishing contract checks passed')

asyncio.run(exercise())
