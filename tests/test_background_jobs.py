import asyncio
import json
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
        server.DB = Path(temp) / 'test.db'
        server.SITE_KIT_JOB_IDS.clear()
        server.SITE_KIT_TASKS.clear()
        try:
            server.init()
            transport = httpx.ASGITransport(app=server.app)
            async with httpx.AsyncClient(transport=transport, base_url='http://testserver') as client:
                assert (await client.post('/api/login', json={'password': server.ADMIN_PASSWORD})).status_code == 200

                calls = []
                async def generated(data, progress=None):
                    calls.append(data.source_url)
                    if progress:
                        progress('Reading reference pages…', 0, 2)
                    await asyncio.sleep(0.08)
                    if progress:
                        progress('Generated 1 of 2 destination-brand pages…', 1, 2)
                    await asyncio.sleep(0.08)
                    return {'pages': [{'id': 1}, {'id': 2}], 'skipped': ['Privacy choices']}

                with patch.object(server, 'generate_site_kit', generated):
                    first = await client.post('/api/site-kit/prepare-job', json={'source_url':'https://source.example'})
                    assert first.status_code == 202, first.text
                    job_id = first.json()['id']
                    assert len(job_id) == 32
                    second = await client.post('/api/site-kit/prepare-job', json={'source_url':'https://source.example'})
                    assert second.status_code == 202
                    assert second.json()['id'] == job_id
                    active = (await client.get('/api/state')).json()['site_kit_job']
                    assert active['id'] == job_id
                    for _ in range(50):
                        status = (await client.get('/api/site-kit/jobs/' + job_id)).json()
                        if status['status'] == 'completed':
                            break
                        await asyncio.sleep(0.02)
                    assert status['status'] == 'completed', status
                    assert status['completed'] == 2 and status['total'] == 2
                    assert status['result']['skipped'] == ['Privacy choices']
                    assert calls == ['https://source.example']
                    assert (await client.get('/api/state')).json()['site_kit_job'] is None

                with server.db() as c:
                    server.ensure_jobs(c)
                    interrupted = 'f' * 32
                    c.execute("INSERT INTO jobs(id,kind,status,progress) VALUES(?,?,?,?)",
                              (interrupted, 'site_kit', 'running', 'Old task'))
                state = (await client.get('/api/state')).json()
                assert state['site_kit_job'] is None
                with server.db() as c:
                    row = c.execute('SELECT status,error FROM jobs WHERE id=?', (interrupted,)).fetchone()
                    assert row['status'] == 'failed'
                    assert 'service restarted' in row['error']
            print('Background page-generation job and restart recovery checks passed')
        finally:
            server.DB = old_db
            server.SITE_KIT_JOB_IDS.clear()
            server.SITE_KIT_TASKS.clear()


asyncio.run(exercise())
