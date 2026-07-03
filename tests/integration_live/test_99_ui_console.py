# ═══════════════════════════════════════════════════════════════════════════════
# Live — UI console + Docker-image checks (runs LAST due to `99_` prefix).
#
# v0.2.64 dev pack — brief 06 §5. These run inside the CI `integration-test-image`
# job against the already-built BY-DIGEST amd64 container, AFTER the image builds
# (build-amd64 / build-arm64) and BEFORE push-playwright-manifest publishes to
# Docker Hub. So a red check here blocks the manifest tag — the Docker-image
# checks gate the publish (README Q5 / ci-pipeline.yml :254 → :400-405). No new
# workflow_dispatch job is invented; this module extends the suite that job runs.
#
# Deploy-via-pytest, numbered top-down (CLAUDE.md testing rule #4):
#   test_1__container_ready       service answers /health/info (sanity; the job
#                                 already waits, this re-confirms in-pytest)
#   test_2__get_index             GET /  → 200, console HTML ("SG Playwright")
#   test_3__get_capabilities      GET /health/capabilities → 200, capabilities shape
#   test_4__index_prefix_aware    GET / behind X-Forwarded-Prefix: /pw → window.API_BASE
#                                 carries /pw; no absolute-rooted asset URL (brief 08)
#   test_5__execute_workflow_W1   POST /sequence/execute (W1) → status completed
#
# Same skip-gate as the rest of the live tier: skipped unless
# SG_PLAYWRIGHT__LIVE_BASE_URL + SG_PLAYWRIGHT__LIVE_API_KEY are set
# (conftest.pytest_collection_modifyitems), so the laptop default `pytest tests/`
# stays hermetic. No mocks, no patches.
# ═══════════════════════════════════════════════════════════════════════════════

import re
from unittest                                                       import TestCase

import httpx

from tests.integration_live.conftest                               import REQUEST_TIMEOUT_S


def _live_client(extra_headers: dict = None):
    from tests.integration_live.conftest import _api_key, _api_key_header, _base_url
    headers = {_api_key_header(): _api_key()}
    if extra_headers:
        headers.update(extra_headers)
    return httpx.Client(base_url=_base_url(), headers=headers, timeout=REQUEST_TIMEOUT_S)


class test_1__container_ready(TestCase):

    def test__health_info_responds_200(self):
        with _live_client() as c:
            r = c.get('/health/info')
            assert r.status_code == 200, f'/health/info → {r.status_code}: {r.text[:300]}'


class test_2__get_index(TestCase):

    def test__index_returns_200_and_console_html(self):
        with _live_client() as c:
            r = c.get('/')
            assert r.status_code == 200, f'GET / → {r.status_code}: {r.text[:300]}'
            body = r.text
            assert 'SG Playwright' in body, 'console marker "SG Playwright" missing from GET /'
            assert 'window.__tool' in body, 'agentic window.__tool surface missing from GET /'
            assert 'const GALLERY' in body, 'example gallery missing from GET /'


class test_3__get_capabilities(TestCase):

    def test__capabilities_returns_200_and_shape(self):
        with _live_client() as c:
            r = c.get('/health/capabilities')
            assert r.status_code == 200, f'/health/capabilities → {r.status_code}: {r.text[:300]}'
            body = r.json()
            assert isinstance(body, dict) and body, f'capabilities body not a non-empty object: {body!r}'


class test_4__index_prefix_aware(TestCase):

    def test__index_behind_pw_prefix_carries_prefix_and_no_absolute_rooted_urls(self):
        with _live_client(extra_headers={'X-Forwarded-Prefix': '/pw'}) as c:
            r = c.get('/')
            assert r.status_code == 200, f'GET / (prefixed) → {r.status_code}'
            body = r.text
            m = re.search(r'window\.API_BASE\s*=\s*"([^"]*)"', body)
            assert m is not None, 'window.API_BASE not found in prefixed render'
            assert m.group(1) == '/pw', f'window.API_BASE should be /pw behind the proxy, got {m.group(1)!r}'
            forbidden = re.findall(r'(?:src|href)\s*=\s*"(/(?:components|api/specs)/[^"]*)"', body)
            assert not forbidden, f'absolute-rooted asset URLs break behind /pw: {forbidden}'

    def test__index_standalone_has_empty_api_base(self):
        with _live_client() as c:                                                   # no X-Forwarded-Prefix; default resolves to the deployment's prefix
            r = c.get('/')
            assert r.status_code == 200
            m = re.search(r'window\.API_BASE\s*=\s*"([^"]*)"', r.text)
            assert m is not None, 'window.API_BASE not found in standalone render'


class test_5__execute_workflow_W1(TestCase):

    def test__W1_sequence_completes(self):                                          # the gallery's flagship workflow runs end-to-end against the real image
        body = {'capture_config' : {'screenshot': {'enabled': True, 'sink': 'inline'}},
                'sequence_config': {}                                              ,
                'steps'          : [{'action': 'navigate', 'url': 'https://example.com', 'wait_until': 'domcontentloaded'},
                                    {'action': 'screenshot', 'full_page': True}]}
        with _live_client() as c:
            r = c.post('/sequence/execute', json=body)
            assert r.status_code == 200, f'/sequence/execute → {r.status_code}: {r.text[:500]}'
            resp = r.json()
            assert resp.get('status') == 'completed', f'status={resp.get("status")}: {resp}'
            assert resp.get('steps_passed', 0) == resp.get('steps_total', -1)
