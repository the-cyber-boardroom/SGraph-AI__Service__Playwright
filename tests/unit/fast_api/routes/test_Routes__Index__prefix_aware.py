# ═══════════════════════════════════════════════════════════════════════════════
# Tests — console asset/component/fetch URLs are root_path-aware (Decision #11)
#
# v0.2.64 dev pack — brief 08 §6 acceptance check (and the runnable, no-browser
# sibling of the CI `test_4__index_prefix_aware` Docker check in brief 06 §5).
#
# The console must work identically standalone at root and behind the `/pw`
# reverse proxy. Concretely:
#   • standalone (no X-Forwarded-Prefix, root_path=/)   → window.API_BASE == ''
#   • behind the proxy (X-Forwarded-Prefix: /pw)         → window.API_BASE == '/pw'
#   • NO absolute-rooted asset URL (/components/..., /api/specs/...) ever appears
#     (brief 08 §4 — those resolve to host/... not host/pw/... and 404 behind /pw)
#   • the only external asset is CDN-absolute (https://dev.tools.sgraph.ai/...),
#     which is prefix-independent (brief 08 rule b)
#
# Rendered via the Routes__Index().index(_FakeRequest()).body.decode() pattern —
# no route scan, no Chromium. A failure of the prefix seam is a BAD failure
# (the console silently breaks behind the proxy), so it is guarded here AND by
# the CI image check before publish.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import re
from unittest                                                               import TestCase

from sg_compute_specs.playwright.core.consts.env_vars                       import ENV_VAR__DEPLOYMENT_TARGET, ENV_VAR__ROOT_PATH
from sg_compute_specs.playwright.core.fast_api.routes.Routes__Index         import Routes__Index


_API_KEY_NAME  = 'FAST_API__AUTH__API_KEY__NAME'
_API_KEY_VALUE = 'FAST_API__AUTH__API_KEY__VALUE'


class _EnvScrub:                                                            # scrub env that steers the resolved prefix so rendering is deterministic
    KEYS = (ENV_VAR__DEPLOYMENT_TARGET, _API_KEY_NAME, _API_KEY_VALUE, ENV_VAR__ROOT_PATH)
    def __init__(self, **overrides):
        self.overrides = overrides
        self.snapshot  = {}
    def __enter__(self):
        for k in self.KEYS:
            self.snapshot[k] = os.environ.pop(k, None)
        for k, v in self.overrides.items():
            os.environ[k] = v
        return self
    def __exit__(self, *exc):
        for k in self.KEYS:
            os.environ.pop(k, None)
            if self.snapshot.get(k) is not None:
                os.environ[k] = self.snapshot[k]


class _FakeRequest:                                                         # only .headers.get is used by Root_Path__Resolver
    def __init__(self, headers: dict = None):
        self.headers = headers or {}


def _render(headers: dict = None) -> str:
    return Routes__Index().index(_FakeRequest(headers)).body.decode()


def _api_base(html: str) -> str:
    m = re.search(r'window\.API_BASE\s*=\s*"([^"]*)"', html)
    assert m is not None, 'window.API_BASE assignment not found in rendered HTML'
    return m.group(1)


class test_Routes__Index__prefix_aware(TestCase):

    def test__api_base_is_empty_at_root(self):                              # SG_PLAYWRIGHT__ROOT_PATH=/ is the explicit "served at root" signal
        with _EnvScrub(**{ENV_VAR__ROOT_PATH: '/'}):
            html = _render()
        assert _api_base(html) == '', f'Expected empty API_BASE at root, got {_api_base(html)!r}'

    def test__api_base_carries_prefix_behind_proxy(self):                   # X-Forwarded-Prefix wins (highest precedence)
        with _EnvScrub():
            html = _render({'X-Forwarded-Prefix': '/pw'})
        assert _api_base(html) == '/pw', f'Expected /pw API_BASE behind proxy, got {_api_base(html)!r}'

    def test__no_absolute_rooted_asset_urls_behind_proxy(self):             # brief 08 §4 — forbidden styles break behind /pw
        with _EnvScrub():
            html = _render({'X-Forwarded-Prefix': '/pw'})
        forbidden = re.findall(r'(?:src|href)\s*=\s*"(/(?:components|api/specs)/[^"]*)"', html)
        assert not forbidden, f'Absolute-rooted asset URLs present (break behind /pw): {forbidden}'

    def test__only_external_asset_is_cdn_absolute(self):                    # every src/href is data:, an http(s) CDN URL, or relative — never absolute-rooted
        with _EnvScrub():
            html = _render({'X-Forwarded-Prefix': '/pw'})
        for url in re.findall(r'(?:src|href)\s*=\s*"([^"]+)"', html):
            if url.startswith('data:') or url.startswith('${') or 'inline_b64' in url or 'screenshot_b64' in url:
                continue                                                    # inline image renders, not asset fetches
            if url.startswith('http://') or url.startswith('https://'):
                continue                                                    # CDN-absolute is prefix-independent (brief 08 rule b)
            assert not url.startswith('/'), f'Absolute-rooted asset URL would break behind /pw: {url!r}'
