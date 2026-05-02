from pathlib import Path
import pytest

API_SITE = Path(__file__).parents[3] / 'sgraph_ai_service_playwright__api_site'

# ── helpers ───────────────────────────────────────────────────────────────── #

def component(name, version='v0/v0.1/v0.1.0'):
    base = API_SITE / 'components' / 'sp-cli' / name / version
    return [base / f'{name}.js', base / f'{name}.html', base / f'{name}.css']

def shared_widget(name, version='v0/v0.1/v0.1.0'):
    base = API_SITE / 'components' / 'sp-cli' / '_shared' / name / version
    return [base / f'{name}.js', base / f'{name}.html', base / f'{name}.css']

def plugin_card(name, version='v0/v0.1/v0.1.0'):
    base = API_SITE / 'plugins' / name / version
    return [base / f'sp-cli-{name}-card.js', base / f'sp-cli-{name}-card.html', base / f'sp-cli-{name}-card.css']

def detail(name, version='v0/v0.1/v0.1.0'):
    return component(f'sp-cli-{name}-detail', version)

def assert_trio(files):
    for f in files:
        assert f.exists(), f'Missing: {f.relative_to(API_SITE.parent)}'
        assert f.stat().st_size > 0, f'Empty: {f.relative_to(API_SITE.parent)}'

# ── admin entry point ─────────────────────────────────────────────────────── #

class Test_Admin_Entry_Point:
    def test_index_html_exists(self):
        assert (API_SITE / 'admin' / 'index.html').exists()

    def test_admin_js_exists(self):
        assert (API_SITE / 'admin' / 'admin.js').exists()

    def test_admin_js_has_settings_bus_import(self):
        content = (API_SITE / 'admin' / 'admin.js').read_text()
        assert 'settings-bus.js' in content

    def test_admin_js_has_build_root_layout(self):
        content = (API_SITE / 'admin' / 'admin.js').read_text()
        assert '_buildRootLayout' in content

    def test_admin_js_has_stop_requested_handler(self):
        content = (API_SITE / 'admin' / 'admin.js').read_text()
        assert 'sp-cli:stack.stop-requested' in content

    def test_index_html_has_all_plugin_card_tags(self):
        content = (API_SITE / 'admin' / 'index.html').read_text()
        for name in ['docker', 'podman', 'elastic', 'vnc', 'prometheus', 'opensearch', 'neko', 'firefox']:
            assert f'sp-cli-{name}-card.js' in content, f'Missing script tag for {name} card'

    def test_index_html_has_all_detail_tags(self):
        content = (API_SITE / 'admin' / 'index.html').read_text()
        for name in ['docker', 'podman', 'elastic', 'vnc', 'prometheus', 'opensearch', 'neko', 'firefox']:
            assert f'sp-cli-{name}-detail.js' in content, f'Missing script tag for {name} detail'

    def test_index_html_has_api_view_tag(self):
        content = (API_SITE / 'admin' / 'index.html').read_text()
        assert 'sp-cli-api-view.js' in content

# ── shared utilities ──────────────────────────────────────────────────────── #

class Test_Shared_Utilities:
    def test_settings_bus(self):
        f = API_SITE / 'shared' / 'settings-bus.js'
        assert f.exists() and f.stat().st_size > 0

    def test_settings_bus_exports(self):
        content = (API_SITE / 'shared' / 'settings-bus.js').read_text()
        for export in ['startSettingsBus', 'getPluginEnabled', 'getAllPluginToggles',
                       'getUIPanelVisible', 'getAllDefaults', 'setPluginEnabled',
                       'setUIPanelVisible', 'setDefault']:
            assert f'export' in content and export in content, f'Missing export: {export}'

    def test_vault_bus(self):
        assert (API_SITE / 'shared' / 'vault-bus.js').exists()

    def test_api_client(self):
        assert (API_SITE / 'shared' / 'api-client.js').exists()

# ── plugin cards ──────────────────────────────────────────────────────────── #

PLUGIN_NAMES = ['docker', 'podman', 'elastic', 'vnc', 'prometheus', 'opensearch', 'neko', 'firefox']

class Test_Plugin_Cards:
    @pytest.mark.parametrize('name', PLUGIN_NAMES)
    def test_card_trio_exists(self, name):
        assert_trio(plugin_card(name))

    @pytest.mark.parametrize('name', PLUGIN_NAMES)
    def test_card_uses_singular_endpoint(self, name):
        js = (API_SITE / 'plugins' / name / 'v0/v0.1/v0.1.0' / f'sp-cli-{name}-card.js').read_text()
        assert f'/{name}/stack' in js,     f'{name} card should use /{name}/stack (singular)'
        assert f'/{name}/stacks' not in js, f'{name} card must not use /{name}/stacks (plural)'

    @pytest.mark.parametrize('name', PLUGIN_NAMES)
    def test_card_fires_launch_event(self, name):
        js = (API_SITE / 'plugins' / name / 'v0/v0.1/v0.1.0' / f'sp-cli-{name}-card.js').read_text()
        assert f'sp-cli:plugin:{name}.launch-requested' in js

# ── shared widgets ────────────────────────────────────────────────────────── #

WIDGET_NAMES = ['sp-cli-status-chip', 'sp-cli-stack-header', 'sp-cli-stop-button',
                'sp-cli-ssm-command', 'sp-cli-network-info', 'sp-cli-launch-form',
                'sg-remote-browser']

class Test_Shared_Widgets:
    @pytest.mark.parametrize('name', WIDGET_NAMES)
    def test_widget_trio_exists(self, name):
        assert_trio(shared_widget(name))

    def test_launch_form_has_random_name_generator(self):
        js = shared_widget('sp-cli-launch-form')[0].read_text()
        assert '_randomName' in js
        assert 'WORDS' in js

    def test_stop_button_fires_stop_requested(self):
        js = shared_widget('sp-cli-stop-button')[0].read_text()
        assert 'sp-cli:stack.stop-requested' in js

# ── launcher pane + launch panel ──────────────────────────────────────────── #

class Test_Launch_Components:
    def test_launcher_pane_trio(self):
        assert_trio(component('sp-cli-launcher-pane'))

    def test_launcher_pane_reads_settings_bus(self):
        js = component('sp-cli-launcher-pane')[0].read_text()
        assert 'getAllPluginToggles' in js

    def test_launch_panel_trio(self):
        assert_trio(component('sp-cli-launch-panel'))

    def test_launch_panel_fires_cancelled(self):
        js = component('sp-cli-launch-panel')[0].read_text()
        assert 'sp-cli:launch.cancelled' in js

# ── per-plugin detail components ──────────────────────────────────────────── #

class Test_Detail_Components:
    @pytest.mark.parametrize('name', PLUGIN_NAMES)
    def test_detail_trio_exists(self, name):
        assert_trio(detail(name))

    def test_elastic_detail_has_kibana_url(self):
        js = detail('elastic')[0].read_text()
        assert ':5601' in js

    def test_vnc_detail_has_remote_browser(self):
        html = detail('vnc')[1].read_text()
        assert 'sg-remote-browser' in html
        js   = detail('vnc')[0].read_text()
        assert 'sg-remote-browser' in js

    def test_vnc_detail_imports_remote_browser(self):
        js = detail('vnc')[0].read_text()
        assert 'sg-remote-browser.js' in js

    def test_firefox_detail_has_remote_browser(self):
        html = detail('firefox')[1].read_text()
        assert 'sg-remote-browser' in html
        js   = detail('firefox')[0].read_text()
        assert 'sg-remote-browser' in js

    def test_firefox_detail_uses_port_5800(self):
        js = detail('firefox')[0].read_text()
        assert ':5800' in js

# ── compute view ─────────────────────────────────────────────────────────── #

class Test_Compute_View:
    def test_trio_exists(self):
        assert_trio(component('sp-cli-compute-view'))

    def test_html_embeds_launcher_and_stacks(self):
        html = component('sp-cli-compute-view')[1].read_text()
        assert 'sp-cli-launcher-pane' in html
        assert 'sp-cli-stacks-pane'   in html

# ── settings view ─────────────────────────────────────────────────────────── #

class Test_Settings_View:
    def test_trio_exists(self):
        assert_trio(component('sp-cli-settings-view'))

    def test_imports_settings_bus(self):
        js = component('sp-cli-settings-view')[0].read_text()
        assert 'settings-bus.js' in js

# ── api view ──────────────────────────────────────────────────────────────── #

class Test_Api_View:
    def test_trio_exists(self):
        assert_trio(component('sp-cli-api-view'))

    def test_html_has_iframe(self):
        html = component('sp-cli-api-view')[1].read_text()
        assert 'iframe' in html

    def test_js_opens_docs(self):
        js = component('sp-cli-api-view')[0].read_text()
        assert '/docs' in js


# ── host control plane widgets ────────────────────────────────────────────── #

SHARED_HOST_WIDGETS = ['sp-cli-host-shell', 'sp-cli-host-api-panel']
DETAIL_HOST_TABS    = ['docker', 'firefox', 'elastic', 'neko', 'vnc']


class Test_Host_Control_Widgets:

    @pytest.mark.parametrize('name', SHARED_HOST_WIDGETS)
    def test_widget_trio_exists(self, name):
        assert_trio(shared_widget(name))

    def test_host_shell_has_quick_commands(self):
        js = shared_widget('sp-cli-host-shell')[0].read_text()
        assert 'QUICK_COMMANDS' in js
        assert 'docker ps'      in js

    def test_host_shell_calls_execute_endpoint(self):
        js = shared_widget('sp-cli-host-shell')[0].read_text()
        assert '/host/shell/execute' in js

    def test_host_shell_shows_unavailable_when_no_url(self):
        html = shared_widget('sp-cli-host-shell')[1].read_text()
        assert 'unavailable' in html.lower()

    def test_host_api_panel_loads_docs(self):
        js = shared_widget('sp-cli-host-api-panel')[0].read_text()
        assert '/docs' in js

    def test_host_api_panel_handles_empty_url(self):
        js = shared_widget('sp-cli-host-api-panel')[0].read_text()
        assert 'unavailable' in js.lower()

    def test_index_html_has_host_shell_tag(self):
        content = (API_SITE / 'admin' / 'index.html').read_text()
        assert 'sp-cli-host-shell.js' in content

    def test_index_html_has_host_api_panel_tag(self):
        content = (API_SITE / 'admin' / 'index.html').read_text()
        assert 'sp-cli-host-api-panel.js' in content


class Test_Detail_Host_Tabs:

    @pytest.mark.parametrize('name', DETAIL_HOST_TABS)
    def test_detail_has_terminal_tab_button(self, name):
        html = detail(name)[1].read_text()
        assert 'Terminal' in html or 'shell' in html.lower()

    @pytest.mark.parametrize('name', DETAIL_HOST_TABS)
    def test_detail_has_host_api_tab_button(self, name):
        html = detail(name)[1].read_text()
        assert 'Host API' in html or 'hostapi' in html.lower()

    @pytest.mark.parametrize('name', DETAIL_HOST_TABS)
    def test_detail_embeds_host_shell_widget(self, name):
        html = detail(name)[1].read_text()
        assert 'sp-cli-host-shell' in html

    @pytest.mark.parametrize('name', DETAIL_HOST_TABS)
    def test_detail_embeds_host_api_panel(self, name):
        html = detail(name)[1].read_text()
        assert 'sp-cli-host-api-panel' in html

    @pytest.mark.parametrize('name', DETAIL_HOST_TABS)
    def test_detail_imports_host_shell_js(self, name):
        js = detail(name)[0].read_text()
        assert 'sp-cli-host-shell' in js

    @pytest.mark.parametrize('name', DETAIL_HOST_TABS)
    def test_detail_imports_host_api_panel_js(self, name):
        js = detail(name)[0].read_text()
        assert 'sp-cli-host-api-panel' in js
