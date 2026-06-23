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


GALLERY_IDS = ['W1', 'W2', 'W3', 'W4', 'W5', 'W6', 'W7', 'W8', 'W9']

# Endpoint → schema each workflow body must deserialise into (brief 06 §3 map).
SCHEMA_FOR_ENDPOINT = {'/sequence/execute' : Schema__Sequence__Request            ,
                       '/inspect'          : Schema__Inspect__Request             ,
                       '/screenshot/batch' : Schema__Screenshot__Batch__Request   }

# ── D7 (FLAGGED, not fixed) ──────────────────────────────────────────────────
# W2's `wait_for` step uses Playwright's glob URL pattern `**/dashboard**`
# (correct per brief 02 + Playwright `wait_for_url` semantics), but
# Schema__Step__Wait_For.url_pattern is typed Safe_Str__Url__Permissive
# (Schema__Step__Wait_For.py:20) whose regex requires a full `http(s)://...`
# URL. So the W2 gallery body is REJECTED with HTTP 400 by /sequence/execute
# today — clicking "Load example → W2 → Execute" never reaches the browser.
# This is a real contract discrepancy surfaced by this test (a good failure):
# the gallery seed and the schema field type disagree. It is out of scope for
# the P6/P7 tests-and-docs slice (it needs either a schema field-type change or
# a gallery edit — both runtime/design decisions), so it is asserted here AS A
# CONTRACT (the same way brief 06 §3 asserts W7's allowlist failure) and flagged
# for the human / a future Dev slice. When D7 is resolved, move W2 into the
# clean-deserialise set below and delete this carve-out.
WORKFLOWS_KNOWN_BAD = {'W2'}                                                                # see D7 above


def _extract_gallery():                                                                     # Parse the live `const GALLERY = [...]` JS-object-literal out of INDEX_HTML
    m = re.search(r'const GALLERY\s*=\s*(\[.*?\]);', INDEX_HTML, re.DOTALL)
    assert m is not None, 'const GALLERY = [...] block not found in INDEX_HTML'
    block = m.group(1)

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

    def test__gallery_has_all_nine_workflows(self):
        assert [w['id'] for w in self.gallery] == GALLERY_IDS

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

    def test__D7__W2_url_pattern_glob_is_rejected_by_wait_for_schema(self):                  # contract assertion of the flagged discrepancy (good-failure test)
        w = self.by_id['W2']
        Schema__Sequence__Request.from_json(w['request'])                                    # the envelope parses (steps stored as List[dict], validated lazily)
        wait_for_step = next(s for s in w['request']['steps'] if s.get('url_pattern'))
        idx           = w['request']['steps'].index(wait_for_step)
        with self.assertRaises(Exception):                                                   # the dispatcher rejects it: Safe_Str__Url__Permissive declines the `**/dashboard**` glob → HTTP 400 at /sequence/execute
            parse_step(wait_for_step, idx)

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
