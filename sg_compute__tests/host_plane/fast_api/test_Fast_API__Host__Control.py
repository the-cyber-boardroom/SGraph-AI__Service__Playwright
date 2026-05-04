# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Fast_API__Host__Control (TestClient integration)
# Follows the pattern of test_Fast_API__SP__CLI.py.
# Requires osbot_fast_api_serverless — skipped when not installed.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import pytest

try:
    from sg_compute.host_plane.fast_api.Fast_API__Host__Control import Fast_API__Host__Control
    FAST_API_AVAILABLE = True
except ImportError:
    FAST_API_AVAILABLE = False

pytestmark = pytest.mark.skipif(not FAST_API_AVAILABLE,
                                 reason='osbot_fast_api_serverless not installed')

API_KEY = 'test-host-control-key'
HEADERS = {'X-API-Key': API_KEY}


@pytest.fixture(scope='module')
def client():
    os.environ['FAST_API__AUTH__API_KEY__NAME']  = 'X-API-Key'
    os.environ['FAST_API__AUTH__API_KEY__VALUE'] = API_KEY
    app = Fast_API__Host__Control().setup()
    yield app.client()
    os.environ.pop('FAST_API__AUTH__API_KEY__NAME',  None)
    os.environ.pop('FAST_API__AUTH__API_KEY__VALUE', None)


# ── Auth ──────────────────────────────────────────────────────────────────────

def test_missing_api_key__returns_401(client):
    r = client.get('/host/status')
    assert r.status_code == 401

def test_wrong_api_key__returns_401(client):
    r = client.get('/host/status', headers={'X-API-Key': 'wrong-key'})
    assert r.status_code == 401

# ── Host status ───────────────────────────────────────────────────────────────

def test_host_status__200(client):
    r = client.get('/host/status', headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert 'cpu_percent'    in body
    assert 'mem_total_mb'   in body
    assert 'disk_total_gb'  in body
    assert 'uptime_seconds' in body
    assert 'pod_count'      in body

def test_host_runtime__200(client):
    r = client.get('/host/runtime', headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert 'runtime' in body
    assert 'version' in body

# ── Boot log ──────────────────────────────────────────────────────────────────

def test_host_boot_log__200(client):
    r = client.get('/host/logs/boot', headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert 'source'    in body
    assert 'lines'     in body
    assert 'content'   in body
    assert 'truncated' in body

def test_host_boot_log__lines_param(client):
    r = client.get('/host/logs/boot?lines=50', headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body['lines'] <= 50

# ── Pods ──────────────────────────────────────────────────────────────────────

def test_list_pods__empty_ok(client):
    r = client.get('/pods/list', headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert 'pods'  in body
    assert 'count' in body

def test_get_pod__not_found__404(client):
    r = client.get('/pods/nonexistent-pod', headers=HEADERS)
    assert r.status_code == 404

def test_get_pod_logs__not_found__404(client):
    r = client.get('/pods/nonexistent-pod/logs', headers=HEADERS)
    assert r.status_code == 404

def test_get_pod_stats__not_found__404(client):
    r = client.get('/pods/nonexistent-pod/stats', headers=HEADERS)
    assert r.status_code == 404

# ── Shell ─────────────────────────────────────────────────────────────────────

def test_shell_execute__allowlisted__200(client):
    r = client.post('/host/shell/execute', headers=HEADERS,
                    json={'command': 'df -h', 'timeout': 10})
    assert r.status_code == 200
    body = r.json()
    assert 'stdout'    in body
    assert 'exit_code' in body
    assert 'timed_out' in body

def test_shell_execute__disallowed__422(client):
    r = client.post('/host/shell/execute', headers=HEADERS,
                    json={'command': 'rm -rf /', 'timeout': 5})
    assert r.status_code in (422, 400)

def test_shell_execute__empty_command__422(client):
    r = client.post('/host/shell/execute', headers=HEADERS,
                    json={'command': '', 'timeout': 5})
    assert r.status_code in (422, 400)

# ── CORS ──────────────────────────────────────────────────────────────────────

def test_cors__options_preflight__200(client):
    r = client.options('/pods/list',
                       headers={'Origin'                         : 'http://localhost:10071',
                                'Access-Control-Request-Method'  : 'GET'                   ,
                                'Access-Control-Request-Headers' : 'X-API-Key'             })
    assert r.status_code in (200, 204)
    assert r.headers.get('access-control-allow-origin') == '*'
    assert r.headers.get('access-control-allow-headers') in ('*', 'X-API-Key', 'x-api-key')

def test_cors__response_includes_acao_header(client):
    r = client.get('/host/status', headers={**HEADERS, 'Origin': 'http://localhost:10071'})
    assert r.status_code == 200
    assert r.headers.get('access-control-allow-origin') == '*'

# ── Docs auth ─────────────────────────────────────────────────────────────────

def test_docs_auth__returns_html_with_key(client):
    r = client.get('/docs-auth?apikey=test-key-abc')
    assert r.status_code == 200
    assert 'text/html' in r.headers['content-type']
    assert '"test-key-abc"' in r.text
    assert 'X-API-Key'         in r.text
    assert 'requestInterceptor' in r.text

def test_docs_auth__no_key(client):
    r = client.get('/docs-auth')
    assert r.status_code == 200
    assert '""' in r.text                                                    # empty string for apiKey

def test_docs_auth__no_auth_required(client):
    r = client.get('/docs-auth')                                             # No X-API-Key header
    assert r.status_code == 200                                              # Unauthenticated access allowed

def test_docs_auth__not_in_openapi_schema(client):
    r = client.get('/openapi.json', headers=HEADERS)
    assert r.status_code == 200
    paths = r.json().get('paths', {})
    assert '/docs-auth' not in paths
