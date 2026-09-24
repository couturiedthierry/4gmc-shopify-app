import asyncio
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


async def exercise():
    with tempfile.TemporaryDirectory() as temp:
        old_db = server.DB
        old_client_id, old_client_secret = server.SHOPIFY_CLIENT_ID, server.SHOPIFY_CLIENT_SECRET
        old_smartapi, old_gemini = server.SMARTAPI_KEY, server.GEMINI_API_KEY
        server.DB = Path(temp) / 'test.db'
        server.SHOPIFY_CLIENT_ID = 'shared-client'
        server.SHOPIFY_CLIENT_SECRET = 'shared-secret'
        server.SMARTAPI_KEY = 'smart-test'
        server.GEMINI_API_KEY = 'gemini-test'
        server.SITE_KIT_JOB_IDS.clear()
        server.SITE_KIT_TASKS.clear()
        server.SITE_KIT_LOCKS.clear()
        server.TASKS_RUNNING = 0
        try:
            server.init()
            transport = httpx.ASGITransport(app=server.app)
            async with httpx.AsyncClient(transport=transport, base_url='http://testserver') as client:
                assert (await client.post('/api/login', json={'password': server.ADMIN_PASSWORD})).status_code == 200
                capacity = await client.put('/api/settings/task-capacity', json={'value': 4})
                assert capacity.status_code == 200 and capacity.json()['value'] == 4

                calls, stores_started = [], set()
                both_started = asyncio.Event()

                async def generated(data, progress=None):
                    store_id = server.ACTIVE_STORE_ID.get()
                    calls.append((store_id, data.source_url))
                    stores_started.add(store_id)
                    if len(stores_started) >= 2:
                        both_started.set()
                    if progress:
                        progress('Reading reference pages…', 0, 2)
                    await asyncio.wait_for(both_started.wait(), timeout=2)
                    if progress:
                        progress('Generated 1 of 2 destination-brand pages…', 1, 2)
                    await asyncio.sleep(0.05)
                    return {'pages': [{'id': 1}, {'id': 2}], 'skipped': ['Privacy choices']}

                with patch.object(server, 'generate_site_kit', generated):
                    first = await client.post('/api/site-kit/prepare-job', json={'source_url':'https://source-one.example'})
                    assert first.status_code == 202, first.text
                    first_id = first.json()['id']
                    assert first.json()['store_id'] == 1 and len(first_id) == 32

                    duplicate = await client.post('/api/site-kit/prepare-job', json={'source_url':'https://source-one.example'})
                    assert duplicate.status_code == 202 and duplicate.json()['id'] == first_id

                    added = await client.post('/api/stores', json={'domain':'parallel-two.myshopify.com'})
                    assert added.status_code == 200, added.text
                    second_store_id = added.json()['id']
                    second = await client.post('/api/site-kit/prepare-job', json={'source_url':'https://source-two.example'})
                    assert second.status_code == 202, second.text
                    second_id = second.json()['id']
                    assert second.json()['store_id'] == second_store_id

                    listing = (await client.get('/api/jobs')).json()
                    assert listing['capacity'] == 4
                    assert {first_id, second_id}.issubset({job['id'] for job in listing['jobs']})

                    statuses = {}
                    for _ in range(100):
                        statuses = {
                            first_id: (await client.get('/api/jobs/' + first_id)).json(),
                            second_id: (await client.get('/api/jobs/' + second_id)).json(),
                        }
                        if all(item['status'] == 'completed' for item in statuses.values()):
                            break
                        await asyncio.sleep(0.02)
                    assert all(item['status'] == 'completed' for item in statuses.values()), statuses
                    assert all(item['completed'] == 2 and item['total'] == 2 for item in statuses.values())
                    assert {source for _, source in calls} == {'https://source-one.example', 'https://source-two.example'}
                    assert stores_started == {1, second_store_id}
                    assert server.TASKS_RUNNING == 0

                    changed = await client.put('/api/settings/task-capacity', json={'value': 6})
                    assert changed.status_code == 200 and changed.json()['value'] == 6
                    assert (await client.get('/api/jobs')).json()['capacity'] == 6

                selected_first = await client.post('/api/stores/1/select')
                assert selected_first.status_code == 200
                with server.db() as c:
                    store = server.store_row(c)
                    brand = server.json.loads(store['brand'])
                    brand['logo'] = {'digest': 'test-logo', 'extension': 'png', 'content_type': 'image/png'}
                    c.execute('UPDATE stores SET brand=? WHERE id=1', (server.json.dumps(brand),))

                product_calls = []

                async def curated(data, request):
                    assert request is None and server.BACKGROUND_JOB.get() is True
                    assert getattr(data, 'max_products', 20) == 20
                    return {'source_url': data.source_url, 'currency': 'USD',
                            'urls': [data.source_url + '/products/one', data.source_url + '/products/two'],
                            'categories': ['Tools'], 'discovered': 12, 'scanned': 12, 'omitted': 10}

                async def published(data, request):
                    assert request is None and server.BACKGROUND_JOB.get() is True
                    product_calls.append(data.url)
                    await asyncio.sleep(0.02)
                    return {'id': len(product_calls), 'title': data.url.rsplit('/', 1)[-1].title()}

                with patch.object(server, 'store_connected', return_value=True), \
                     patch.object(server, 'source_catalog', curated), \
                     patch.object(server, 'auto_publish_source_product', published):
                    catalog = await client.post('/api/products/catalog-job',
                                                json={'source_url': 'https://catalog.example'})
                    assert catalog.status_code == 202, catalog.text
                    catalog_id = catalog.json()['id']
                    duplicate_catalog = await client.post('/api/products/catalog-job',
                                                          json={'source_url': 'https://catalog.example'})
                    assert duplicate_catalog.status_code == 202
                    assert duplicate_catalog.json()['id'] == catalog_id
                    catalog_status = {}
                    for _ in range(100):
                        catalog_status = (await client.get('/api/jobs/' + catalog_id)).json()
                        if catalog_status['status'] == 'completed':
                            break
                        await asyncio.sleep(0.02)
                    assert catalog_status['status'] == 'completed', catalog_status
                    assert catalog_status['completed'] == 2 and catalog_status['total'] == 2
                    assert len(catalog_status['result']['published']) == 2
                    assert len(product_calls) == 2

                with server.db() as c:
                    server.ensure_jobs(c)
                    interrupted = 'f' * 32
                    c.execute("INSERT INTO jobs(id,kind,status,progress) VALUES(?,?,?,?)",
                              (interrupted, 'site_kit', 'running', 'Old task'))
                state = (await client.get('/api/state')).json()
                assert state['site_kit_job'] is None
                assert state['task_capacity'] == 6
                assert len(state['jobs']) >= 3
                with server.db() as c:
                    row = c.execute('SELECT status,error FROM jobs WHERE id=?', (interrupted,)).fetchone()
                    assert row['status'] == 'failed'
                    assert 'service restarted' in row['error']
            print('Parallel multi-store task jobs, progress, capacity, and restart recovery checks passed')
        finally:
            server.DB = old_db
            server.SHOPIFY_CLIENT_ID, server.SHOPIFY_CLIENT_SECRET = old_client_id, old_client_secret
            server.SMARTAPI_KEY, server.GEMINI_API_KEY = old_smartapi, old_gemini
            server.SITE_KIT_JOB_IDS.clear()
            server.SITE_KIT_TASKS.clear()
            server.SITE_KIT_LOCKS.clear()
            server.TASKS_RUNNING = 0


asyncio.run(exercise())
