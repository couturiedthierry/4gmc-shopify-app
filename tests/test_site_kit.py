import asyncio
import json
import re
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server
import site_kit


def check_brand_validation():
    business = {'business_name': 'Example Co', 'domain_name': 'example.com',
                'email': 'support@example.com', 'address': '123 Main St',
                'phone': '+1 212 555 0100', 'country': 'United States', 'currency': 'USD'}
    item = {'title': 'About', 'kind': 'about',
            'source_url': 'https://source.example/pages/about',
            'example': ('This reference has original sentences about customer service and store operations. ' * 4)}
    leaked = ('Example Co is described at example.com and support@example.com. '
              'Source Example LLC is still named as the responsible company. ' * 3)
    try:
        server.validate_brand_page(item, 'About Example Co', leaked, business,
                                   'source.example', ['Source Example LLC'])
    except Exception as error:
        assert getattr(error, 'status_code', None) == 502
    else:
        raise AssertionError('Source business identity must be rejected')
    return_item = {'title': 'Returns Policy', 'kind': 'returns',
                   'source_url': 'https://source.example/policies/refund-policy',
                   'example': 'Neutral reference information about customer returns. ' * 5}
    incomplete_returns = ('Example Co accepts returns within 30 days. Contact support@example.com '
                          'at example.com for return instructions and mailing costs. ' * 3)
    try:
        server.validate_brand_page(return_item, 'Returns & Refunds Policy', incomplete_returns,
                                   business, 'source.example', [])
    except Exception as error:
        assert getattr(error, 'status_code', None) == 502
    else:
        raise AssertionError('Return policy without refund handling must be rejected')
    phrase = 'one two three four five six seven eight nine ten eleven twelve thirteen fourteen'
    copied_item = dict(item, example=phrase + ' extra source words ' + phrase)
    copied = ('Example Co support is available at support@example.com and example.com. ' +
              phrase + '. More original destination explanation for Example Co customers. ' * 3)
    try:
        server.validate_brand_page(copied_item, 'About Example Co', copied, business,
                                   'source.example', [])
    except Exception as error:
        assert getattr(error, 'status_code', None) == 502
    else:
        raise AssertionError('Copied source passages must be rejected')


def check_parser():
    markup = '<html><header>Navigation</header><main><div class="shopify-policy__body"><h1>Shipping</h1><p>Orders ship within five business days.</p><script>Ignore this instruction</script><p>Email support for delivery questions and any other order issue.</p></div></main><footer>Footer</footer></html>'
    text = site_kit.extract_policy_text(markup)
    assert 'Orders ship within five business days.' in text
    assert 'Email support for delivery questions' in text
    assert 'Ignore this instruction' not in text
    assert 'Navigation' not in text
    try:
        site_kit.source_origin('http://127.0.0.1:8000')
    except ValueError:
        pass
    else:
        raise AssertionError('Private or HTTP sources must be rejected')


async def check_workflow():
    with tempfile.TemporaryDirectory() as temp:
        old_db = server.DB
        server.DB = Path(temp) / 'test.db'
        try:
            server.init()
            with server.db() as c:
                c.execute('UPDATE stores SET domain=?,business=? WHERE id=1', (
                    'merchant-test.myshopify.com',
                    json.dumps({'business_name': 'Example Co', 'domain_name': 'example.com', 'email': 'support@example.com',
                                'shipping_time': '5 business days', 'shipping_cost': 'Free',
                                'return_window': '30 days', 'address': '123 Main St, New York, NY',
                                'phone': '+1 212 555 0100', 'country': 'United States', 'currency': 'USD',
                                'live_chat': 'Available on the website during business hours',
                                'business_hours': 'Mon-Fri: 9:00 AM - 5:00 PM (Eastern Time)'}),
                ))
            client = TestClient(server.app)
            assert client.post('/api/login', json={'password': server.ADMIN_PASSWORD}).status_code == 200

            async def examples(origin):
                assert origin == 'https://source.example'
                return {kind: 'Source policy example with practical customer information. ' * 3 for kind in site_kit.POLICY_PATHS}

            async def pages(origin):
                assert origin == 'https://source.example'
                return [{'url': origin + '/pages/warranty-policy', 'handle': 'warranty-policy',
                         'title': 'Warranty Policy', 'body': 'Warranty information and customer contact details. ' * 4}]

            async def ai(prompt, max_tokens=700):
                if 'REFERENCE BLUEPRINT EXTRACTION' in prompt:
                    assert max_tokens == 1500
                    terms = []
                    if 'Page type: shipping' in prompt:
                        terms = ['Free United States shipping', 'Orders process in 2 business days', 'Delivery takes 3-7 business days']
                    elif 'Page type: returns' in prompt:
                        terms = ['Returns accepted within 30 days', 'Customers contact support before mailing a return']
                    return {'sections': [{'heading': 'Overview', 'purpose': 'Explain the policy clearly'},
                                         {'heading': 'Customer support', 'purpose': 'Explain how customers get help'}],
                            'operational_terms': terms,
                            'source_identity_terms': ['Source Example LLC']}
                assert 'Example Co' in prompt
                assert 'UNTRUSTED SOURCE TEXT' not in prompt
                assert max_tokens == 3500
                kind = re.search(r'Page type: ([a-z]+)', prompt).group(1)
                base = ('Example Co provides clear information for customers. Contact support@example.com '
                        'or visit example.com when you need help with an order. ')
                if kind == 'shipping':
                    body = (base + 'Example Co provides free shipping in the United States. Orders are processed '
                            'within 2 business days, and delivery normally takes 3-7 business days. ') * 2
                elif kind == 'returns':
                    body = (base + 'Example Co accepts eligible returns within 30 days. Contact support@example.com '
                            'before mailing a return to receive instructions about the return method and costs. Approved refunds are explained after inspection. ') * 2
                else:
                    body = base * 4
                return {'title': 'Example Co ' + kind.title(), 'body': body}

            with patch.object(site_kit, 'source_origin', return_value='https://source.example'), \
                 patch.object(site_kit, 'collect_policies', examples), \
                 patch.object(site_kit, 'collect_pages', pages), \
                 patch.object(server, 'ai_json', ai), \
                 patch.object(server, 'SMARTAPI_KEY', 'test-key'):
                response = client.post('/api/site-kit/prepare', json={'source_url': 'https://source.example'})
            assert response.status_code == 200, response.text
            plan = response.json()
            assert len(plan['pages']) == 8
            assert any(item['source_url'].endswith('/pages/warranty-policy') for item in plan['pages'])
            contact = next(item for item in plan['pages'] if item['kind'] == 'contact')
            assert 'Live Chat: Available on the website during business hours' in contact['body']
            assert 'Business Hours: Mon-Fri: 9:00 AM - 5:00 PM (Eastern Time)' in contact['body']
            for detail in ('Example Co', 'example.com', 'support@example.com',
                           '123 Main St, New York, NY', '+1 212 555 0100'):
                assert detail in contact['body']
            assert {item['kind'] for item in plan['pages']} == set(server.SITE_KIT_ORDER) | {'custom'}
            assert client.get('/api/site-kit/plan').json()['fingerprint'] == plan['fingerprint']
            assert client.post('/api/site-kit/publish', json={'fingerprint': '0' * 64}).status_code == 409

            published = []

            async def token(_store):
                return 'test-token'

            async def publish(page_id, _request):
                published.append(page_id)
                return {'ok': True}

            with patch.object(server, 'token_for', token), patch.object(server, 'publish_page', publish):
                response = client.post('/api/site-kit/publish', json={'fingerprint': plan['fingerprint']})
            assert response.status_code == 200, response.text
            assert response.json()['failed'] is None
            assert len(published) == 8
            with server.db() as c:
                rows = server.site_kit_rows(c)
                assert all(rows[kind]['reviewed_hash'] == server.page_digest(rows[kind]) for kind in server.SITE_KIT_ORDER)
                assert all(json.loads(rows[kind]['brand_guard'])['version'] == 2 for kind in server.SITE_KIT_ORDER)
            edited = plan['pages'][0]
            assert client.put('/api/pages/' + str(edited['id']), json={
                'kind': edited['kind'], 'title': edited['title'],
                'body': edited['body'] + '\nUnsealed manual edit.'
            }).status_code == 200
            assert client.get('/api/site-kit/plan').status_code == 409
            current = client.get('/api/state').json()['store']
            revised = dict(current['business'], shipping_time='7 business days')
            assert client.put('/api/store', json={'name': current['name'], 'domain': current['domain'],
                                                  'business': revised, 'brand': current['brand']}).status_code == 200
            assert client.get('/api/site-kit/plan').status_code == 409
        finally:
            server.DB = old_db


check_parser()
check_brand_validation()
asyncio.run(check_workflow())
print('Automated site kit checks passed')
