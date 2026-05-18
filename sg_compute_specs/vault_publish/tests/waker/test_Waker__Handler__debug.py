# ═══════════════════════════════════════════════════════════════════════════════
# Waker tests — Waker__Handler debug surface
# Verifies X-Waker-* headers (Layer 1) and structured JSON log (Layer 2) across
# all state-machine paths.  No mocks, no patches.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import sys

from sg_compute_specs.vault_publish.waker.Endpoint__Resolver                     import Endpoint__Resolver
from sg_compute_specs.vault_publish.waker.Waker__Handler                         import Waker__Handler
from sg_compute_specs.vault_publish.waker.schemas.Enum__Instance__State          import Enum__Instance__State
from sg_compute_specs.vault_publish.waker.schemas.Enum__Waker__Action            import Enum__Waker__Action
from sg_compute_specs.vault_publish.waker.schemas.Enum__Waker__State             import Enum__Waker__State
from sg_compute_specs.vault_publish.waker.schemas.Schema__Endpoint__Resolution   import Schema__Endpoint__Resolution
from sg_compute_specs.vault_publish.waker.schemas.Schema__Waker__Request_Context import Schema__Waker__Request_Context


# ── In-memory fakes ───────────────────────────────────────────────────────────

class _Resolver__Fixed(Endpoint__Resolver):
    def __init__(self, state, vault_url='', instance_id='i-test01'):
        self._state       = state
        self._vault_url   = vault_url
        self._instance_id = instance_id
        self._started     = []

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
    def __init__(self, status=200):
        self._status = status

    def proxy(self, vault_url, method, path, headers, body) -> dict:
        return {
            'status_code': self._status,
            'headers'    : {'Content-Type': 'text/html'},
            'body'       : b'vault-content',
        }


def _handler(state, vault_url='', health_ok=True, proxy_status=200,
             version='v-test') -> tuple:
    resolver = _Resolver__Fixed(state, vault_url=vault_url)
    proxy    = _Proxy__Fixed(status=proxy_status)
    h        = Waker__Handler(
        _resolver_factory = lambda: resolver,
        _proxy_factory    = lambda: proxy,
        _version          = version,
    )
    if not health_ok:
        h._health_ok = lambda url: False
    return h, resolver, proxy


def _ctx(slug='sara-cv', host='sara-cv.aws.sg-labs.app',
         request_id='req-123', source_ip='1.2.3.4') -> Schema__Waker__Request_Context:
    return Schema__Waker__Request_Context(
        host       = host,
        slug       = slug,
        path       = '/',
        method     = 'GET',
        request_id = request_id,
        source_ip  = source_ip,
    )


# ── Layer 1: X-Waker-* headers present on every response ─────────────────────

class TestWakerHeaders__Present:
    def test_headers_present_on_404(self):
        h, _, _ = _handler(Enum__Instance__State.UNKNOWN)
        result  = h.handle(_ctx())
        for hdr in ('X-Waker-State', 'X-Waker-Slug', 'X-Waker-Action', 'X-Waker-Elapsed-Ms'):
            assert hdr in result['headers'], f'{hdr} missing from 404 response'

    def test_headers_present_on_warming(self):
        h, _, _ = _handler(Enum__Instance__State.STOPPED)
        result  = h.handle(_ctx())
        for hdr in ('X-Waker-State', 'X-Waker-Slug', 'X-Waker-Action', 'X-Waker-Elapsed-Ms'):
            assert hdr in result['headers'], f'{hdr} missing from warming response'

    def test_headers_present_on_proxy(self):
        h, _, _ = _handler(Enum__Instance__State.RUNNING, vault_url='http://1.2.3.4:8080')
        h._health_ok = lambda url: True
        result = h.handle(_ctx())
        for hdr in ('X-Waker-State', 'X-Waker-Slug', 'X-Waker-Action', 'X-Waker-Elapsed-Ms'):
            assert hdr in result['headers'], f'{hdr} missing from proxied response'

    def test_request_id_in_headers_when_provided(self):
        h, _, _ = _handler(Enum__Instance__State.UNKNOWN)
        result  = h.handle(_ctx(request_id='req-abc'))
        assert result['headers'].get('X-Waker-Request-Id') == 'req-abc'

    def test_version_in_headers(self):
        h, _, _ = _handler(Enum__Instance__State.UNKNOWN, version='v1.2.3')
        result  = h.handle(_ctx())
        assert result['headers'].get('X-Waker-Version') == 'v1.2.3'

    def test_no_request_id_header_when_empty(self):
        h, _, _ = _handler(Enum__Instance__State.UNKNOWN)
        result  = h.handle(Schema__Waker__Request_Context(host='', slug=''))
        assert 'X-Waker-Request-Id' not in result['headers']


# ── Layer 1: state and action values ─────────────────────────────────────────

class TestWakerHeaders__StateAction:
    def test_unknown_slug_state_not_found(self):
        h, _, _ = _handler(Enum__Instance__State.UNKNOWN)
        result  = h.handle(_ctx())
        assert result['headers']['X-Waker-State']  == 'not_found'
        assert result['headers']['X-Waker-Action'] == 'returned-404'

    def test_empty_slug_state_not_found(self):
        h, _, _ = _handler(Enum__Instance__State.UNKNOWN)
        result  = h.handle(Schema__Waker__Request_Context(host='', slug=''))
        assert result['headers']['X-Waker-State']  == 'not_found'
        assert result['headers']['X-Waker-Action'] == 'returned-404'

    def test_stopped_state_started(self):
        h, _, _ = _handler(Enum__Instance__State.STOPPED)
        result  = h.handle(_ctx())
        assert result['headers']['X-Waker-State']  == 'started'
        assert result['headers']['X-Waker-Action'] == 'started-ec2'

    def test_pending_state_warming(self):
        h, _, _ = _handler(Enum__Instance__State.PENDING)
        result  = h.handle(_ctx())
        assert result['headers']['X-Waker-State']  == 'warming'
        assert result['headers']['X-Waker-Action'] == 'returned-warming'

    def test_stopping_state_warming(self):
        h, _, _ = _handler(Enum__Instance__State.STOPPING)
        result  = h.handle(_ctx())
        assert result['headers']['X-Waker-State']  == 'warming'
        assert result['headers']['X-Waker-Action'] == 'returned-warming'

    def test_running_healthy_state_proxied(self):
        h, _, _ = _handler(Enum__Instance__State.RUNNING, vault_url='http://1.2.3.4:8080')
        h._health_ok = lambda url: True
        result = h.handle(_ctx())
        assert result['headers']['X-Waker-State']  == 'proxied'
        assert result['headers']['X-Waker-Action'] == 'proxied'

    def test_running_unhealthy_state_warming(self):
        h, _, _ = _handler(Enum__Instance__State.RUNNING, vault_url='http://1.2.3.4:8080',
                            health_ok=False)
        result = h.handle(_ctx())
        assert result['headers']['X-Waker-State']  == 'warming'
        assert result['headers']['X-Waker-Action'] == 'returned-warming'

    def test_proxy_5xx_state_error(self):
        h, _, _ = _handler(Enum__Instance__State.RUNNING, vault_url='http://1.2.3.4:8080',
                            proxy_status=502)
        h._health_ok = lambda url: True
        result = h.handle(_ctx())
        assert result['headers']['X-Waker-State']  == 'error'
        assert result['headers']['X-Waker-Action'] == 'returned-502'


# ── Layer 1: slug, host, instance-id, ec2-state values ───────────────────────

class TestWakerHeaders__Values:
    def test_slug_header(self):
        h, _, _ = _handler(Enum__Instance__State.UNKNOWN)
        result  = h.handle(_ctx(slug='bob-cv'))
        assert result['headers']['X-Waker-Slug'] == 'bob-cv'

    def test_host_header(self):
        h, _, _ = _handler(Enum__Instance__State.UNKNOWN)
        result  = h.handle(_ctx(host='bob-cv.aws.sg-labs.app'))
        assert result['headers']['X-Waker-Host'] == 'bob-cv.aws.sg-labs.app'

    def test_instance_id_header_on_stopped(self):
        h, _, _ = _handler(Enum__Instance__State.STOPPED)
        result  = h.handle(_ctx())
        assert result['headers']['X-Waker-Instance-Id'] == 'i-test01'

    def test_instance_id_empty_when_unknown(self):
        resolver = _Resolver__Fixed(Enum__Instance__State.UNKNOWN, instance_id='')
        h = Waker__Handler(_resolver_factory=lambda: resolver, _version='v-test')
        result = h.handle(_ctx())
        assert result['headers']['X-Waker-Instance-Id'] == ''

    def test_ec2_state_header_reflects_resolved_state(self):
        h, _, _ = _handler(Enum__Instance__State.STOPPED)
        result  = h.handle(_ctx())
        assert result['headers']['X-Waker-Ec2-State'] == 'stopped'

    def test_elapsed_ms_is_numeric_string(self):
        h, _, _ = _handler(Enum__Instance__State.UNKNOWN)
        result  = h.handle(_ctx())
        elapsed = result['headers']['X-Waker-Elapsed-Ms']
        assert elapsed.isdigit(), f'expected numeric, got {elapsed!r}'


# ── Layer 2: structured JSON log ──────────────────────────────────────────────

class TestWakerLog:
    def _handle_and_capture(self, h, ctx, capsys):
        h.handle(ctx)
        return json.loads(capsys.readouterr().out.strip())

    def test_log_emitted_once_per_handle(self, capsys):
        h, _, _ = _handler(Enum__Instance__State.UNKNOWN)
        h.handle(_ctx())
        out = capsys.readouterr().out.strip()
        lines = [l for l in out.splitlines() if l]
        assert len(lines) == 1

    def test_log_is_valid_json(self, capsys):
        h, _, _ = _handler(Enum__Instance__State.UNKNOWN)
        h.handle(_ctx())
        log = json.loads(capsys.readouterr().out)
        assert isinstance(log, dict)

    def test_log_contains_required_keys(self, capsys):
        h, _, _ = _handler(Enum__Instance__State.UNKNOWN)
        h.handle(_ctx())
        log = json.loads(capsys.readouterr().out)
        for key in ('ts', 'slug', 'host', 'method', 'path', 'state',
                    'action', 'status', 'elapsed_ms'):
            assert key in log, f'missing key {key!r}'

    def test_log_slug_matches_ctx(self, capsys):
        h, _, _ = _handler(Enum__Instance__State.UNKNOWN)
        h.handle(_ctx(slug='alice-cv'))
        log = json.loads(capsys.readouterr().out)
        assert log['slug'] == 'alice-cv'

    def test_log_state_matches_header(self, capsys):
        h, _, _ = _handler(Enum__Instance__State.STOPPED)
        result  = h.handle(_ctx())
        log     = json.loads(capsys.readouterr().out)
        assert log['state'] == result['headers']['X-Waker-State']

    def test_log_request_id(self, capsys):
        h, _, _ = _handler(Enum__Instance__State.UNKNOWN)
        h.handle(_ctx(request_id='req-xyz'))
        log = json.loads(capsys.readouterr().out)
        assert log['request_id'] == 'req-xyz'

    def test_log_source_ip(self, capsys):
        h, _, _ = _handler(Enum__Instance__State.UNKNOWN)
        h.handle(_ctx(source_ip='9.8.7.6'))
        log = json.loads(capsys.readouterr().out)
        assert log['source_ip'] == '9.8.7.6'

    def test_log_version(self, capsys):
        h, _, _ = _handler(Enum__Instance__State.UNKNOWN, version='v-42')
        h.handle(_ctx())
        log = json.loads(capsys.readouterr().out)
        assert log['version'] == 'v-42'

    def test_log_elapsed_ms_non_negative(self, capsys):
        h, _, _ = _handler(Enum__Instance__State.UNKNOWN)
        h.handle(_ctx())
        log = json.loads(capsys.readouterr().out)
        assert log['elapsed_ms'] >= 0
