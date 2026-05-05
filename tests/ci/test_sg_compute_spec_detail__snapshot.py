# ═══════════════════════════════════════════════════════════════════════════════
# Structural test for sg-compute-spec-detail web component (T2-FE-patch Task 5)
#
# Visual snapshot testing (against a live browser + running dashboard server)
# is PARTIAL — no ESM web-component test runner exists in this project.
# Future: live visual tests will run against a Playwright Node spun from spec
# (e.g. sg-compute spec firefox create → node serves dashboard → Playwright
# navigates and captures screenshot). For now this test validates file-level
# contracts: expected DOM structure, JS API surface, and CSS selectors.
# ═══════════════════════════════════════════════════════════════════════════════

from pathlib import Path

COMPONENT_DIR = (
    Path(__file__).parents[2]
    / 'sgraph_ai_service_playwright__api_site'
    / 'components' / 'sg-compute' / 'sg-compute-spec-detail'
    / 'v0' / 'v0.1' / 'v0.1.0'
)


def _read(filename: str) -> str:
    return (COMPONENT_DIR / filename).read_text()


class Test_SgComputeSpecDetail__structure:

    def test_three_file_pattern_exists(self):
        for ext in ('js', 'html', 'css'):
            assert (COMPONENT_DIR / f'sg-compute-spec-detail.{ext}').exists(), \
                f'Missing sg-compute-spec-detail.{ext}'

    def test_custom_element_registered(self):
        js = _read('sg-compute-spec-detail.js')
        assert "customElements.define('sg-compute-spec-detail'" in js

    def test_open_method_exists(self):
        js = _read('sg-compute-spec-detail.js')
        assert 'open(spec)' in js

    def test_render_method_exists(self):
        js = _read('sg-compute-spec-detail.js')
        assert '_render(spec)' in js

    def test_launch_dispatches_catalog_launch(self):
        js = _read('sg-compute-spec-detail.js')
        assert 'sp-cli:catalog-launch' in js

    def test_readme_placeholder_always_shown(self):
        js = _read('sg-compute-spec-detail.js')
        # readme link must always be hidden; placeholder always shown
        assert 'this._readmeLink.hidden        = true' in js
        assert 'this._readmePlaceholder.hidden = false' in js
        # the broken live link must NOT be enabled
        assert 'this._readmeLink.hidden      = false' not in js

    def test_no_inline_styles_in_render(self):
        js = _read('sg-compute-spec-detail.js')
        # inline style= attributes in template literals were removed in T2-FE-patch
        assert 'style="font-family:monospace' not in js
        assert 'style="color:var(--sg-text-muted)' not in js

    def test_stability_unknown_fallback(self):
        js = _read('sg-compute-spec-detail.js')
        assert "spec.stability || 'unknown'" in js
        assert "spec.stability || 'experimental'" not in js

    def test_css_has_sd_field_empty_class(self):
        css = _read('sg-compute-spec-detail.css')
        assert '.sd-field-empty' in css

    def test_css_has_sd_extends_id_class(self):
        css = _read('sg-compute-spec-detail.css')
        assert '.sd-extends-id' in css

    def test_css_has_unknown_stability_badge(self):
        css = _read('sg-compute-spec-detail.css')
        assert '.sd-stability-badge.unknown' in css

    def test_html_has_readme_placeholder_element(self):
        html = _read('sg-compute-spec-detail.html')
        assert 'sd-readme-placeholder' in html
        assert 'sd-readme-link' in html

    def test_html_has_launch_buttons(self):
        html = _read('sg-compute-spec-detail.html')
        assert 'btn-launch-header' in html
        assert 'btn-launch-footer' in html
