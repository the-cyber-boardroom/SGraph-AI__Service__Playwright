# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Routes__Index (GET / capability-driven console)
#
# v0.2.64 dev pack P2-P5 rebuild: the two-tab screenshot toy becomes a
# capability-driven, agent-native console (sg-layout + sg-tokens shell, 8 endpoint-
# family tabs, the 24-verb sequence builder, workflow import/export + gallery, in-app
# docs, and an agentic window.__tool). Assertions are on the RENDERED HTML via
# Routes__Index().index(_FakeRequest()).body.decode() — no route registration or
# Chromium needed, so these run anywhere the package imports.
#
# Phase-1 behaviour (auth-aware bootstrap, escaping, prefix-aware links, Array guards)
# is preserved through the rebuild and re-asserted below against the new text.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                          import TestCase

from sg_compute_specs.playwright.core.consts.env_vars                                  import ENV_VAR__DEPLOYMENT_TARGET, ENV_VAR__ROOT_PATH
from sg_compute_specs.playwright.core.fast_api.Fast_API__Playwright__Service           import Fast_API__Playwright__Service
from sg_compute_specs.playwright.core.fast_api.routes.Routes__Index                    import Routes__Index


_API_KEY_NAME  = 'FAST_API__AUTH__API_KEY__NAME'
_API_KEY_VALUE = 'FAST_API__AUTH__API_KEY__VALUE'


class _EnvScrub:                                                                       # scrub the env vars that steer prefix + auth so serving is deterministic
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


class _FakeRequest:                                                                    # minimal stand-in — only .headers.get is used by Root_Path__Resolver
    def __init__(self, headers: dict = None):
        self.headers = headers or {}


def _render(headers: dict = None) -> str:
    return Routes__Index().index(_FakeRequest(headers)).body.decode()


# ════════════════════════════════════════════════════════════════════════════════
#  Phase-1 behaviour preserved through the rebuild
# ════════════════════════════════════════════════════════════════════════════════
class test_Routes__Index__phase1_preserved(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.html = _render()

    # ── health badge reuses the entered key (auth-aware) → no always-degraded bug ──
    def test__health_check_sends_api_key(self):
        assert 'function authHeaders'         in self.html
        assert "h[authHeaderName()] = k"      in self.html                            # key attached under the selected auth header
        assert "apiGet('/health/status')"     in self.html                            # health check goes through the auth-aware getter
        assert "await fetch(window.API_BASE + '/health/status')" not in self.html     # old keyless call gone

    # ── capability bootstrap: /health/info + /health/capabilities fetched on load ──
    def test__bootstrap_fetches_info_and_capabilities(self):
        assert "apiGet('/health/info')"         in self.html
        assert "apiGet('/health/capabilities')" in self.html
        assert 'function bootstrap'             in self.html
        assert 'let CAPABILITIES'               in self.html

    # ── every user-echoed string is escaped (XSS discipline preserved + extended) ──
    def test__escaping_preserved(self):
        assert 'function escHtml'  in self.html
        assert 'const u=escHtml(url)' in self.html or 'escHtml(url)' in self.html      # url escaped before interpolation
        assert 'title="${url}"'    not in self.html                                   # no raw url in an attribute
        assert '.replace(/"/g'     in self.html                                       # escaper also escapes quotes (attribute-safe)

    # ── batch render survives a non-array screenshots payload ──
    def test__batch_guards_non_array_screenshots(self):
        assert 'Array.isArray(data.screenshots)' in self.html

    # ── /docs link is prefix-aware (composes off window.API_BASE, not absolute /docs) ──
    def test__docs_link_is_prefix_aware(self):
        assert 'id="docs-link"'                       in self.html
        assert "dl.href=window.API_BASE+'/docs'"      in self.html
        assert '<a href="/docs"'                      not in self.html

    def test__docs_link_prefixed_behind_proxy(self):
        html = _render({'x-forwarded-prefix': '/pw'})
        assert 'window.API_BASE="/pw";' in html

    # ── "html" is a render mode, not a screenshot format ──
    def test__format_toggle_relabelled(self):
        assert 'Image (PNG)' in self.html
        assert 'HTML source' in self.html

    # ── window.API_BASE injection preserved ──
    def test__api_base_injection_preserved(self):
        assert 'window.API_BASE="__API_BASE__"' not in self.html                      # template was substituted
        assert 'window.API_BASE="/pw";'         in self.html                          # default prefix


# ════════════════════════════════════════════════════════════════════════════════
#  P2 — capability-driven console on sg-layout + sg-tokens
# ════════════════════════════════════════════════════════════════════════════════
class test_Routes__Index__P2_console(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.html = _render()

    def test__sg_tokens_loaded_cdn_absolute(self):
        assert 'https://dev.tools.sgraph.ai/components/tokens/' in self.html          # sg-tokens CDN-absolute (prefix-independent)
        assert 'sg-tokens.css'                                  in self.html
        # sg-layout is imported from tools.sgraph.ai (the documented host) with a
        # dev-host fallback; if it can't load, the grid fallback keeps the console usable.
        assert 'https://tools.sgraph.ai/core/sg-layout/v0.1.0/sg-layout.js' in self.html

    def test__all_endpoint_family_tabs_present(self):
        for tab in ['screenshot','sequence','inspect','session','browser','debug','service','docs']:
            assert f'data-tab="{tab}"' in self.html, f'missing tab {tab}'
            assert f'id="tab-{tab}"'   in self.html, f'missing pane {tab}'

    def test__no_forbidden_absolute_rooted_same_origin_url(self):
        # same-origin assets/fetches must compose off window.API_BASE; absolute-rooted
        # /components.. or /api/specs.. break behind the /pw proxy (Decision #11).
        assert 'src="/components'  not in self.html
        assert 'href="/components' not in self.html
        assert '"/api/specs/'      not in self.html

    def test__same_origin_fetch_is_api_base_prefixed(self):
        assert "fetch(window.API_BASE + path" in self.html                            # apiGet + request both prefix every same-origin call
        assert "apiGet('/health/status')"     in self.html                            # health goes through the prefixed getter

    def test__auth_mode_toggle_present(self):
        assert "setAuthMode('apiKey')" in self.html
        assert "setAuthMode('proxy')"  in self.html
        assert 'x-sgraph-access-token' in self.html                                   # /pw proxy header
        assert 'X-API-Key'             in self.html                                   # direct header
        assert 'function authHeaderName' in self.html

    def test__capability_gating_present(self):
        assert 'supports_persistent' in self.html                                     # Session gated on persistence
        assert 'supports_video'      in self.html                                     # video verbs gated
        assert 'supported_sinks'     in self.html                                     # sink picker limited
        assert 'function applyCapabilities' in self.html

    def test__sequence_builder_has_real_verbs(self):
        # the 24-verb vocabulary present in the builder verb table
        for verb in ['navigate','click','fill','press','select','hover','scroll',
                     'wait_for','wait','screenshot','evaluate','get_pdf','get_dom_tree',
                     'get_a11y_tree','get_console_tail','get_network_failures','set_viewport']:
            assert verb in self.html, f'verb {verb} missing from builder'


# ════════════════════════════════════════════════════════════════════════════════
#  P3 — workflow import/export + gallery
# ════════════════════════════════════════════════════════════════════════════════
class test_Routes__Index__P3_workflows(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.html = _render()

    def test__workflow_io_present(self):
        for fn in ['function wfExportFile','function wfImportFile','function wfSaveLocal',
                   'function wfLoadLocal','function exportWorkflow','function importWorkflow']:
            assert fn in self.html, f'missing {fn}'

    def test__gallery_w1_to_w9_present_with_real_verbs(self):
        for wid in ['S1','S2','S3','S4','S5','W1','W2','W3','W4','W5','W6','W7','W8','W9']:
            assert f"id:'{wid}'" in self.html, f'gallery missing {wid}'
        # real verb/field names from the capability map, not invented ones
        assert "action:'get_pdf'"           in self.html                              # W4
        assert "action:'get_console_tail'"  in self.html                              # W5
        assert "action:'get_a11y_tree'"     in self.html                              # W3
        assert "action:'evaluate'"          in self.html                              # W7
        assert "action:'set_viewport'"      in self.html                              # W6
        assert 'url_pattern'                in self.html                              # W2 wait_for field

    def test__copy_curl_uses_placeholder_not_token(self):
        assert 'function copyCurl' in self.html
        assert '$SG_PLAYWRIGHT_KEY' in self.html                                      # placeholder
        # the curl builder must NOT inline the stored key value
        assert 'keyEl.value' not in self.html.split('function copyCurl')[1].split('function flash')[0]

    def test__copy_json_present(self):
        assert 'function copyJson' in self.html
        assert 'Copy as curl'      in self.html
        assert 'Copy as JSON'      in self.html


# ════════════════════════════════════════════════════════════════════════════════
#  P4 — docs & help
# ════════════════════════════════════════════════════════════════════════════════
class test_Routes__Index__P4_docs(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.html = _render()

    def test__docs_generated_from_capability_surface(self):
        assert 'function renderDocs'   in self.html
        assert 'VERB_LIST'             in self.html                                   # docs iterate the verb surface
        assert 'live /health/capabilities' in self.html                              # docs include live caps

    def test__evaluate_allowlist_hint(self):
        assert 'allowlist' in self.html                                               # evaluate / wait_for:function hint
        assert 'NOT 422'   in self.html

    def test__skills_deeplink_prefix_aware(self):
        assert "sl.href=window.API_BASE+'/admin/skills/human'" in self.html
        assert "cl.href=window.API_BASE+'/auth/set-cookie-form'" in self.html


# ════════════════════════════════════════════════════════════════════════════════
#  P5 — agentic window.__tool
# ════════════════════════════════════════════════════════════════════════════════
class test_Routes__Index__P5_tool_api(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.html = _render()

    def test__window_tool_registered(self):
        assert 'window.__tool ='          in self.html
        assert 'window.__tool_registry'   in self.html
        assert 'window.SGA_TOOL'          in self.html

    def test__tool_method_surface(self):
        for m in ['async screenshot(','async batch(','async sequence(','async inspect(',
                  'async browser(','session:','async run(','loadExample(',
                  'exportWorkflow(','importWorkflow(','setAuth(','getState(','getRuns(','getActiveTab(']:
            assert m in self.html, f'missing tool method {m}'

    def test__tool_session_subsurface(self):
        for m in ['async open(','async act(','async probe(','async close(']:
            assert m in self.html

    def test__meta_surface(self):
        for m in ['getMethods(','getVersion(','getManifest(','getSkills(','health(','getLog(']:
            assert m in self.html

    def test__getmanifest_is_cached_capabilities(self):
        assert 'getManifest(){ return CAPABILITIES; }' in self.html

    def test__getskills_returns_human_browser_api_trio(self):
        block = self.html.split('async getSkills()')[1].split('async health()')[0]
        assert 'human:'   in block
        assert 'browser:' in block
        assert 'api:'     in block
        assert '_apiSkill()' in block                                                 # api skill generated from capability surface

    def test__token_never_exposed_by_getter_or_log(self):
        # getLog / getRuns / getState must not read the key back
        for fn_marker in ['getLog(){', 'getRuns(n){', 'getState(){']:
            block = self.html.split(fn_marker)[1][:200]
            assert 'keyEl.value' not in block
            assert 'KEY_LS'      not in block


# ════════════════════════════════════════════════════════════════════════════════
#  Body-level serving — TestClient GET / returns 200 + the console HTML (no Chromium)
# ════════════════════════════════════════════════════════════════════════════════
class test_Routes__Index__serving(TestCase):

    def test__get_root_returns_200_and_console_html(self):
        with _EnvScrub(**{ENV_VAR__DEPLOYMENT_TARGET: 'laptop'   ,                      # GET / is subject to the API-key middleware; pass the key
                          _API_KEY_NAME             : 'X-API-Key',
                          _API_KEY_VALUE            : 'unit-test'}):
            fa = Fast_API__Playwright__Service().setup()
            r  = fa.client().get('/', headers={'X-API-Key': 'unit-test'})
        assert r.status_code == 200
        assert 'SG <span>Playwright</span> Console' in r.text
        assert 'window.__tool ='                    in r.text

    def test__get_root_prefix_aware_behind_proxy(self):                               # render-pattern: /pw prefix injected; no absolute-rooted same-origin asset
        html = _render({'x-forwarded-prefix': '/pw'})
        assert 'window.API_BASE="/pw";'  in html
        assert 'src="/components'        not in html
        assert '"/api/specs/'            not in html


# ════════════════════════════════════════════════════════════════════════════════
#  Iteration 2 — light work panes, sg-layout wiring + fallback, screenshot viewer,
#  copyText clipboard fix, S-series examples, bottom __tool console
# ════════════════════════════════════════════════════════════════════════════════
class test_Routes__Index__iteration2(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.html = _render()

    # ── item 1: theme split — light work panes; header + rail keep dark tokens ──
    def test__light_work_panes_present(self):
        assert '.work-light'                in self.html                              # light pane class defined
        assert 'class="builder work-light"' in self.html                             # center builder is a light pane
        assert 'class="result work-light"'  in self.html                             # right result is a light pane
        assert '--lsurface'                 in self.html                             # light palette tokens
        assert '--ltext'                    in self.html

    def test__header_and_rail_keep_dark_tokens(self):
        # the dark chrome variables are still the ones header/.tab-rail use
        assert 'header{background:var(--surface)' in self.html
        assert '.tab-rail{background:var(--surface)' in self.html
        assert 'class="tab-rail"' in self.html                                       # rail is NOT a .work-light pane
        assert 'class="tab-rail work-light"' not in self.html

    def test__light_panes_restyle_inputs(self):                                      # inputs/selects/buttons readable on white
        assert '.work-light input[type=text]' in self.html
        assert '.work-light .gbtn'            in self.html
        assert '.work-light select'           in self.html

    # ── item 2: sg-layout hosted via the blessed tag-instantiation pattern ──
    def test__sg_layout_pane_hosts_defined(self):
        # sg-layout instantiates a tag per tab; we host each pane with an element
        # that relocates our pre-built pane content (parked in #pane-store) into itself.
        assert 'id="pane-store"'                 in self.html
        assert "definePaneHost('sg-pane-builder','builder')"       in self.html
        assert "definePaneHost('sg-pane-result','result-panel')"   in self.html
        assert "definePaneHost('sg-pane-console','console-pane')"  in self.html
        assert "tag:'sg-pane-builder'"           in self.html                          # layout tree uses the host tag, not slot=
        assert 'function defaultConsoleLayout'   in self.html

    def test__sg_layout_uses_documented_api(self):
        assert "customElements.whenDefined('sg-layout')" in self.html                  # wait for registration before setLayout
        assert 'el.setLayout('                   in self.html
        assert "el.events.on('layout:changed'"   in self.html                          # internal event bus, not addEventListener
        assert "'sg-playwright:console:layout:v2'" in self.html                        # persisted layout tree

    def test__sg_layout_graceful_fallback_and_reset(self):
        assert 'function applyConsoleGridFallback' in self.html                        # plain grid if sg-layout is absent/fails
        assert 'getBoundingClientRect().width<=0'  in self.html                        # verify-or-revert mount check
        assert 'function resetConsoleLayout'       in self.html                        # header ⟲ Layout control
        assert "document.getElementById('sess-disabled').style" not in self.html       # null crash stays guarded

    # ── item 3: screenshot viewer with Download + Open in new tab ──
    def test__screenshot_viewer_present(self):
        assert 'function shotViewerEl' in self.html
        assert 'function showShot'     in self.html
        assert '.shot-viewer'          in self.html
        assert 'Download'              in self.html
        assert 'Open in new tab'       in self.html
        assert '.download='            in self.html or 'download=filename' in self.html

    def test__screenshot_viewer_used_by_single_batch_and_steps(self):
        assert "showShot('data:image/png;base64,'+data.screenshot_b64" in self.html  # single
        assert "shotViewerEl('data:image/png;base64,'+s.screenshot_b64" in self.html # batch
        assert 'div.appendChild(shotViewerEl(sh.src' in self.html                    # per-step

    # ── item 4: copyText clipboard fix — all three sites routed through it ──
    def test__copytext_helper_present(self):
        assert 'function copyText'           in self.html
        assert 'document.execCommand'        in self.html                            # insecure-origin fallback
        assert 'window.isSecureContext'      in self.html

    def test__no_bare_navigator_clipboard_writeText(self):
        # the ONLY navigator.clipboard.writeText( call lives inside copyText's secure
        # branch; every call SITE (copyJson/copyCurl/trace-id/console) routes through
        # copyText so insecure origins never hit a bare clipboard call.
        assert self.html.count('navigator.clipboard.writeText(') == 1
        copytext_block = self.html.split('function copyText')[1].split('function _copyFallback')[0]
        assert 'navigator.clipboard.writeText(' in copytext_block                     # the one call is inside copyText

    def test__three_clipboard_sites_use_copytext(self):
        assert self.html.count('copyText(') >= 4                                     # copyJson + copyCurl + trace-id + console viewer/quick
        assert 'copyText(JSON.stringify(body' in self.html                           # copyJson
        assert 'copyText(curl)'               in self.html                           # copyCurl
        assert "onclick=\"copyText('"          in self.html                          # trace-id click-to-copy

    # ── item 5: S-series self-contained examples + D7 fix ──
    def test__s_series_examples_present(self):
        for sid in ['S1','S2','S3','S4','S5']:
            assert f"id:'{sid}'" in self.html, f'missing {sid}'
        assert 'function tpUrl' in self.html
        assert "window.location.origin + window.API_BASE + '/test-pages/'" in self.html
        assert "tpUrl('simple')"  in self.html                                       # S1/S2
        assert "tpUrl('form')"    in self.html                                       # S3
        assert "tpUrl('dynamic')" in self.html                                       # S4
        assert "tpUrl('links')"   in self.html                                       # S5

    def test__D7_w2_uses_valid_full_url_pattern(self):
        assert "url_pattern:'**/dashboard**'" not in self.html                       # the rejected glob is gone
        assert "url_pattern:'https://app.example.com/dashboard'" in self.html        # full http(s) URL

    # ── item 6: bottom __tool console ──
    def test__bottom_tool_console_present(self):
        assert 'id="console-pane"'      in self.html
        assert 'id="console-input"'     in self.html
        assert 'function consoleRun'    in self.html
        assert 'function consoleQuick'  in self.html
        assert '__tool.meta.getMethods()' in self.html                              # quick button
        assert 'getManifest()'          in self.html
        assert 'getSkills()'            in self.html
        assert 'getLog()'               in self.html

    def test__console_output_is_escaped(self):
        block = self.html.split('async function consoleRun')[1].split('document.getElementById(\'console-input\').addEventListener')[0]
        assert 'escHtml(' in block                                                   # all console output escaped
        assert '_consoleImageSrc' in self.html                                       # base64/imageSrc → viewer

    def test__console_runs_in_browser_not_server_allowlist(self):
        assert 'not the server-side evaluate allowlist' in self.html or 'NOT the server-side evaluate allowlist' in self.html
