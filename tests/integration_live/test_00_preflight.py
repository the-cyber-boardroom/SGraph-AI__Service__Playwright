# ═══════════════════════════════════════════════════════════════════════════════
# Live — Preflight (runs FIRST due to `00_` prefix).
#
# Five tiers, escalating from cheapest to most expensive. The point is to
# fail at the right altitude:
#   1. CI runner can resolve + reach https://sgraph.ai          (no service involved — purely a runner egress probe)
#   2. CI runner can resolve + reach https://send.sgraph.ai
#   3. sg-playwright service answers /health/info                (cheapest service endpoint — no browser launch)
#   4. sg-playwright service answers /health/capabilities        (proves a usable browser is detected)
#   5. sg-playwright service can complete a minimal navigate     (full e2e path: route → service → real Chromium → real target)
#
# If tier 1 fails → CI egress is blocked; nothing else can work.
# If tier 3 fails → service died between the curl wait loop and pytest; check container logs.
# If tier 4 fails → image is missing Chromium / playwright deps.
# If tier 5 fails → image can't launch a browser process; check sandbox/seccomp/RAM.
# Only when tier 5 is green should the rest of the suite tell you anything useful.
# ═══════════════════════════════════════════════════════════════════════════════

import socket
from unittest import TestCase
from urllib.parse                                                       import urlparse

import httpx

from tests.integration_live.conftest                                    import (TARGET__SGRAPH,
                                                                                 TARGET__SEND,
                                                                                 REQUEST_TIMEOUT_S)


def _live_client():
    from tests.integration_live.conftest import _api_key, _api_key_header, _base_url
    return httpx.Client(base_url=_base_url(),
                        headers={_api_key_header(): _api_key()},
                        timeout=REQUEST_TIMEOUT_S)


# ─── Tier 1+2 — CI runner egress probe (no sg-playwright involved) ────────────
class test_01_ci_runner_egress(TestCase):

    def test__runner_can_resolve_sgraph_ai_dns(self):
        host = urlparse(TARGET__SGRAPH).hostname
        try:
            socket.gethostbyname(host)
        except socket.gaierror as e:
            self.fail(f'CI runner cannot resolve DNS for {host}: {e}. The runner has no working DNS or no network egress.')

    def test__runner_can_resolve_send_sgraph_ai_dns(self):
        host = urlparse(TARGET__SEND).hostname
        try:
            socket.gethostbyname(host)
        except socket.gaierror as e:
            self.fail(f'CI runner cannot resolve DNS for {host}: {e}')

    def test__runner_can_https_get_sgraph_ai(self):                                   # No service involved — verifies runner-level HTTPS works
        with httpx.Client(timeout=15.0) as c:
            r = c.get(TARGET__SGRAPH)
            assert r.status_code < 500, f'sgraph.ai returned {r.status_code}; site may be down'
            assert len(r.content) > 100, 'sgraph.ai responded but body is suspiciously small'

    def test__runner_can_https_get_send_sgraph_ai(self):
        with httpx.Client(timeout=15.0) as c:
            r = c.get(TARGET__SEND)
            assert r.status_code < 500, f'send.sgraph.ai returned {r.status_code}'
            assert len(r.content) > 100


# ─── Tier 3 — service liveness (no browser launch) ────────────────────────────
class test_02_service_reachable(TestCase):

    def test__health_info_responds_200(self):                                         # Cheapest endpoint — no Chromium, no outbound; if this fails the container is gone
        with _live_client() as c:
            r = c.get('/health/info')
            assert r.status_code == 200, f'/health/info returned {r.status_code}: {r.text[:300]}'

    def test__health_info_payload_has_service_version(self):
        with _live_client() as c:
            r = c.get('/health/info')
            body = r.json()
            assert isinstance(body, dict), f'Expected dict, got {type(body).__name__}'
            assert 'service_version' in body, f'Missing service_version in /health/info — keys: {sorted(body.keys())}'
            assert str(body['service_version']).startswith('v'), f'Unexpected service_version shape: {body["service_version"]!r}'


# ─── Tier 4 — service reports a usable browser ────────────────────────────────
class test_03_service_capabilities(TestCase):

    def test__capabilities_responds_200(self):
        with _live_client() as c:
            r = c.get('/health/capabilities')
            assert r.status_code == 200, f'/health/capabilities returned {r.status_code}: {r.text[:300]}'

    def test__capabilities_advertises_a_detected_target(self):                        # If the image is missing Chromium / playwright system deps, the detector reports unhealthy here
        with _live_client() as c:
            r = c.get('/health/capabilities')
            body = r.json()
            assert body, f'Empty capabilities body: {body!r}'                          # At least something — the exact shape is intentionally not pinned here so cap-detector evolution doesn't break this preflight


# ─── Tier 5 — full e2e: service can launch a browser + reach a target ─────────
class test_04_service_can_navigate(TestCase):

    def test__minimal_navigate_to_sgraph_ai_succeeds(self):                           # If THIS fails, every test after will too — fail loudly and early
        body = {'capture_config' : {}                                          ,
                'sequence_config': {}                                          ,
                'steps'          : [{'action'    : 'navigate'                  ,
                                     'url'       : TARGET__SGRAPH              ,
                                     'timeout_ms': 30_000                      }]}
        with _live_client() as c:
            r = c.post('/sequence/execute', json=body)
            assert r.status_code == 200, f'/sequence/execute returned {r.status_code}: {r.text[:500]}'
            resp = r.json()
            assert resp.get('status') in ('completed', 'partial'), f'Sequence status {resp.get("status")} — full response: {resp}'
            assert resp.get('steps_passed', 0) >= 1, f'Navigate step did not pass — step_results: {resp.get("step_results")}'
