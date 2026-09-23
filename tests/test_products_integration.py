import json
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server

with tempfile.TemporaryDirectory() as temp:
    server.DB = Path(temp) / 'test.db'
    server.init()
    body = 'This sample item is described using only verified facts from the merchant and source listing.'
    with server.db() as c:
        c.execute('UPDATE stores SET domain=?,business=?,shopify_token=?,shopify_refresh_token=?,shopify_expires_at=?,shopify_refresh_expires_at=?,shopify_scopes=? WHERE id=1', (
            'merchant-test.myshopify.com',json.dumps({'business_name':'Example','currency':'USD'}),
            server.FERNET.encrypt(b'fake-test-token').decode(),
            server.FERNET.encrypt(b'fake-refresh-token').decode(),int(time.time()+3600),int(time.time()+7200),server.SHOPIFY_SCOPES))
        product_id = c.execute('INSERT INTO products(store_id,source_url,source_title,title,description,price,sku,gtin,images,source_data) VALUES(?,?,?,?,?,?,?,?,?,?)',(
            1,'https://source.example/products/item','Sample item','Sample item',body,'12.50','ABC-1','',
            json.dumps(['https://cdn.example.com/item.jpg']),json.dumps({'variants':[{'id':1}]}))).lastrowid
    client = TestClient(server.app)
    assert client.post('/api/login',json={'password':server.ADMIN_PASSWORD}).status_code==200
    assert client.post(f'/api/products/{product_id}/upload').status_code==400
    assert client.post(f'/api/products/{product_id}/review').status_code==200
    calls=[]
    async def graph(domain, token, query, variables=None):
        calls.append((query,variables))
        if 'collectionByIdentifier' in query:
            return {'collectionByIdentifier': None}
        if 'collectionCreate' in query:
            return {'collectionCreate': {'collection': {'id': 'gid://shopify/Collection/8', 'title': 'Featured Products', 'handle': 'featured-products'}, 'userErrors': []}}
        if 'collectionAddProducts' in query:
            return {'collectionAddProducts': {'collection': {'id': 'gid://shopify/Collection/8'}, 'userErrors': []}}
        if 'publications(first:50)' in query:
            return {'publications': {'nodes': [{'id': 'gid://shopify/Publication/5', 'name': 'Online Store', 'channels': {'nodes': []}}]}}
        if 'publishablePublish' in query:
            return {'publishablePublish': {'publishable': {'publishedOnPublication': True}, 'userErrors': []}}
        if 'inventoryLevels(first:50)' in query:
            return {'productByIdentifier': {'variants': {'nodes': [{'id': 'gid://shopify/ProductVariant/3', 'inventoryItem': {'id': 'gid://shopify/InventoryItem/7', 'tracked': False, 'inventoryLevels': {'nodes': []}}}]}}}
        if 'locations(first:20)' in query:
            return {'locations': {'nodes': [{'id': 'gid://shopify/Location/1', 'name': 'Main', 'isActive': True}]}}
        if 'inventorySetQuantities' in query:
            return {'inventorySetQuantities': {'inventoryAdjustmentGroup': {'changes': []}, 'userErrors': []}}
        if 'shop{currencyCode}' in query:
            return {'shop':{'currencyCode':'USD'}}
        if 'productByIdentifier' in query and variables['identifier'].get('handle'):
            return {'productByIdentifier':None}
        if 'productCreate' in query:
            assert variables['product']['status'] in ('DRAFT', 'ACTIVE')
            assert variables['product']['vendor']=='My store'
            assert variables['product']['productType']=='Featured Products'
            assert 'media' not in variables
            return {'productCreate':{'product':{'id':'gid://shopify/Product/99'},'userErrors':[]}}
        if 'id status' in query:
            return {'productByIdentifier':{'id':'gid://shopify/Product/99','status':'ACTIVE'}}
        if 'productUpdate' in query:
            return {'productUpdate':{'product':{'id':'gid://shopify/Product/99'},'userErrors':[]}}
        if 'productVariantsBulkUpdate' in query:
            assert variables['variants'][0]['price']=='12.50'
            assert isinstance(variables['variants'][0]['inventoryItem']['tracked'], bool)
            return {'productVariantsBulkUpdate':{'product':{'id':'gid://shopify/Product/99'},'userErrors':[]}}
        if 'media(first:' in query:
            with server.db() as check_db:
                expected_sku = check_db.execute('SELECT sku FROM products WHERE id=?', (product_id,)).fetchone()['sku']
            return {'productByIdentifier':{'id':'gid://shopify/Product/99','title':'Sample item','descriptionHtml':server.page_html(body),'status':'ACTIVE','handle':'gmc-studio-product-1','vendor':'My store','productType':'Featured Products','variants':{'nodes':[{'id':'gid://shopify/ProductVariant/3','price':'12.50','sku':expected_sku, 'barcode':'','inventoryItem':{'tracked':True}}]},'media':{'nodes':[]}}}
        return {'productByIdentifier':{'id':'gid://shopify/Product/99','variants':{'nodes':[{'id':'gid://shopify/ProductVariant/3'}]}}}
    with patch.object(server,'shopify_graphql',graph):
        response=client.post(f'/api/products/{product_id}/upload')
        assert response.status_code==200,response.text
        response=client.post(f'/api/products/{product_id}/upload')
        assert response.status_code==200,response.text
    assert sum('productCreate' in q for q,_ in calls)==1
    assert sum('productUpdate' in q for q,_ in calls)==1
    assert client.get('/api/state').json()['products'][0]['status'] in ('shopify_draft', 'published')
    publish_calls=[]
    async def publishing_graph(domain, token, query, variables=None):
        publish_calls.append((query, variables))
        if 'publications(first:50)' in query:
            return {'publications': {'nodes': [{'id': 'gid://shopify/Publication/5', 'name': 'Online Store',
                                                 'channels': {'nodes': [{'handle': 'online_store_channel', 'name': 'Online Store'}]}}]}}
        if 'publishablePublish' in query:
            assert variables['publicationId']=='gid://shopify/Publication/5'
            return {'publishablePublish': {'publishable': {'publishedOnPublication': True}, 'userErrors': []}}
        if 'productUpdate' in query:
            assert variables['product']['status']=='ACTIVE'
            return {'productUpdate': {'product': {'id': 'gid://shopify/Product/99'}, 'userErrors': []}}
        if 'publishedOnPublication' in query:
            return {'productByIdentifier': {'id': 'gid://shopify/Product/99', 'status': 'ACTIVE',
                                            'handle': 'gmc-studio-product-1', 'publishedOnPublication': True}}
        if 'productByIdentifier' in query:
            return {'productByIdentifier': {'id': 'gid://shopify/Product/99', 'status': 'DRAFT',
                                            'handle': 'gmc-studio-product-1'}}
        raise AssertionError(query)
    with patch.object(server,'shopify_graphql',publishing_graph):
        result=client.post('/api/products/auto-publish',json={'url':'https://source.example/products/item'})
        assert result.status_code==400
        with server.db() as c:
            c.execute("UPDATE stores SET product_source_url='https://source.example' WHERE id=1")
        from starlette.requests import Request
        cookie=client.cookies.get('gmc_session')
        request=Request({'type':'http','method':'POST','headers':[(b'cookie',f'gmc_session={cookie}'.encode())]})
        import asyncio
        result=asyncio.run(server.publish_source_product(product_id,request))
        assert result['status']=='published'
    assert any('publishablePublish' in query for query,_ in publish_calls)
    assert client.get('/api/state').json()['products'][0]['status']=='published'
    async def active_product(domain, token, query, variables=None):
        if 'collectionAddProducts' in query:
            return {'collectionAddProducts': {'collection': {'id': 'gid://shopify/Collection/8'}, 'userErrors': []}}
        if 'publications(first:50)' in query:
            return {'publications': {'nodes': [{'id': 'gid://shopify/Publication/5', 'name': 'Online Store', 'channels': {'nodes': []}}]}}
        if 'publishablePublish' in query:
            return {'publishablePublish': {'publishable': {'publishedOnPublication': True}, 'userErrors': []}}
        if 'inventoryLevels(first:50)' in query:
            return {'productByIdentifier': {'variants': {'nodes': [{'id': 'gid://shopify/ProductVariant/3', 'inventoryItem': {'id': 'gid://shopify/InventoryItem/7', 'tracked': False, 'inventoryLevels': {'nodes': []}}}]}}}
        if 'locations(first:20)' in query:
            return {'locations': {'nodes': [{'id': 'gid://shopify/Location/1', 'name': 'Main', 'isActive': True}]}}
        if 'inventorySetQuantities' in query:
            return {'inventorySetQuantities': {'inventoryAdjustmentGroup': {'changes': []}, 'userErrors': []}}
        if 'shop{currencyCode}' in query:
            return {'shop':{'currencyCode':'USD'}}
        if 'productUpdate' in query:
            assert variables['product']['status']=='ACTIVE'
            return {'productUpdate':{'product':{'id':'gid://shopify/Product/99'},'userErrors':[]}}
        if 'productVariantsBulkUpdate' in query:
            return {'productVariantsBulkUpdate':{'product':{'id':'gid://shopify/Product/99'},'userErrors':[]}}
        if 'media(first:' in query:
            with server.db() as check_db:
                expected_sku = check_db.execute('SELECT sku FROM products WHERE id=?', (product_id,)).fetchone()['sku']
            return {'productByIdentifier':{'id':'gid://shopify/Product/99','title':'Sample item','descriptionHtml':server.page_html(body),'status':'ACTIVE','handle':'gmc-studio-product-1','vendor':'My store','productType':'Featured Products','variants':{'nodes':[{'id':'gid://shopify/ProductVariant/3','price':'12.50','sku':expected_sku,'barcode':'','inventoryItem':{'tracked':True}}]},'media':{'nodes':[]}}}
        if 'variants(first:2)' in query:
            return {'productByIdentifier':{'id':'gid://shopify/Product/99','variants':{'nodes':[{'id':'gid://shopify/ProductVariant/3'}]}}}
        return {'productByIdentifier':{'id':'gid://shopify/Product/99','status':'ACTIVE'}}
    with patch.object(server,'shopify_graphql',active_product):
        assert client.post(f'/api/products/{product_id}/upload').status_code==200
    assert client.get('/api/state').json()['products'][0]['status']=='published'
    assert client.put(f'/api/products/{product_id}',json={'title':'Sample item','description':body,'price':'0','sku':'ABC-1','gtin':''}).status_code==200
    assert client.post(f'/api/products/{product_id}/review').status_code==400
    current_store=client.get('/api/state').json()['store']
    assert client.put('/api/store',json={'name':current_store['name'],'domain':'another-test.myshopify.com','business':current_store['business'],'brand':current_store['brand']}).status_code==200
    after_switch=client.get('/api/state').json()
    assert after_switch['store']['connected'] is False
    assert after_switch['products'][0]['shopify_id']==''
    assert client.post(f'/api/products/{product_id}/resync').status_code==200
    assert client.post('/api/products/reset-all').status_code==200
print('Product draft upload contract checks passed')
