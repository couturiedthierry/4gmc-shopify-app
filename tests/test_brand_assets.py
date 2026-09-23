import base64
import io
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


def image_b64(fmt='PNG', size=(32, 24), color=(72, 115, 220, 255)):
    image = Image.new('RGBA', size, color)
    output = io.BytesIO()
    image.save(output, format=fmt)
    return base64.b64encode(output.getvalue()).decode(), output.getvalue()


with tempfile.TemporaryDirectory() as temp:
    old_db = server.DB
    server.DB = Path(temp) / 'test.db'
    try:
        server.init()
        client = TestClient(server.app)
        assert client.post('/api/login', json={'password': server.ADMIN_PASSWORD}).status_code == 200

        encoded, raw = image_b64()
        uploaded = client.put('/api/store/brand-asset', json={
            'kind': 'logo', 'filename': 'brand-logo.png',
            'content_type': 'image/png', 'data': encoded,
        })
        assert uploaded.status_code == 200, uploaded.text
        state = client.get('/api/state').json()
        assert state['store']['brand']['logo']['filename'] == 'brand-logo.png'
        assert state['store']['brand']['logo']['digest']
        response = client.get('/api/store/brand-assets/logo')
        assert response.status_code == 200
        assert response.content == raw
        assert response.headers['content-type'].startswith('image/png')

        dark_encoded, dark_raw = image_b64(color=(10, 10, 10, 255))
        dark_uploaded = client.put('/api/store/brand-asset', json={
            'kind': 'logo_dark', 'filename': 'brand-logo-dark.png',
            'content_type': 'image/png', 'data': dark_encoded,
        })
        assert dark_uploaded.status_code == 200, dark_uploaded.text
        state = client.get('/api/state').json()
        assert state['store']['brand']['logo_dark']['filename'] == 'brand-logo-dark.png'
        assert state['store']['brand']['logo_dark']['digest']
        dark_response = client.get('/api/store/brand-assets/logo_dark')
        assert dark_response.status_code == 200
        assert dark_response.content == dark_raw

        saved = client.put('/api/store', json={
            'name': state['store']['name'], 'domain': state['store']['domain'],
            'business': state['store']['business'],
            'brand': {'color': '#112233', 'accent': '#445566'},
        })
        assert saved.status_code == 200, saved.text
        state = client.get('/api/state').json()
        assert state['store']['brand']['logo']['digest']
        assert state['store']['brand']['logo_dark']['digest']
        assert state['store']['brand']['color'] == '#112233'

        invalid = base64.b64encode(b'<html>not an image</html>').decode()
        rejected = client.put('/api/store/brand-asset', json={
            'kind': 'favicon', 'filename': 'bad.png',
            'content_type': 'image/png', 'data': invalid,
        })
        assert rejected.status_code == 400

        created = client.post('/api/stores', json={
            'domain': 'brand-two.myshopify.com',
            'client_id': 'brand-client-two', 'client_secret': 'brand-secret-two',
        })
        assert created.status_code == 200, created.text
        second_id = created.json()['id']
        assert client.get('/api/store/brand-assets/logo').status_code == 404
        assert client.get('/api/store/brand-assets/logo_dark').status_code == 404

        favicon_data, favicon_raw = image_b64(size=(16, 16), color=(130, 100, 230, 255))
        favicon = client.put('/api/store/brand-asset', json={
            'kind': 'favicon', 'filename': 'favicon.png',
            'content_type': 'image/png', 'data': favicon_data,
        })
        assert favicon.status_code == 200, favicon.text
        assert client.get('/api/store/brand-assets/favicon').content == favicon_raw

        assert client.post('/api/stores/1/select').status_code == 200
        assert client.get('/api/store/brand-assets/logo').content == raw
        assert client.get('/api/store/brand-assets/logo_dark').content == dark_raw
        assert client.get('/api/store/brand-assets/favicon').status_code == 404
        assert client.post('/api/stores/' + str(second_id) + '/select').status_code == 200
        assert client.get('/api/store/brand-assets/logo').status_code == 404
        assert client.get('/api/store/brand-assets/logo_dark').status_code == 404
        assert client.get('/api/store/brand-assets/favicon').content == favicon_raw
        print('Per-store logo and favicon upload checks passed')
    finally:
        server.DB = old_db
