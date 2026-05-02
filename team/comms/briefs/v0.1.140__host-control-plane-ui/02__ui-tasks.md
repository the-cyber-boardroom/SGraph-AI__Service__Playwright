# Host Control Plane UI — Tasks

**version** v0.1.140  
**date** 02 May 2026

Read `01__what-backend-shipped.md` first for endpoint specs, auth contract, and local dev setup.

---

## Codebase conventions (non-negotiable)

| Rule | How it looks |
|------|-------------|
| 3-file pattern | `{name}.js` + `{name}.html` + `{name}.css` under `components/sp-cli/_shared/{name}/v0/v0.1/v0.1.0/` |
| Base class | `SgComponent` from `https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js` |
| Shadow DOM | `this.$('.foo')` for all shadow queries — never `document.querySelector` inside a component |
| Pending stack | If `onReady()` hasn't fired yet, store in `this._pendingStack` and apply on ready |
| API calls | Raw `fetch()` to `host_api_url` with `X-API-Key` header — do NOT use `apiClient` (wrong base URL + wrong key) |
| No bundler | All imports are ES module `import` statements; CDN libs via dynamic `import()` |
| No framework | Tab switching is plain JS + CSS data attributes |

Existing reference to read before coding:
- `components/sp-cli/_shared/sp-cli-stack-header/` — minimal 3-file widget
- `components/sp-cli/sp-cli-api-view/` — iframe pattern (5 lines of JS)
- `components/sp-cli/sp-cli-docker-detail/` — `open(stack)` + `setStack` + pending pattern

---

## Task 0 — Surface `host_api_url` on the stack object (prerequisite)

**Files to change:**
```
sgraph_ai_service_playwright__cli/catalog/schemas/Schema__Stack__Summary.py
sgraph_ai_service_playwright__cli/catalog/service/Stack__Catalog__Service.py
```

Add to `Schema__Stack__Summary`:
```python
host_api_url            : Safe_Str__Text
host_api_key_vault_path : Safe_Str__Text
```

In `Stack__Catalog__Service.list_all_stacks()`, derive from the plugin info object (all plugin info schemas already have `public_ip` and `stack_name`):
```python
host_api_url            = f'http://{info.public_ip}:9000' if str(info.public_ip) else '',
host_api_key_vault_path = f'/ec2/{info.stack_name}/host-api-key',
```

Add the corresponding test assertions to `tests/unit/sgraph_ai_service_playwright__cli/catalog/`.

**If you skip Task 0,** derive both values client-side in `sp-cli-host-shell.js` and `sp-cli-host-api-panel.js`:
```javascript
const hostUrl  = stack.host_api_url || (stack.public_ip ? `http://${stack.public_ip}:9000` : '')
const vaultPath = stack.host_api_key_vault_path || `/ec2/${stack.stack_name}/host-api-key`
```

---

## Task 1 — `sp-cli-host-shell` widget

**Path:**
```
sgraph_ai_service_playwright__api_site/components/sp-cli/_shared/sp-cli-host-shell/v0/v0.1/v0.1.0/
    sp-cli-host-shell.js
    sp-cli-host-shell.html
    sp-cli-host-shell.css
```

**HTML (`sp-cli-host-shell.html`):**
```html
<div class="shell-unavailable hidden">
  <p>Host API not yet available for this stack.</p>
</div>
<div class="shell-panel">
  <div class="shell-toolbar">
    <select class="cmd-select"></select>
    <button class="btn-run">Run</button>
    <button class="btn-clear">Clear</button>
    <span class="shell-status"></span>
  </div>
  <div class="shell-output"></div>
</div>
```

**JS (`sp-cli-host-shell.js`):**

```javascript
import { SgComponent }  from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import { currentVault } from '../../../../../shared/vault-bus.js'

const QUICK_COMMANDS = [
    { label: 'List containers',    cmd: 'docker ps'          },
    { label: 'Disk usage',         cmd: 'df -h'              },
    { label: 'Memory',             cmd: 'free -m'            },
    { label: 'Uptime',             cmd: 'uptime'             },
    { label: 'Kernel version',     cmd: 'uname -r'           },
]

class SpCliHostShell extends SgComponent {
    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-host-shell' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._unavailable = this.$('.shell-unavailable')
        this._panel       = this.$('.shell-panel')
        this._select      = this.$('.cmd-select')
        this._output      = this.$('.shell-output')
        this._status      = this.$('.shell-status')
        this.$('.btn-run')  ?.addEventListener('click', () => this._run())
        this.$('.btn-clear')?.addEventListener('click', () => { this._output.innerHTML = '' })
        QUICK_COMMANDS.forEach(({ label, cmd }) => {
            const opt = document.createElement('option')
            opt.value = cmd; opt.textContent = label
            this._select.appendChild(opt)
        })
        if (this._pendingStack) { this.open(this._pendingStack); this._pendingStack = null }
    }

    open(stack) {
        if (!this._unavailable) { this._pendingStack = stack; return }
        this._hostUrl = stack.host_api_url
                     || (stack.public_ip ? `http://${stack.public_ip}:9000` : '')
        const vaultPath = stack.host_api_key_vault_path
                       || `/ec2/${stack.stack_name}/host-api-key`
        this._hostApiKey = ''
        if (this._hostUrl) {
            const vault = currentVault()
            if (vault && vaultPath) vault.read(vaultPath).then(k => { this._hostApiKey = k || '' })
            this._unavailable.classList.add('hidden')
            this._panel.classList.remove('hidden')
        } else {
            this._unavailable.classList.remove('hidden')
            this._panel.classList.add('hidden')
        }
    }

    async _run() {
        const cmd = this._select?.value
        if (!cmd || !this._hostUrl) return
        this._status.textContent = 'running…'
        try {
            const resp = await fetch(`${this._hostUrl}/host/shell/execute`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json', 'X-API-Key': this._hostApiKey },
                body:    JSON.stringify({ command: cmd, timeout: 30 }),
            })
            const data = await resp.json()
            const text = (data.stdout || '') + (data.stderr || '')
            this._appendOutput(cmd, text, resp.ok)
            this._status.textContent = resp.ok ? `exit ${data.exit_code}` : `HTTP ${resp.status}`
        } catch (err) {
            this._appendOutput(cmd, `Network error: ${err.message}`, false)
            this._status.textContent = 'error'
        }
    }

    _appendOutput(cmd, text, ok) {
        const block = document.createElement('div')
        block.className = `output-block ${ok ? '' : 'output-error'}`
        block.innerHTML = `<span class="output-prompt">$ ${cmd}</span><pre class="output-text">${_esc(text)}</pre>`
        this._output.appendChild(block)
        this._output.scrollTop = this._output.scrollHeight
    }
}

function _esc(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') }

customElements.define('sp-cli-host-shell', SpCliHostShell)
```

**CSS (`sp-cli-host-shell.css`):**

Dark terminal aesthetic. Key rules:
```css
:host { display: block; height: 100%; }
.shell-output {
    background: #1a1a1a; color: #d4d4d4;
    font-family: monospace; font-size: 13px;
    padding: 8px; overflow-y: auto; max-height: 400px;
    border-radius: 4px; margin-top: 8px;
}
.output-prompt { color: #6a9955; display: block; margin-top: 8px; }
.output-text   { margin: 0; white-space: pre-wrap; word-break: break-all; }
.output-error  { color: #f44747; }
.shell-toolbar { display: flex; gap: 8px; align-items: center; }
.cmd-select    { flex: 1; }
.hidden        { display: none !important; }
```

**Acceptance:**
- [ ] Widget renders correctly when `host_api_url` is set
- [ ] "Unavailable" message shown when `host_api_url` is empty
- [ ] Selecting a command and clicking Run fires `POST /host/shell/execute`
- [ ] `stdout + stderr` appended to output with the command as a prompt line
- [ ] Clear empties the output area
- [ ] Exit code displayed in status area

---

## Task 2 — `sp-cli-host-terminal` widget (Phase 2 — skip if time-constrained)

Interactive WebSocket terminal using xterm.js. Build after Task 1 is working and Tasks 3–5 are done.

```
sgraph_ai_service_playwright__api_site/components/sp-cli/_shared/sp-cli-host-terminal/v0/v0.1/v0.1.0/
    sp-cli-host-terminal.js
    sp-cli-host-terminal.html
    sp-cli-host-terminal.css
```

**Key notes:**
- Load xterm.js from CDN via dynamic import: `import('https://cdn.jsdelivr.net/npm/@xterm/xterm@5/+esm')`
- Browsers cannot send custom headers on WebSocket — pass the API key as a query param: `ws://{host}/host/shell/stream?api_key={key}`
- The backend WS endpoint currently only validates `X-API-Key` header. **Flag this to the backend session** — it needs to accept `?api_key=` as a fallback for WS. Do not implement Task 2 until that backend change lands.
- `close()` must cancel the WebSocket and kill the xterm instance to prevent memory leaks
- The detail component calls `this._terminal?.close?.()` when the tab becomes inactive

---

## Task 3 — Add Terminal + Host API tabs to detail components

Add tabs to five plugin detail components: **docker, firefox, elastic, neko, vnc**.

**Pattern for each detail HTML** — wrap existing content in an `info` panel and add two new panels:

```html
<div class="detail-tabs">
  <button class="tab-btn active" data-tab="info">Info</button>
  <button class="tab-btn"        data-tab="shell">Terminal</button>
  <button class="tab-btn"        data-tab="hostapi">Host API</button>
</div>
<div class="tab-panel active" data-panel="info">
  <!-- existing detail-top + detail-body content here, unchanged -->
</div>
<div class="tab-panel" data-panel="shell">
  <sp-cli-host-shell class="host-shell"></sp-cli-host-shell>
</div>
<div class="tab-panel" data-panel="hostapi">
  <sp-cli-host-api-panel class="host-api-panel"></sp-cli-host-api-panel>
</div>
```

**Pattern for each detail JS** — add to imports, `onReady`, `open`, and add a tab helper:

```javascript
// imports (add alongside existing _shared imports)
import '../../../../_shared/sp-cli-host-shell/v0/v0.1/v0.1.0/sp-cli-host-shell.js'
import '../../../../_shared/sp-cli-host-api-panel/v0/v0.1/v0.1.0/sp-cli-host-api-panel.js'

// onReady additions
this._shell    = this.$('.host-shell')
this._hostApi  = this.$('.host-api-panel')
this._tabs     = [...this.$$('.tab-btn')]   // $$ = querySelectorAll in shadow
this._panels   = [...this.$$('.tab-panel')]
this._tabs.forEach(btn => btn.addEventListener('click', () => this._activateTab(btn.dataset.tab)))

// open additions (after existing setStack calls)
this._shell  ?.open?.(stack)
this._hostApi?.open?.(stack)

// new method
_activateTab(name) {
    this._tabs  .forEach(b => b.classList.toggle  ('active', b.dataset.tab   === name))
    this._panels.forEach(p => p.classList.toggle  ('active', p.dataset.panel === name))
}
```

**CSS for tabs (add to each detail CSS):**
```css
.detail-tabs   { display: flex; gap: 4px; margin-bottom: 8px; border-bottom: 1px solid var(--color-border, #ddd); }
.tab-btn       { background: none; border: none; padding: 6px 12px; cursor: pointer; color: var(--color-text-secondary); border-bottom: 2px solid transparent; }
.tab-btn.active{ color: var(--color-primary, #0066cc); border-bottom-color: var(--color-primary, #0066cc); }
.tab-panel     { display: none; }
.tab-panel.active { display: block; }
```

**Affected files (10 files each = 30 edits total):**
```
components/sp-cli/sp-cli-docker-detail/v0/v0.1/v0.1.0/sp-cli-docker-detail.{js,html,css}
components/sp-cli/sp-cli-firefox-detail/v0/v0.1/v0.1.0/sp-cli-firefox-detail.{js,html,css}
components/sp-cli/sp-cli-elastic-detail/v0/v0.1/v0.1.0/sp-cli-elastic-detail.{js,html,css}
components/sp-cli/sp-cli-neko-detail/v0/v0.1/v0.1.0/sp-cli-neko-detail.{js,html,css}
components/sp-cli/sp-cli-vnc-detail/v0/v0.1/v0.1.0/sp-cli-vnc-detail.{js,html,css}
```

**Acceptance:**
- [ ] Three tabs visible in each updated detail
- [ ] Info tab shows all existing content without regression
- [ ] Terminal tab shows the `sp-cli-host-shell` widget
- [ ] Host API tab shows the `sp-cli-host-api-panel` widget
- [ ] Tab switch does not re-fetch stack data
- [ ] `$$` helper exists on `SgComponent` or is implemented as `this._root.querySelectorAll`

> Note on `$$`: check whether `SgComponent` exposes `$$` for `querySelectorAll`. If not, use `Array.from(this.shadowRoot.querySelectorAll('.tab-btn'))` instead of `this.$$('.tab-btn')`.

---

## Task 4 — `sp-cli-host-api-panel` widget

The simplest task — an iframe wrapper, 5 lines of meaningful JS.

**Path:**
```
sgraph_ai_service_playwright__api_site/components/sp-cli/_shared/sp-cli-host-api-panel/v0/v0.1/v0.1.0/
    sp-cli-host-api-panel.js
    sp-cli-host-api-panel.html
    sp-cli-host-api-panel.css
```

**HTML:**
```html
<div class="panel-wrap">
  <p class="unavailable hidden">Host API not yet available for this stack.</p>
  <iframe class="api-frame" title="Host Control Plane API" frameborder="0"></iframe>
</div>
```

**JS:**
```javascript
import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

class SpCliHostApiPanel extends SgComponent {
    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-host-api-panel' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._frame       = this.$('.api-frame')
        this._unavailable = this.$('.unavailable')
        if (this._pendingStack) { this.open(this._pendingStack); this._pendingStack = null }
    }

    open(stack) {
        if (!this._frame) { this._pendingStack = stack; return }
        const url = stack.host_api_url || (stack.public_ip ? `http://${stack.public_ip}:9000` : '')
        if (!url) {
            this._unavailable.classList.remove('hidden')
            this._frame.classList.add('hidden')
            this._frame.src = ''
        } else {
            this._unavailable.classList.add('hidden')
            this._frame.classList.remove('hidden')
            this._frame.src = `${url}/docs`
        }
    }
}

customElements.define('sp-cli-host-api-panel', SpCliHostApiPanel)
```

**CSS:** Match `sp-cli-api-view.css` — `color-scheme: light; background: #fff`. Full height iframe, no border, no dark bleed-through.

**Acceptance:**
- [ ] Iframe loads `{host_api_url}/docs` when URL is present
- [ ] "Unavailable" message shown when URL is empty
- [ ] White background (consistent with sp-cli-api-view)

---

## Task 5 — `index.html` script tags

**File:** `sgraph_ai_service_playwright__api_site/admin/index.html`

Add three `<script type="module">` tags in the `<!-- shared widgets -->` section alongside `sp-cli-launch-form`:

```html
<!-- host control plane widgets -->
<script type="module" src="../components/sp-cli/_shared/sp-cli-host-shell/v0/v0.1/v0.1.0/sp-cli-host-shell.js"></script>
<script type="module" src="../components/sp-cli/_shared/sp-cli-host-api-panel/v0/v0.1/v0.1.0/sp-cli-host-api-panel.js"></script>
<script type="module" src="../components/sp-cli/_shared/sp-cli-host-terminal/v0/v0.1/v0.1.0/sp-cli-host-terminal.js"></script>
```

The third one (host-terminal) can wait until Task 2 is built. Tags are not harmful if the file doesn't exist yet — the browser will simply get a 404 for that module.

---

## Task 6 — Tests

**File:** `tests/unit/api_site/test_Admin__Dashboard__Components.py`

Add two new test classes at the bottom:

```python
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
```

---

## Build order

```
Task 0 (Schema__Stack__Summary — optional)
Task 4 (sp-cli-host-api-panel)  ─┐
Task 1 (sp-cli-host-shell)      ─┤─→ Task 3 (tab wiring) → Task 5 (index.html) → Task 6 (tests)
Task 2 (sp-cli-host-terminal)   ─┘  (skip until Phase 2 WebSocket backend is ready)
```

Tasks 1 and 4 are independent of each other. Do both, then Task 3 (which uses both). Task 2 is optional for this slice.

---

## Acceptance checklist

- [ ] `sp-cli-host-shell` trio exists and is non-empty
- [ ] `sp-cli-host-api-panel` trio exists and is non-empty
- [ ] Docker/Firefox/Elastic/Neko/VNC detail HTML files each have Terminal + Host API tabs
- [ ] Tab switching works without page reload or data re-fetch
- [ ] Shell widget shows "unavailable" when `host_api_url` is empty
- [ ] Host API iframe shows white background (no dark theme bleed-through)
- [ ] `index.html` has script tags for both new shared widgets
- [ ] All 11 new tests in `Test_Host_Control_Widgets` pass
- [ ] All 30 new parametrised tests in `Test_Detail_Host_Tabs` pass
- [ ] Existing tests still pass (run `pytest tests/unit/api_site/` before pushing)
