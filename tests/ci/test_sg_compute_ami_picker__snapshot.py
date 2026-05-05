# ═══════════════════════════════════════════════════════════════════════════════
# Structural test for sg-compute-ami-picker web component
#
# Validates the live-fetch contract introduced when GET /api/amis landed:
#   - apiClient import present (no longer a stub)
#   - setSpecId() performs a real fetch (not the placeholder comment)
#   - _populateAmis() exists and handles empty + non-empty paths
#   - DOM helpers _showLoading / _showError / _hidePlaceholder present
#   - select element starts hidden; ami-empty element present
#   - sg-compute:ami.selected event dispatched on change
# ═══════════════════════════════════════════════════════════════════════════════

from pathlib import Path

COMPONENT_DIR = (
    Path(__file__).parents[2]
    / 'sgraph_ai_service_playwright__api_site'
    / 'components' / 'sp-cli' / '_shared' / 'sg-compute-ami-picker'
    / 'v0' / 'v0.1' / 'v0.1.0'
)


def _read(filename: str) -> str:
    return (COMPONENT_DIR / filename).read_text()


class Test_SgComputeAmiPicker__structure:

    def test_three_file_pattern_exists(self):
        for ext in ('js', 'html', 'css'):
            assert (COMPONENT_DIR / f'sg-compute-ami-picker.{ext}').exists(), \
                f'Missing sg-compute-ami-picker.{ext}'

    def test_custom_element_registered(self):
        js = _read('sg-compute-ami-picker.js')
        assert "customElements.define('sg-compute-ami-picker'" in js

    def test_api_client_imported(self):
        js = _read('sg-compute-ami-picker.js')
        assert "import { apiClient" in js
        assert 'shared/api-client.js' in js

    def test_set_spec_id_calls_api(self):
        js = _read('sg-compute-ami-picker.js')
        # must perform a real fetch, not just store the specId
        assert '/api/amis?spec_id=' in js

    def test_populate_amis_method_exists(self):
        js = _read('sg-compute-ami-picker.js')
        assert '_populateAmis(' in js

    def test_populate_amis_handles_empty(self):
        js = _read('sg-compute-ami-picker.js')
        # empty path shows ami-empty; select stays hidden
        assert 'ami-empty' in js
        assert 'amis.length' in js

    def test_loading_state_helper_exists(self):
        js = _read('sg-compute-ami-picker.js')
        assert '_showLoading(' in js

    def test_error_state_helper_exists(self):
        js = _read('sg-compute-ami-picker.js')
        assert '_showError(' in js

    def test_hide_placeholder_helper_exists(self):
        js = _read('sg-compute-ami-picker.js')
        assert '_hidePlaceholder(' in js

    def test_ami_selected_event_dispatched(self):
        js = _read('sg-compute-ami-picker.js')
        assert 'sg-compute:ami.selected' in js

    def test_get_selected_ami_id_method_exists(self):
        js = _read('sg-compute-ami-picker.js')
        assert 'getSelectedAmiId(' in js

    def test_no_partial_stub_comment(self):
        js = _read('sg-compute-ami-picker.js')
        # old stub comment must be gone
        assert 'GET /api/amis not yet available' not in js

    def test_html_has_ami_placeholder(self):
        html = _read('sg-compute-ami-picker.html')
        assert 'ami-placeholder' in html

    def test_html_ami_select_starts_hidden(self):
        html = _read('sg-compute-ami-picker.html')
        assert 'ami-select' in html
        # select must start hidden (shown only after successful fetch)
        assert 'hidden' in html

    def test_html_has_ami_empty(self):
        html = _read('sg-compute-ami-picker.html')
        assert 'ami-empty' in html

    def test_css_has_ami_select_styles(self):
        css = _read('sg-compute-ami-picker.css')
        assert '.ami-select' in css

    def test_css_has_ami_placeholder_styles(self):
        css = _read('sg-compute-ami-picker.css')
        assert '.ami-placeholder' in css
