# ═══════════════════════════════════════════════════════════════════════════════
# Live — Φ3 DOM-read verbs (FR-2) + a11y (FR-5b) + PDF (FR-5d) +
# wait_for: function (FR-1c).
#
# Ship gate for Φ3: @Content's vault case is solvable end-to-end with
# `wait_for: text` → `get_dom_tree` → real selector, with no blind waits.
# This tier proves the new verbs round-trip through the FastAPI surface.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from tests.integration_live.conftest import TARGET__SGRAPH


def _client():
    from tests.integration_live.conftest import _api_key, _api_key_header, _base_url, REQUEST_TIMEOUT_S
    import httpx
    return httpx.Client(base_url=_base_url(),
                        headers={_api_key_header(): _api_key()},
                        timeout=REQUEST_TIMEOUT_S)


def _base_body(steps):
    return {'capture_config' : {}                ,
            'sequence_config': {}                ,
            'steps'          : steps             }


# ─── FR-2 ────────────────────────────────────────────────────────────────────────
class test_get_text(TestCase):

    def test__get_text_returns_visible_text_of_body(self):
        body = _base_body([
            {'action': 'navigate', 'url': TARGET__SGRAPH},
            {'action': 'get_text'                       },
        ])
        with _client() as c:
            r = c.post('/sequence/execute', json=body)
            assert r.status_code == 200, r.text
            results = r.json()['step_results']
            text = results[1].get('text') or ''
            assert len(text) > 50, f'expected meaningful text, got {text!r}'


class test_get_html(TestCase):

    def test__get_html_no_selector_returns_full_document_html(self):
        body = _base_body([
            {'action': 'navigate', 'url': TARGET__SGRAPH},
            {'action': 'get_html'                       },
        ])
        with _client() as c:
            r = c.post('/sequence/execute', json=body)
            assert r.status_code == 200, r.text
            results = r.json()['step_results']
            html = results[1].get('html') or ''
            assert '<html' in html.lower() and '</html>' in html.lower()

    def test__get_html_with_selector_returns_outerhtml_only(self):
        body = _base_body([
            {'action': 'navigate', 'url': TARGET__SGRAPH                  },
            {'action': 'get_html', 'selector': 'body'                     },
        ])
        with _client() as c:
            r = c.post('/sequence/execute', json=body)
            assert r.status_code == 200, r.text
            results = r.json()['step_results']
            html = results[1].get('html') or ''
            assert html.lower().lstrip().startswith('<body'), f'expected body outerHTML, got {html[:200]!r}'


class test_get_dom_tree(TestCase):                                                       # FR-2 headline — the "what should I be targeting" verb

    def test__returns_compact_tree_with_expected_node_shape(self):
        body = _base_body([
            {'action'       : 'navigate'                                                       , 'url': TARGET__SGRAPH},
            {'action'       : 'get_dom_tree'                                                                          ,
             'max_depth'    : 3                                                                                       },
        ])
        with _client() as c:
            r = c.post('/sequence/execute', json=body)
            assert r.status_code == 200, r.text
            results = r.json()['step_results']
            tree = results[1].get('dom_tree')
            assert isinstance(tree, dict), f'dom_tree missing or wrong type: {type(tree)}'
            for key in ('tag', 'rect', 'visible', 'child_count', 'children'):
                assert key in tree, f'dom_tree missing expected key {key!r} — got keys {sorted(tree.keys())}'
            assert tree['tag'] == 'body'                                                       # Default root
            assert isinstance(tree['children'], list)

    def test__max_depth_bounds_recursion(self):                                          # max_depth=1 should yield body + direct children only (no grandkids)
        body = _base_body([
            {'action': 'navigate'    , 'url': TARGET__SGRAPH         },
            {'action': 'get_dom_tree', 'max_depth': 1                },
        ])
        with _client() as c:
            r = c.post('/sequence/execute', json=body)
            assert r.status_code == 200, r.text
            tree = r.json()['step_results'][1]['dom_tree']
            for child in tree.get('children', []):
                assert child.get('children', []) == [], f'depth-2 node should have empty children at max_depth=1'


# ─── FR-5b — accessibility tree ─────────────────────────────────────────────────
class test_get_a11y_tree(TestCase):

    def test__returns_a11y_snapshot(self):
        body = _base_body([
            {'action': 'navigate'     , 'url': TARGET__SGRAPH},
            {'action': 'get_a11y_tree'                       },
        ])
        with _client() as c:
            r = c.post('/sequence/execute', json=body)
            assert r.status_code == 200, r.text
            results = r.json()['step_results']
            tree = results[1].get('accessibility_tree')
            assert isinstance(tree, dict), f'accessibility_tree missing or wrong type: {type(tree)}'
            assert 'role' in tree or 'name' in tree or 'children' in tree                # Playwright a11y snapshot shape


# ─── FR-5d — PDF rendering ──────────────────────────────────────────────────────
class test_get_pdf(TestCase):

    def test__pdf_artefact_carries_size_bytes_and_inline_payload(self):
        body = _base_body([
            {'action': 'navigate', 'url': TARGET__SGRAPH},
            {'action': 'get_pdf'                        },
        ])
        body['capture_config'] = {'pdf': {'enabled': True, 'sink': 'inline'}}
        with _client() as c:
            r = c.post('/sequence/execute', json=body)
            assert r.status_code == 200, r.text
            results = r.json()['step_results']
            artefacts = results[1].get('artefacts') or []
            assert artefacts, f'expected PDF artefact, got step_result: {results[1]}'
            ref = artefacts[0]
            assert ref['artefact_type'] == 'pdf'
            assert int(ref['size_bytes']) > 100
            assert ref.get('inline_b64')                                                 # PDF bytes embedded base64


# ─── FR-1c — wait_for: function ─────────────────────────────────────────────────
class test_wait_for_function__allowlist_gated(TestCase):                                 # Default service starts with an empty allowlist; wait_for.function must be rejected with 422

    def test__unallowed_function_is_rejected_422(self):
        body = _base_body([
            {'action': 'navigate', 'url': TARGET__SGRAPH                                 },
            {'action': 'wait_for', 'function': '() => true', 'timeout_ms': 1000          },
        ])
        with _client() as c:
            r = c.post('/sequence/execute', json=body)
            assert r.status_code == 422, f'expected 422 (allowlist denial), got {r.status_code}: {r.text[:300]}'
            err = r.json().get('detail') or r.text
            assert 'allowlist' in err.lower() or 'allowed' in err.lower(), f'unexpected error body: {err!r}'
