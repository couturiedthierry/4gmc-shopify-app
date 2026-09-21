import json
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server
import shopify_usa as usa


def region(code):
    return {'__typename':'MarketRegionCountry','countryCode':code}


def market(mid, code, status='ACTIVE'):
    return {'id':mid,'name':code,'status':status,'conditions':{'regionsCondition':{
        'applicationLevel':'SPECIFIED','regions':{'pageInfo':{'hasNextPage':False},'nodes':[region(code)]}}}}


def connection(items):
    return {'pageInfo':{'hasNextPage':False},'nodes':items}


with tempfile.TemporaryDirectory() as temp:
    server.DB=Path(temp)/'test.db'
    server.init()
    with server.db() as c:
        c.execute('UPDATE stores SET name=?,domain=?,business=?,shopify_token=?,shopify_refresh_token=?,shopify_expires_at=?,shopify_refresh_expires_at=?,shopify_scopes=? WHERE id=1',(
            'Example Store','merchant-test.myshopify.com',
            json.dumps({'business_name':'Example Store','email':'help@example.com','country':'United States','currency':'USD','shipping_time':'3-5 business days'}),
            server.FERNET.encrypt(b'fake-access').decode(),server.FERNET.encrypt(b'fake-refresh').decode(),
            int(time.time()+3600),int(time.time()+7200),server.SHOPIFY_SCOPES))
        c.execute("INSERT INTO pages(store_id,kind,title,body,status,reviewed_hash) VALUES(1,'shipping','Shipping policy','Old terms','published','old-review')")
    markets=[market('gid://shopify/Market/1','US'),market('gid://shopify/Market/2','CA')]
    shipping_options=[]
    calls=[]
    async def graph(domain,token,query,variables=None):
        calls.append((query,variables))
        if 'UsaStoreContext' in query:
            return {'shop':{'name':'Old Shopify Name','contactEmail':'old@example.com','currencyCode':'USD',
                            'features':{'marketDrivenShipping':True}},'markets':connection(markets)}
        if 'UsaMarketShipping' in query:
            return {'markets':connection([{'id':markets[0]['id'],'delivery':{'shipping':{
                'isEnabled':True,'optionDefinitions':connection(shipping_options)}}}])}
        if 'UsaMarketUpdate' in query:
            mid=variables['id'];input=variables['input']
            if 'status' in input:
                next(m for m in markets if m['id']==mid)['status']=input['status']
            if 'delivery' in input:
                shipping=input['delivery']['shipping']
                assert shipping['optionDefinitionsToDelete']==[]
                assert shipping['optionDefinitionsToCreate'][0]['flatRate']['rateGroups'][0]['rate']['price']=={'amount':'0.00','currencyCode':'USD'}
                shipping_options[:]=[{'id':'gid://shopify/DeliveryFlatRateOptionDefinition/1','isActive':True,
                    'name':'Free shipping','rateGroups':connection([{'rate':{'price':{'amount':'0.00','currencyCode':'USD'}}}])}]
            return {'marketUpdate':{'market':{'id':mid,'status':next(m for m in markets if m['id']==mid)['status']},'userErrors':[]}}
        raise AssertionError('Unexpected operation')
    client=TestClient(server.app)
    assert client.post('/api/login',json={'password':server.ADMIN_PASSWORD}).status_code==200
    with patch.object(server,'shopify_graphql',graph):
        plan=client.get('/api/shopify/usa-plan')
        assert plan.status_code==200,plan.text
        body=plan.json()
        assert body['shipping_system']=='markets'
        assert body['markets_to_pause'][0]['name']=='CA'
        assert len(body['manual_steps'])==2
        assert client.post('/api/shopify/usa-apply',json={'fingerprint':'0'*64}).status_code==409
        response=client.post('/api/shopify/usa-apply',json={'fingerprint':body['fingerprint']})
        assert response.status_code==200,response.text
        assert response.json()['shipping_verified'] is True
    assert markets[1]['status']=='DRAFT'
    assert len(shipping_options)==1
    with server.db() as c:
        saved=server.store_row(c)
        assert json.loads(saved['business'])['shipping_cost']=='Free shipping in the United States (USD 0.00)'
        page=c.execute('SELECT status,reviewed_hash FROM pages WHERE store_id=1').fetchone()
        assert page['status']=='draft' and page['reviewed_hash']==''

profile={'id':'gid://shopify/DeliveryProfile/1','name':'General','profileLocationGroups':[
    {'locationGroup':{'id':'gid://shopify/DeliveryLocationGroup/1'},'locationGroupZones':connection([
        {'zone':{'id':'gid://shopify/DeliveryZone/1','countries':[{'code':{'countryCode':'CA','restOfWorld':False},'provinces':[]}]},
         'methodDefinitions':connection([])}])}]}
change=usa.legacy_profile_input(profile)
assert change['zonesToDelete']==['gid://shopify/DeliveryZone/1']
zone=change['locationGroupsToUpdate'][0]['zonesToCreate'][0]
assert zone['countries']==[{'code':'US','includeAllProvinces':True}]
assert zone['methodDefinitionsToCreate'][0]['rateGroupsToCreate'][0]['rateDefinitionsToCreate'][0]['price']['amount']=='0.00'
print('USA market and free-shipping workflow checks passed')
