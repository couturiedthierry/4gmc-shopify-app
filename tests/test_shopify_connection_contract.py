import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


source = (Path(__file__).resolve().parents[1] / 'static' / 'app.js').read_text(encoding='utf-8')
assert 'name="client_id"' not in source
assert 'name="client_secret"' not in source
assert "launchParams.has('shop')&&launchParams.has('host')" in source
assert 'Legacy install flow enabled' in source

access, refresh, expires_at, refresh_expires_at = server.token_pair({
    'access_token': 'permanent-token',
})
assert (access, refresh, expires_at, refresh_expires_at) == ('permanent-token', '', 0, 0)
print('Shared app credentials and Shopify launch diagnostics checks passed')
