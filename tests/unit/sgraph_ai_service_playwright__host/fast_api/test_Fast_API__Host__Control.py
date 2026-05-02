# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Fast_API__Host__Control (TestClient integration)
# Follows the pattern of test_Fast_API__SP__CLI.py.
# Requires osbot_fast_api_serverless — skipped when not installed.
# ══════════════════════════════════════════════════════════════════════��════════

import os
import pytest

try:
    from sgraph_ai_service_playwright__host.fast_api.Fast_API__Host__Control import Fast_API__Host__Control
    FAST_API_AVAILABLE = True
except ImportError:
    FAST_API_AVAILABLE = False

pytestmark = pytest.mark.skipif(not FAST_API_AVAILABLE,
                                 reason='osbot_fast_api_serverless not installed')

API_KEY = 'test-host-control-key'
HEADERS = {'X-API-Key': API_KEY}


@pytest.fixture(scope='module')
def client():
    os.environ['FAST_API__AUTH__API_KEY__VALUE'] = API_KEY
    app = Fast_API__Host__Control().setup()
    yield app.client()
    os.environ.pop('FAST_API__AUTH__API_KEY__VALUE', None)


# ── Auth ──────────────────────────────────────────────���───────────────────────

def test_missing_api_key__returns_401(client):
    r = client.get('/host/status')
    assert r.status_code == 401

def test_wrong_api_key__returns_401(client):
    r = client.get('/host/status', headers={'X-API-Key': 'wrong-key'})
    assert r.status_code == 401

# ── Host status ──────────────────────────────���───────────────────────────────���

def test_host_status__200(client):
    r = client.get('/host/status', headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert 'cpu_percent'     in body
    assert 'mem_total_mb'    in body
    assert 'disk_total_gb'   in body
    assert 'uptime_seconds'  in body
    assert 'container_count' in body

def test_host_runtime__200(client):
    r = client.get('/host/runtime', headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert 'runtime' in body
    assert 'version' in body

# ── Containers ────────────────────────────────────────────────────────────────

def test_list_containers__empty_ok(client):
    r = client.get('/containers/list', headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert 'containers' in body
    assert 'count'      in body

def test_get_container__not_found__404(client):
    r = client.get('/containers/nonexistent-container', headers=HEADERS)
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
    assert r.status_code in (422, 400)   # validation error from Safe_Str__Shell__Command

def test_shell_execute__empty_command__422(client):
    r = client.post('/host/shell/execute', headers=HEADERS,
                    json={'command': '', 'timeout': 5})
    assert r.status_code in (422, 400)
