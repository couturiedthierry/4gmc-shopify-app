import json
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


def conn(items):
    return {'pageInfo':{'hasNextPage':False},'nodes':items}

market={'id':'gid://shopify/Market/1','name':'United States','status':'ACTIVE',
        'conditions':{'regionsCondition':{'applicationLevel':'SPECIFIED',
        'regions':conn([{'__typename':'MarketRegionCountry','countryCode':'US'}])}}}
zone={'zone':{'id':'gid://shopify/DeliveryZone/1','countries':[{'code':{'countryCode':'CA','restOfWorld':False},'provinces':[]}]},
      'methodDefinitions':conn([])}
profile={'id':'gid://shopify/DeliveryProfile/1','name':'General',
         'profileLocationGroups':[{'locationGroup':{'id':'gid://shopify/DeliveryLocationGroup/1'},
                                  'locationGroupZones':conn([zone])}]}

with tempfile.TemporaryDirectory() as temp:
    server.DB=Path(temp)/'test.db';server.init()
    with server.db() as c:
        c.execute('UPDATE stores SET name=?,domain=?,business=?,shopify_token=?,shopify_refresh_token=?,shopify_expires_at=?,shopify_refresh_expires_at=?,shopify_scopes=? WHERE id=1',(
            'Example Store','merchant-test.myshopify.com',
            json.dumps({'business_name':'Example Store','email':'help@example.com','country':'US','currency':'USD','shipping_time':'3-5 business days'}),
            server.FERNET.encrypt(b'fake-access').decode(),server.FERNET.encrypt(b'fake-refresh').decode(),
            int(time.time()+3600),int(time.time()+7200),server.SHOPIFY_SCOPES))
    async def graph(domain,token,query,variables=None):
        if 'UsaStoreContext' in query:
            return {'shop':{'name':'Example Store','contactEmail':'help@example.com','currencyCode':'USD',
                            'features':{'marketDrivenShipping':False}},'markets':conn([market])}
        if 'UsaDeliveryProfiles' in query:
            return {'deliveryProfiles':conn([profile])}
        if 'UsaProfileUpdate' in query:
            body=variables['profile']
            assert body['zonesToDelete']==['gid://shopify/DeliveryZone/1']
            assert body['locationGroupsToUpdate'][0]['zonesToCreate'][0]['countries'][0]['code']=='US'
            profile['profileLocationGroups'][0]['locationGroupZones']=conn([{
                'zone':{'id':'gid://shopify/DeliveryZone/2','countries':[{'code':{'countryCode':'US','restOfWorld':False},'provinces':[]}]},
                'methodDefinitions':conn([{'id':'gid://shopify/DeliveryMethodDefinition/1','active':True,
                    'name':'Free shipping','methodConditions':[],
                    'rateProvider':{'__typename':'DeliveryRateDefinition','price':{'amount':'0.00','currencyCode':'USD'}}}])}])
            return {'deliveryProfileUpdate':{'profile':{'id':profile['id']},'userErrors':[]}}
        raise AssertionError('Unexpected Shopify operation')
    client=TestClient(server.app)
    assert client.post('/api/login',json={'password':server.ADMIN_PASSWORD}).status_code==200
    with patch.object(server,'shopify_graphql',graph):
        plan=client.get('/api/shopify/usa-plan')
        assert plan.status_code==200,plan.text
        assert plan.json()['shipping_system']=='delivery_profiles'
        assert plan.json()['manual_steps']==[]
        applied=client.post('/api/shopify/usa-apply',json={'fingerprint':plan.json()['fingerprint']})
        assert applied.status_code==200,applied.text
        assert applied.json()['shipping_verified'] is True
print('Legacy free-shipping setup checks passed')
