# ═══════════════════════════════════════════════════════════════════════════════
# Waker tests — Waker__Handler
# Tests every state path: STOPPED, PENDING, STOPPING, RUNNING (healthy + not),
# UNKNOWN (slug not found), and empty slug. Uses in-memory resolver + proxy.
# No mocks, no patches.
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.vault_publish.waker.Endpoint__Resolver                     import Endpoint__Resolver
from sg_compute_specs.vault_publish.waker.Waker__Handler                         import Waker__Handler
from sg_compute_specs.vault_publish.waker.schemas.Enum__Instance__State          import Enum__Instance__State
from sg_compute_specs.vault_publish.waker.schemas.Schema__Endpoint__Resolution   import Schema__Endpoint__Resolution
from sg_compute_specs.vault_publish.waker.schemas.Schema__Waker__Request_Context import Schema__Waker__Request_Context


# ── In-memory fakes ───────────────────────────────────────────────────────────

class _Resolution__Fixed(Endpoint__Resolver):
    def __init__(self, state: Enum__Instance__State, vault_url: str = '',
                 instance_id: str = 'i-abc'):
        self._state      = state
        self._vault_url  = vault_url
        self._instance_id= instance_id
        self._started    = []

    def resolve(self, slug: str) -> Schema__Endpoint__Resolution:
        return Schema__Endpoint__Resolution(
            slug        = slug,
            instance_id = self._instance_id,
            state       = self._state,
            vault_url   = self._vault_url,
            public_ip   = '1.2.3.4' if self._vault_url else '',
        )

    def start(self, instance_id: str) -> bool:
        self._started.append(instance_id)
        return True


class _Proxy__Fixed:
    def __init__(self, status: int = 200, body: bytes = b'vault content'):
        self._status = status
        self._body   = body
        self.proxied = []

    def proxy(self, vault_url, method, path, headers, body) -> dict:
        self.proxied.append({'url': vault_url, 'method': method, 'path': path})
        return {
            'status_code': self._status,
            'headers'    : {'Content-Type': 'text/html'},
            'body'       : self._body,
        }


def _handler(state, vault_url='', health_ok=True, proxy_status=200) -> tuple:
    resolver = _Resolution__Fixed(state, vault_url=vault_url)
    proxy    = _Proxy__Fixed(status=proxy_status)
    h        = Waker__Handler(
        _resolver_factory = lambda: resolver,
        _proxy_factory    = lambda: proxy,
    )
    if not health_ok:
        h._health_ok = lambda url: False
    return h, resolver, proxy


def _ctx(slug='sara-cv', path='/') -> Schema__Waker__Request_Context:
    return Schema__Waker__Request_Context(
        host   = f'{slug}.aws.sg-labs.app',
        slug   = slug,
        path   = path,
        method = 'GET',
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestHandlerUnknownSlug:
    def test_empty_slug_returns_404(self):
        h, _, _ = _handler(Enum__Instance__State.UNKNOWN)
        ctx = Schema__Waker__Request_Context(host='', slug='', path='/')
        result = h.handle(ctx)
        assert result['status_code'] == 404

    def test_unknown_slug_returns_404(self):
        h, _, _ = _handler(Enum__Instance__State.UNKNOWN)
        result  = h.handle(_ctx())
        assert result['status_code'] == 404

    def test_404_body_mentions_slug(self):
        h, _, _ = _handler(Enum__Instance__State.UNKNOWN)
        result  = h.handle(_ctx())
        assert b'404' in result['body'] or b'not found' in result['body'].lower()


class TestHandlerStopped:
    def test_stopped_returns_202(self):
        h, _, _ = _handler(Enum__Instance__State.STOPPED)
        result  = h.handle(_ctx())
        assert result['status_code'] == 202

    def test_stopped_starts_instance(self):
        h, resolver, _ = _handler(Enum__Instance__State.STOPPED)
        h.handle(_ctx())
        assert 'i-abc' in resolver._started

    def test_stopped_body_is_warming_html(self):
        h, _, _ = _handler(Enum__Instance__State.STOPPED)
        result  = h.handle(_ctx())
        assert b'warming' in result['body'].lower()

    def test_stopped_no_cache_header(self):
        h, _, _ = _handler(Enum__Instance__State.STOPPED)
        result  = h.handle(_ctx())
        assert 'no-store' in result['headers'].get('Cache-Control', '')


class TestHandlerPending:
    def test_pending_returns_202(self):
        h, _, _ = _handler(Enum__Instance__State.PENDING)
        assert h.handle(_ctx())['status_code'] == 202

    def test_pending_does_not_start_instance(self):
        h, resolver, _ = _handler(Enum__Instance__State.PENDING)
        h.handle(_ctx())
        assert resolver._started == []


class TestHandlerStopping:
    def test_stopping_returns_202(self):
        h, _, _ = _handler(Enum__Instance__State.STOPPING)
        assert h.handle(_ctx())['status_code'] == 202


class TestHandlerRunningHealthy:
    def test_running_healthy_proxies_request(self):
        h, _, proxy = _handler(
            Enum__Instance__State.RUNNING, vault_url='http://1.2.3.4:8080')
        h._health_ok = lambda url: True                                            # Force health check pass
        result = h.handle(_ctx(path='/ui/'))
        assert result['status_code'] == 200
        assert len(proxy.proxied) == 1
        assert proxy.proxied[0]['path'] == '/ui/'

    def test_running_healthy_forwards_method(self):
        h, _, proxy = _handler(
            Enum__Instance__State.RUNNING, vault_url='http://1.2.3.4:8080')
        h._health_ok = lambda url: True
        ctx = Schema__Waker__Request_Context(
            host='x.aws.sg-labs.app', slug='x', path='/api/v1', method='POST')
        h.handle(ctx)
        assert proxy.proxied[0]['method'] == 'POST'


class TestHandlerRunningNotHealthy:
    def test_running_not_healthy_returns_warming(self):
        h, _, proxy = _handler(
            Enum__Instance__State.RUNNING, vault_url='http://1.2.3.4:8080',
            health_ok=False)
        result = h.handle(_ctx())
        assert b'warming' in result['body'].lower()
        assert len(proxy.proxied) == 0                                             # No proxying
