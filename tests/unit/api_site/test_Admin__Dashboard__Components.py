from pathlib import Path
import pytest

REPO_ROOT  = Path(__file__).parents[3]
API_SITE   = REPO_ROOT / 'sgraph_ai_service_playwright__api_site'
SPEC_SPECS = REPO_ROOT / 'sg_compute_specs'

# ── helpers ───────────────────────────────────────────────────────────────── #

def component(name, version='v0/v0.1/v0.1.0'):
    base = API_SITE / 'components' / 'sg-compute' / name / version
    return [base / f'{name}.js', base / f'{name}.html', base / f'{name}.css']

def shared_widget(name, version='v0/v0.1/v0.1.0'):
    base = API_SITE / 'components' / 'sg-compute' / '_shared' / name / version
    return [base / f'{name}.js', base / f'{name}.html', base / f'{name}.css']

def plugin_card(name, version='v0/v0.1/v0.1.0'):
    base = SPEC_SPECS / name / 'ui' / 'card' / version
    return [base / f'sg-compute-{name}-card.js', base / f'sg-compute-{name}-card.html', base / f'sg-compute-{name}-card.css']

def detail(name, version='v0/v0.1/v0.1.0'):
    base = SPEC_SPECS / name / 'ui' / 'detail' / version
    return [base / f'sg-compute-{name}-detail.js', base / f'sg-compute-{name}-detail.html', base / f'sg-compute-{name}-detail.css']

def assert_trio(files):
    for f in files:
        assert f.exists(), f'Missing: {f.relative_to(REPO_ROOT)}'
        assert f.stat().st_size > 0, f'Empty: {f.relative_to(REPO_ROOT)}'

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
            assert f'sg-compute-{name}-card.js' in content, f'Missing script tag for {name} card'

    def test_index_html_has_all_detail_tags(self):
        content = (API_SITE / 'admin' / 'index.html').read_text()
        for name in ['docker', 'podman', 'elastic', 'vnc', 'prometheus', 'opensearch', 'neko', 'firefox']:
            assert f'sg-compute-{name}-detail.js' in content, f'Missing script tag for {name} detail'

    def test_index_html_has_api_view_tag(self):
        content = (API_SITE / 'admin' / 'index.html').read_text()
        assert 'sg-compute-api-view.js' in content

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
        js = plugin_card(name)[0].read_text()
        assert f'/{name}/stack' in js,     f'{name} card should use /{name}/stack (singular)'
        assert f'/{name}/stacks' not in js, f'{name} card must not use /{name}/stacks (plural)'

    @pytest.mark.parametrize('name', PLUGIN_NAMES)
    def test_card_fires_launch_event(self, name):
        js = plugin_card(name)[0].read_text()
        assert f'sp-cli:plugin:{name}.launch-requested' in js

# ── shared widgets ────────────────────────────────────────────────────────── #

WIDGET_NAMES = ['sg-compute-status-chip', 'sg-compute-stack-header', 'sg-compute-stop-button',
                'sg-compute-ssm-command', 'sg-compute-network-info', 'sg-compute-launch-form',
                'sg-remote-browser']

class Test_Shared_Widgets:
    @pytest.mark.parametrize('name', WIDGET_NAMES)
    def test_widget_trio_exists(self, name):
        assert_trio(shared_widget(name))

    def test_launch_form_has_random_name_generator(self):
        js = shared_widget('sg-compute-launch-form')[0].read_text()
        assert '_randomName' in js
        assert 'WORDS' in js

    def test_stop_button_fires_stop_requested(self):
        js = shared_widget('sg-compute-stop-button')[0].read_text()
        assert 'sp-cli:stack.stop-requested' in js

# ── launcher pane + launch panel ──────────────────────────────────────────── #

class Test_Launch_Components:
    def test_launcher_pane_trio(self):
        assert_trio(component('sg-compute-launcher-pane'))

    def test_launcher_pane_reads_settings_bus(self):
        js = component('sg-compute-launcher-pane')[0].read_text()
        assert 'getAllPluginToggles' in js

    def test_launch_panel_trio(self):
        assert_trio(component('sg-compute-launch-panel'))

    def test_launch_panel_fires_cancelled(self):
        js = component('sg-compute-launch-panel')[0].read_text()
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
        assert_trio(component('sg-compute-compute-view'))

    def test_html_has_template_browser(self):
        html = component('sg-compute-compute-view')[1].read_text()
        assert 'spec-groups' in html or 'browser-col' in html

    def test_html_has_configure_pane(self):
        html = component('sg-compute-compute-view')[1].read_text()
        assert 'configure-col' in html

    def test_html_has_launch_button(self):
        html = component('sg-compute-compute-view')[1].read_text()
        assert 'Launch node' in html

    def test_js_has_grouped_catalog(self):
        js = component('sg-compute-compute-view')[0].read_text()
        assert 'nav_group'     in js
        assert '_renderGroups' in js

    def test_js_has_cost_table(self):
        js = component('sg-compute-compute-view')[0].read_text()
        assert 'COST_TABLE' in js

    def test_js_imports_settings_bus(self):
        js = component('sg-compute-compute-view')[0].read_text()
        assert 'settings-bus.js' in js

    def test_html_has_cost_bar(self):
        html = component('sg-compute-compute-view')[1].read_text()
        assert 'cfg-cost-bar' in html

    def test_html_has_two_column_fields(self):
        html = component('sg-compute-compute-view')[1].read_text()
        assert 'cfg-field-row' in html

    def test_html_has_cfg_desc(self):
        html = component('sg-compute-compute-view')[1].read_text()
        assert 'cfg-desc' in html

    def test_js_catalog_has_descriptions(self):
        js = component('sg-compute-compute-view')[0].read_text()
        assert 'display_name' in js

    def test_js_fires_node_launched(self):
        js = component('sg-compute-compute-view')[0].read_text()
        assert 'sp-cli:node.launched' in js

# ── settings view ─────────────────────────────────────────────────────────── #

class Test_Settings_View:
    def test_trio_exists(self):
        assert_trio(component('sg-compute-settings-view'))

    def test_imports_settings_bus(self):
        js = component('sg-compute-settings-view')[0].read_text()
        assert 'settings-bus.js' in js

# ── diagnostics view ──────────────────────────────────────────────────────── #

class Test_Diagnostics_View:
    def test_trio_exists(self):
        assert_trio(component('sg-compute-diagnostics-view'))

    def test_js_layout_has_events_log_tab(self):
        js = component('sg-compute-diagnostics-view')[0].read_text()
        assert 'Events Log' in js

    def test_js_layout_has_events_log_component(self):
        js = component('sg-compute-diagnostics-view')[0].read_text()
        assert 'sg-compute-events-log' in js

    def test_js_imports_sg_layout(self):
        js = component('sg-compute-diagnostics-view')[0].read_text()
        assert 'sg-layout.js' in js

    def test_js_calls_set_layout(self):
        js = component('sg-compute-diagnostics-view')[0].read_text()
        assert 'setLayout' in js

    def test_html_mounts_sg_layout(self):
        html = component('sg-compute-diagnostics-view')[1].read_text()
        assert 'sg-layout' in html

    def test_left_nav_has_no_diag_item(self):
        html = (API_SITE / 'components/sg-compute/sg-compute-left-nav/v0/v0.1/v0.1.0/sg-compute-left-nav.html').read_text()
        assert 'data-view="diagnostics"' not in html

    def test_top_bar_has_diagnostics_button(self):
        html = (API_SITE / 'components/sg-compute/sg-compute-top-bar/v0/v0.1/v0.1.0/sg-compute-top-bar.html').read_text()
        assert 'Diagnostics' in html

    def test_top_bar_js_dispatches_nav_event(self):
        js = (API_SITE / 'components/sg-compute/sg-compute-top-bar/v0/v0.1/v0.1.0/sg-compute-top-bar.js').read_text()
        assert 'diagnostics' in js and 'sp-cli:nav.selected' in js

    def test_admin_js_events_log_removed_from_right_panels(self):
        content = (API_SITE / 'admin' / 'admin.js').read_text()
        assert "key: 'events_log'" not in content

# ── api view ──────────────────────────────────────────────────────────────── #

class Test_Api_View:
    def test_trio_exists(self):
        assert_trio(component('sg-compute-api-view'))

    def test_html_has_iframe(self):
        html = component('sg-compute-api-view')[1].read_text()
        assert 'iframe' in html

    def test_js_opens_docs(self):
        js = component('sg-compute-api-view')[0].read_text()
        assert '/docs' in js


# ── host control plane widgets ────────────────────────────────────────────── #

SHARED_HOST_WIDGETS = ['sg-compute-host-shell', 'sg-compute-host-api-panel']
DETAIL_HOST_TABS    = ['docker', 'firefox', 'elastic', 'neko', 'vnc']


class Test_Host_Control_Widgets:

    @pytest.mark.parametrize('name', SHARED_HOST_WIDGETS)
    def test_widget_trio_exists(self, name):
        assert_trio(shared_widget(name))

    def test_host_shell_has_quick_commands(self):
        js = shared_widget('sg-compute-host-shell')[0].read_text()
        assert 'QUICK_COMMANDS' in js
        assert 'docker ps'      in js

    def test_host_shell_calls_execute_endpoint(self):
        js = shared_widget('sg-compute-host-shell')[0].read_text()
        assert '/host/shell/execute' in js

    def test_host_shell_shows_unavailable_when_no_url(self):
        html = shared_widget('sg-compute-host-shell')[1].read_text()
        assert 'unavailable' in html.lower()

    def test_host_api_panel_loads_docs(self):
        js = shared_widget('sg-compute-host-api-panel')[0].read_text()
        assert '/docs' in js

    def test_host_api_panel_handles_empty_url(self):
        js = shared_widget('sg-compute-host-api-panel')[0].read_text()
        assert 'unavailable' in js.lower()

    def test_index_html_has_host_shell_tag(self):
        content = (API_SITE / 'admin' / 'index.html').read_text()
        assert 'sg-compute-host-shell.js' in content

    def test_index_html_has_host_api_panel_tag(self):
        content = (API_SITE / 'admin' / 'index.html').read_text()
        assert 'sg-compute-host-api-panel.js' in content


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
        assert 'sg-compute-host-shell' in html

    @pytest.mark.parametrize('name', DETAIL_HOST_TABS)
    def test_detail_embeds_host_api_panel(self, name):
        html = detail(name)[1].read_text()
        assert 'sg-compute-host-api-panel' in html

    @pytest.mark.parametrize('name', DETAIL_HOST_TABS)
    def test_detail_imports_host_shell_js(self, name):
        js = detail(name)[0].read_text()
        assert 'sg-compute-host-shell' in js

    @pytest.mark.parametrize('name', DETAIL_HOST_TABS)
    def test_detail_imports_host_api_panel_js(self, name):
        js = detail(name)[0].read_text()
        assert 'sg-compute-host-api-panel' in js


# ── nodes-view ────────────────────────────────────────────────────────────── #

class Test_Nodes_View:

    def test_trio_exists(self):
        assert_trio(component('sg-compute-nodes-view'))

    def test_has_master_list(self):
        html = component('sg-compute-nodes-view')[1].read_text()
        assert 'node-rows' in html or 'nodes-list' in html

    def test_has_empty_state(self):
        html = component('sg-compute-nodes-view')[1].read_text()
        assert 'No active nodes' in html

    def test_has_terminal_tab(self):
        html = component('sg-compute-nodes-view')[1].read_text()
        assert 'Terminal' in html

    def test_has_host_api_tab(self):
        html = component('sg-compute-nodes-view')[1].read_text()
        assert 'Host API' in html or 'hostapi' in html

    def test_embeds_host_shell(self):
        html = component('sg-compute-nodes-view')[1].read_text()
        assert 'sg-compute-host-shell' in html

    def test_embeds_host_api_panel(self):
        html = component('sg-compute-nodes-view')[1].read_text()
        assert 'sg-compute-host-api-panel' in html

    def test_imports_host_shell(self):
        js = component('sg-compute-nodes-view')[0].read_text()
        assert 'sg-compute-host-shell' in js

    def test_registers_custom_element(self):
        js = component('sg-compute-nodes-view')[0].read_text()
        assert "customElements.define('sg-compute-nodes-view'" in js

    def test_index_html_loads_nodes_view(self):
        content = (API_SITE / 'admin' / 'index.html').read_text()
        assert 'sg-compute-nodes-view.js' in content

    def test_admin_js_has_nodes_view_title(self):
        content = (API_SITE / 'admin' / 'admin.js').read_text()
        assert 'nodes' in content and 'Active Nodes' in content

    def test_ec2_tokens_css_exists(self):
        assert (API_SITE / 'shared' / 'ec2-tokens.css').exists()

    def test_ec2_tokens_has_accent(self):
        css = (API_SITE / 'shared' / 'ec2-tokens.css').read_text()
        assert '#4ECDC4' in css or '4ECDC4' in css

    def test_ec2_tokens_maps_sg_tokens(self):
        css = (API_SITE / 'shared' / 'ec2-tokens.css').read_text()
        assert '--sg-accent' in css
        assert '--sg-bg' in css

    def test_index_html_loads_ec2_tokens(self):
        content = (API_SITE / 'admin' / 'index.html').read_text()
        assert 'ec2-tokens.css' in content


# ── stacks-view ───────────────────────────────────────────────────────────── #

class Test_Stacks_View:

    def test_trio_exists(self):
        assert_trio(component('sg-compute-stacks-view'))

    def test_html_has_coming_soon(self):
        html = component('sg-compute-stacks-view')[1].read_text()
        assert 'coming' in html.lower() or 'soon' in html.lower()

    def test_html_describes_stacks(self):
        html = component('sg-compute-stacks-view')[1].read_text()
        assert 'Stack' in html

    def test_html_has_feature_list(self):
        html = component('sg-compute-stacks-view')[1].read_text()
        assert 'cs-feature' in html

    def test_registers_custom_element(self):
        js = component('sg-compute-stacks-view')[0].read_text()
        assert "customElements.define('sg-compute-stacks-view'" in js

    def test_index_html_loads_stacks_view(self):
        content = (API_SITE / 'admin' / 'index.html').read_text()
        assert 'sg-compute-stacks-view.js' in content

    def test_admin_js_has_stacks_in_view_titles(self):
        content = (API_SITE / 'admin' / 'admin.js').read_text()
        assert 'stacks' in content and 'Stacks' in content

    def test_left_nav_has_stacks_item(self):
        html = (API_SITE / 'components/sg-compute/sg-compute-left-nav/v0/v0.1/v0.1.0/sg-compute-left-nav.html').read_text()
        assert 'stacks' in html


# ── settings view cleanup ─────────────────────────────────────────────────── #

class Test_Settings_View_Cleanup:

    def test_compute_specs_section_removed_from_html(self):
        html = component('sg-compute-settings-view')[1].read_text()
        assert 'Compute Specs' not in html

    def test_plugin_list_div_removed_from_html(self):
        html = component('sg-compute-settings-view')[1].read_text()
        assert 'plugin-list' not in html

    def test_get_all_plugin_toggles_not_imported(self):
        js = component('sg-compute-settings-view')[0].read_text()
        assert 'getAllPluginToggles' not in js

    def test_set_plugin_enabled_not_imported(self):
        js = component('sg-compute-settings-view')[0].read_text()
        assert 'setPluginEnabled' not in js

    def test_ui_panels_section_still_present(self):
        html = component('sg-compute-settings-view')[1].read_text()
        assert 'UI Panels' in html

    def test_defaults_section_still_present(self):
        html = component('sg-compute-settings-view')[1].read_text()
        assert 'Defaults' in html

    def test_layout_reset_still_present(self):
        html = component('sg-compute-settings-view')[1].read_text()
        assert 'Reset layout' in html or 'btn-reset-layout' in html
