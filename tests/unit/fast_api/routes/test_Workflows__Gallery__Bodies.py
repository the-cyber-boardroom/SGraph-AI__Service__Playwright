# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Gallery workflow BODIES deserialise into their target schemas
#
# v0.2.64 dev pack — brief 06 §2 ("body-level test tier that runs WITHOUT a
# browser"). The console (Routes__Index.INDEX_HTML) ships W1-W9 as one-click
# "Load example" buttons whose `request` body IS the exact `/sequence/execute`,
# `/inspect`, or `/screenshot/batch` request body (Decision #3 — workflows are
# portable JSON that matches the request schema).
#
# This is the real regression guard for the gallery: it pulls the W1-W9 bodies
# out of the LIVE INDEX_HTML `const GALLERY = [...]` block (single source of
# truth — no fixture copy that could drift) and asserts each one deserialises
# into its target Schema__* via `.from_json()` WITHOUT raising, and that every
# step deserialises through the real dispatcher `parse_step()`. `from_json`
# raises ValueError on a bad field type (verified), so a green run proves the
# gallery bodies are field-valid against the real schemas.
#
# No browser, no mocks, no patches — runnable anywhere the package imports.
# The W1-W9 → assertion map against REAL Chromium lives in
# tests/integration/test_Workflows__Gallery.py (gated, skipped when absent).
# ═══════════════════════════════════════════════════════════════════════════════

import json
import re
from unittest                                                                               import TestCase

from sg_compute_specs.playwright.core.dispatcher.step_schema_registry                       import parse_step
from sg_compute_specs.playwright.core.fast_api.routes.Routes__Index                         import INDEX_HTML
from sg_compute_specs.playwright.core.schemas.enums.Enum__Step__Action                      import Enum__Step__Action
from sg_compute_specs.playwright.core.schemas.inspect.Schema__Inspect__Request              import Schema__Inspect__Request
from sg_compute_specs.playwright.core.schemas.screenshot.Schema__Screenshot__Batch__Request import Schema__Screenshot__Batch__Request
from sg_compute_specs.playwright.core.schemas.sequence.Schema__Sequence__Request            import Schema__Sequence__Request


from sg_compute_specs.playwright.core.schemas.screenshot.Schema__Screenshot__Request       import Schema__Screenshot__Request

# S1-S6 self-contained fixture examples (Decision #5) lead the gallery; W1-W9 follow.
# S6 is the set_cookie demo (stateless — cookie lives only in that request's context).
GALLERY_IDS_S = ['S1', 'S2', 'S3', 'S4', 'S5', 'S6']
GALLERY_IDS_W = ['W1', 'W2', 'W3', 'W4', 'W5', 'W6', 'W7', 'W8', 'W9']
GALLERY_IDS   = GALLERY_IDS_S + GALLERY_IDS_W

# tpUrl(name) resolves at runtime to window.location.origin + window.API_BASE +
# '/test-pages/<name>'. For the body-level (no-browser) tests we substitute a
# concrete absolute URL so the literals deserialise; the real origin is supplied by
# the browser at click time.
_TP_ORIGIN = 'http://test.local/test-pages/'

# Endpoint → schema each workflow body must deserialise into (brief 06 §3 map).
SCHEMA_FOR_ENDPOINT = {'/sequence/execute' : Schema__Sequence__Request            ,
                       '/inspect'          : Schema__Inspect__Request             ,
                       '/screenshot/batch' : Schema__Screenshot__Batch__Request   ,
                       '/screenshot'       : Schema__Screenshot__Request          }

# ── D7 (FIXED, iteration 2) ──────────────────────────────────────────────────
# Previously W2's `wait_for` step used Playwright's glob URL pattern
# `**/dashboard**`, but Schema__Step__Wait_For.url_pattern is typed
# Safe_Str__Url__Permissive whose regex requires a full `http(s)://...` URL — so
# the W2 body was REJECTED with HTTP 400 by /sequence/execute (clicking
# "Load example → W2 → Execute" never reached the browser). Iteration 2 changes
# W2 to a full-URL pattern (`https://app.example.com/dashboard`), so W2 now
# deserialises cleanly like every other workflow. WORKFLOWS_KNOWN_BAD is now
# empty; the regression guard below asserts W2's url_pattern step parses.
WORKFLOWS_KNOWN_BAD = set()                                                                 # D7 resolved — see above


def _extract_gallery():                                                                     # Parse the live `const GALLERY = [...]` JS-object-literal out of INDEX_HTML
    m = re.search(r'const GALLERY\s*=\s*(\[.*?\]);', INDEX_HTML, re.DOTALL)
    assert m is not None, 'const GALLERY = [...] block not found in INDEX_HTML'
    block = m.group(1)

    # tpUrl('name') / tpUrl("name") → a concrete quoted URL literal so the JS-object
    # literal becomes valid JSON (the real origin is composed in-browser at click time).
    block = re.sub(r"tpUrl\(\s*['\"]([a-z]+)['\"]\s*\)", lambda mm: '"' + _TP_ORIGIN + mm.group(1) + '"', block)

    strings = []                                                                            # 1) stash single- AND double-quoted JS string literals (handles nested quotes, e.g. W8 javascript)
    def _stash(mm):
        raw   = mm.group(0)
        quote = raw[0]
        inner = raw[1:-1].replace('\\' + quote, quote)
        strings.append(inner)
        return '\x00%d\x00' % (len(strings) - 1)
    s = re.sub(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'', _stash, block)

    s = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', s)                      # 2) quote bare object keys
    s = re.sub(r',(\s*[}\]])', r'\1', s)                                                     # 3) strip trailing commas (JS allows, JSON forbids)

    def _unstash(mm):                                                                        # 4) restore stashed strings as JSON-escaped strings
        return json.dumps(strings[int(mm.group(1))])
    s = re.sub(r'\x00(\d+)\x00', _unstash, s)

    return json.loads(s)


class test_Workflows__Gallery__Bodies(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.gallery    = _extract_gallery()
        cls.by_id      = {w['id']: w for w in cls.gallery}

    # ── the gallery itself ──────────────────────────────────────────────────────

    def test__gallery_has_s_series_then_w_series(self):
        assert [w['id'] for w in self.gallery] == GALLERY_IDS                                # S1-S5 lead (headline), W1-W9 follow

    def test__s_series_targets_self_contained_test_pages(self):                              # Decision #5 — S-series URLs are the service's own /test-pages/* fixtures
        for sid in GALLERY_IDS_S:
            w   = self.by_id[sid]
            req = w['request']
            blob = json.dumps(req)
            assert '/test-pages/' in blob, f'{sid} does not target a /test-pages fixture'

    def test__s_series_urls_compose_off_origin_and_api_base(self):                           # the live JS composes tpUrl off window.location.origin + window.API_BASE
        assert "function tpUrl" in INDEX_HTML
        assert "window.location.origin + window.API_BASE + '/test-pages/'" in INDEX_HTML

    def test__every_workflow_has_endpoint_and_request(self):
        for w in self.gallery:
            assert w.get('endpoint'), f'{w["id"]} missing endpoint'
            assert isinstance(w.get('request'), dict), f'{w["id"]} missing request body'
            assert w['endpoint'] in SCHEMA_FOR_ENDPOINT, \
                f'{w["id"]} endpoint {w["endpoint"]!r} has no target schema in the map'

    # ── each body deserialises into its target schema (the regression guard) ────

    def test__every_workflow_body_deserialises_into_its_target_schema(self):
        for w in self.gallery:
            if w['id'] in WORKFLOWS_KNOWN_BAD:                                               # D7 — asserted separately below
                continue
            schema_cls = SCHEMA_FOR_ENDPOINT[w['endpoint']]
            obj        = schema_cls.from_json(w['request'])                                  # raises ValueError on any bad field type / shape
            assert obj is not None, f'{w["id"]} → {schema_cls.__name__} returned None'

    def test__D7__W2_url_pattern_is_now_a_valid_full_url(self):                              # D7 regression guard — W2's wait_for url_pattern parses through the dispatcher
        w = self.by_id['W2']
        Schema__Sequence__Request.from_json(w['request'])                                    # envelope parses
        wait_for_step = next(s for s in w['request']['steps'] if s.get('url_pattern'))
        assert wait_for_step['url_pattern'].startswith('http')                               # full http(s):// URL, not a `**/glob**`
        assert '*' not in wait_for_step['url_pattern']
        idx = w['request']['steps'].index(wait_for_step)
        parsed = parse_step(wait_for_step, idx)                                              # no longer rejected by Safe_Str__Url__Permissive
        assert parsed is not None

    def test__S6_set_cookie_body_round_trips(self):                                          # set_cookie slice — S6 is navigate → shot → set_cookie → navigate (the "reload") → shot
        w   = self.by_id['S6']
        obj = Schema__Sequence__Request.from_json(w['request'])
        assert len(obj.steps) == 5
        assert [s['action'] for s in w['request']['steps']] == ['navigate', 'screenshot', 'set_cookie', 'navigate', 'screenshot']
        sc     = next(s for s in w['request']['steps'] if s['action'] == 'set_cookie')
        parsed = parse_step(sc, 2)                                                           # url-form cookie parses through the real dispatcher
        assert str(parsed.name)  == 'sg_demo'
        assert str(parsed.url).startswith('http')
        assert bool(parsed.http_only) is False                                               # HttpOnly would be invisible to the fixture's document.cookie render

    def test__F6__w_series_carries_egress_badge_and_s_series_does_not(self):                 # F6 — every external-URL example is flagged; self-contained ones are not
        for w in self.gallery:
            if w['id'].startswith('W'):
                assert w.get('egress') is True, f"{w['id']} targets an external site but has no egress:true flag"
            else:
                assert 'egress' not in w, f"{w['id']} is self-contained and must not be badged"

    def test__W1_sequence_body_round_trips(self):                                            # spot-check the most-exercised body explicitly
        w   = self.by_id['W1']
        obj = Schema__Sequence__Request.from_json(w['request'])
        assert len(obj.steps) == len(w['request']['steps'])

    def test__W3_inspect_body_round_trips(self):
        w   = self.by_id['W3']
        obj = Schema__Inspect__Request.from_json(w['request'])
        assert str(obj.navigate.url) == w['request']['navigate']['url']
        assert len(obj.probes)       == len(w['request']['probes'])

    def test__W8_batch_body_round_trips(self):
        w   = self.by_id['W8']
        obj = Schema__Screenshot__Batch__Request.from_json(w['request'])
        assert len(obj.items) == len(w['request']['items'])

    # ── every step in every sequence/inspect body parses via the real dispatcher ─

    def test__every_step_parses_through_the_dispatcher(self):
        for w in self.gallery:
            if w['id'] in WORKFLOWS_KNOWN_BAD:                                               # D7 — W2's url_pattern step fails to parse (asserted above)
                continue
            req = w['request']
            steps = []
            steps += req.get('steps', [])                                                   # sequence / W9 act body
            steps += req.get('settle', [])                                                  # inspect settle steps
            steps += list(req.get('probes', {}).values())                                   # inspect probe steps
            for i, step in enumerate(steps):
                parsed = parse_step(step, i)
                assert parsed is not None, f'{w["id"]} step {i} ({step.get("action")}) failed to parse'

    def test__every_step_action_is_a_known_verb(self):                                       # no W uses a verb outside Enum__Step__Action (guards a typo in the gallery)
        valid = {a.value for a in Enum__Step__Action}
        for w in self.gallery:
            req   = w['request']
            steps = req.get('steps', []) + req.get('settle', []) + list(req.get('probes', {}).values())
            for step in steps:
                if 'action' in step:
                    assert step['action'] in valid, \
                        f'{w["id"]} uses unknown verb {step["action"]!r}'
