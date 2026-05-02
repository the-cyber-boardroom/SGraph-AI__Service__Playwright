# Host Control Plane — Frontend Team Brief

**version** v0.22.20
**date** 02 May 2026
**from** Claude Code (frontend session)
**to** Frontend team (this Claude session)
**type** Dev brief

---

## Objective

Wire the host control plane into the Admin Dashboard so that each running stack's detail panel exposes:

1. A **Terminal tab** — command execution via `POST /host/shell/execute` (phase 1) and interactive shell via WebSocket (phase 2)
2. A **Host API tab** — Swagger docs iframe for the host control plane's own `/docs` page (mirrors what `sp-cli-api-view` does for the main SP CLI)

Architecture context: `v0.22.20__reference__host-control-plane-architecture.md` (same folder).

---

## What the Backend Provides (our inputs)

Two new fields on the stack object that arrives via `sp-cli:stack.selected`:

```javascript
stack.host_api_url            // "http://3.8.x.x:9000" — empty until boot complete
stack.host_api_key_vault_path // "/ec2/grand-wien/host-api-key" — empty until provisioned
```

**During development (before backend is live):** use `http://localhost:9000` as `host_api_url` and any non-empty string for `host_api_key_vault_path`. Build and test everything against a local dev server.

The API key itself is read from the vault via the existing `vault-bus.js` singleton. The detail components do not manage auth — they read the key from `vault-bus` and put it in the `X-API-Key` header on every request to `host_api_url`.

---

## Tasks

### Task 1 — `sp-cli-host-shell` shared widget

A read-only command execution panel. Reuses the existing `SgComponent` 3-file pattern.

```
sgraph_ai_service_playwright__api_site/components/sp-cli/_shared/sp-cli-host-shell/v0/v0.1/v0.1.0/
    sp-cli-host-shell.js
    sp-cli-host-shell.html
    sp-cli-host-shell.css
```

**HTML template:**

```html
<div class="shell-panel">
  <div class="shell-toolbar">
    <select class="cmd-select"></select>
    <button class="btn-run">Run</button>
    <button class="btn-clear">Clear</button>
  </div>
  <div class="shell-output"></div>
</div>
```

**JS behaviour:**

- `open(stack)` is called by the detail component when it becomes active. Stores `host_api_url` and reads the API key from vault-bus.
- The `<select>` is pre-populated with the SHELL_COMMAND_ALLOWLIST subset that makes sense for a UI:
  ```javascript
  const QUICK_COMMANDS = [
      { label: 'List containers (ps)',   cmd: 'docker ps'      },
      { label: 'Disk usage',             cmd: 'df -h'          },
      { label: 'Memory',                 cmd: 'free -m'        },
      { label: 'Uptime',                 cmd: 'uptime'         },
      { label: 'Runtime version',        cmd: 'docker version' },
  ]
  ```
- "Run" calls `POST {host_api_url}/host/shell/execute` with `{ command: selectedCmd }` and `X-API-Key` header.
- Response `stdout + stderr` is appended to `.shell-output` as a timestamped `<pre>` block.
- "Clear" empties the output area.
- If `host_api_url` is empty, render a `<p class="unavailable">Host API not yet available</p>` message instead of the toolbar.

**CSS:** Dark terminal aesthetic. `.shell-output` uses `font-family: monospace; background: #1a1a1a; color: #d4d4d4`. Max-height with scroll.

**Acceptance:**
- Widget renders correctly when `host_api_url` is set
- Widget shows "unavailable" message when `host_api_url` is empty
- `Run` fires `POST /host/shell/execute`, output appears in panel
- `Clear` empties output

---

### Task 2 — `sp-cli-host-terminal` shared widget (phase 2 — interactive)

Interactive WebSocket terminal using xterm.js. This is a progressive enhancement over Task 1 — build after Task 1 is working.

```
sgraph_ai_service_playwright__api_site/components/sp-cli/_shared/sp-cli-host-terminal/v0/v0.1/v0.1.0/
    sp-cli-host-terminal.js
    sp-cli-host-terminal.html
    sp-cli-host-terminal.css
```

**Key implementation points:**

xterm.js is loaded from CDN (no bundler in this project):
```javascript
import('https://cdn.jsdelivr.net/npm/@xterm/xterm@5/+esm').then(({ Terminal }) => {
    this._term = new Terminal({ cols: 120, rows: 30, theme: { background: '#1a1a1a' } })
    this._term.open(this.$('.terminal-container'))
    this._connectWebSocket()
})
```

WebSocket connection: `new WebSocket(\`ws://${host}/host/shell/stream\`, [], { headers: { 'X-API-Key': key } })`.

Note: browsers do not support custom headers on WebSocket. The API key must be passed as a query parameter instead:
```javascript
const wsUrl = `${hostWsUrl}/host/shell/stream?api_key=${encodeURIComponent(apiKey)}`
```
The backend should validate `api_key` query param as a fallback to the `X-API-Key` header for WS endpoints only.

`open(stack)` initialises the terminal and connects. `close()` tears down the WebSocket.

**Acceptance:**
- Terminal renders in the shadow DOM
- Typing characters sends them over the WebSocket
- Server output appears in the terminal
- Resize event from the detail panel propagates to xterm's `term.resize()`

---

### Task 3 — Add Terminal + Host API tabs to detail components

Every plugin detail component that can run on an EC2 host gets two new tabs. Start with `docker`, `firefox`, `elastic`, `neko`, `vnc` — the five that are most likely to have an EC2 host behind them.

**Pattern (same for all affected details):**

In `sp-cli-{name}-detail.html`, add two new tab buttons and panels alongside the existing content:

```html
<div class="detail-tabs">
  <button class="tab-btn active" data-tab="info">Info</button>
  <button class="tab-btn" data-tab="shell">Terminal</button>
  <button class="tab-btn" data-tab="hostapi">Host API</button>
</div>
<div class="tab-panel active" data-panel="info">
  <!-- existing stack header + network info + SSM command etc. -->
</div>
<div class="tab-panel" data-panel="shell">
  <sp-cli-host-shell class="host-shell"></sp-cli-host-shell>
</div>
<div class="tab-panel" data-panel="hostapi">
  <sp-cli-host-api-panel class="host-api-panel"></sp-cli-host-api-panel>
</div>
```

Tab switching: pure CSS (`[data-panel].active { display: block }`) + a small `_activateTab(name)` helper in the JS. No framework.

In the JS `open(stack)` method, call:
```javascript
this.$('.host-shell')?.open?.(stack)
this.$('.host-api-panel')?.open?.(stack)
```

Import the two new components:
```javascript
import '../../../_shared/sp-cli-host-shell/v0/v0.1/v0.1.0/sp-cli-host-shell.js'
import '../../../_shared/sp-cli-host-api-panel/v0/v0.1/v0.1.0/sp-cli-host-api-panel.js'
```

**Acceptance:**
- Three tabs visible in each updated detail component
- Info tab shows existing content (no regression)
- Terminal tab shows `sp-cli-host-shell` widget
- Host API tab shows `sp-cli-host-api-panel` widget
- Tab switching does not re-fetch data

---

### Task 4 — `sp-cli-host-api-panel` shared widget

Wraps the host control plane's `/docs` Swagger page in an iframe — identical to `sp-cli-api-view` but scoped to a single stack's host API.

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
  <iframe class="api-frame" title="Host Control Plane API"></iframe>
</div>
```

**JS:**
```javascript
open(stack) {
    const url = stack.host_api_url
    if (!url) {
        this.$('.unavailable').classList.remove('hidden')
        this.$('.api-frame').classList.add('hidden')
        return
    }
    this.$('.api-frame').src = `${url}/docs`
}
```

**CSS:** Same as `sp-cli-api-view.css` — `color-scheme: light`, `background: #fff`, full-height iframe, no border.

**Acceptance:**
- Iframe loads `{host_api_url}/docs` when URL is present
- "Unavailable" message shown when URL is empty
- Matches sp-cli-api-view visual style (white background, no dark bleed-through)

---

### Task 5 — `index.html` + `admin.js` wiring

**`index.html`:** Add script tags for the two new shared widgets:
```html
<script type="module" src="../components/sp-cli/_shared/sp-cli-host-shell/v0/v0.1/v0.1.0/sp-cli-host-shell.js"></script>
<script type="module" src="../components/sp-cli/_shared/sp-cli-host-terminal/v0/v0.1/v0.1.0/sp-cli-host-terminal.js"></script>
<script type="module" src="../components/sp-cli/_shared/sp-cli-host-api-panel/v0/v0.1/v0.1.0/sp-cli-host-api-panel.js"></script>
```

No changes to `admin.js` are needed for Tasks 1–4. The detail components handle everything internally once `open(stack)` is called.

**Optional (if the interactive terminal from Task 2 is built):** xterm.js CDN is loaded lazily inside `sp-cli-host-terminal.js` — no additional `index.html` entry needed.

---

### Task 6 — Tests

Add to `tests/unit/api_site/test_Admin__Dashboard__Components.py`:

```python
SHARED_HOST_WIDGETS = ['sp-cli-host-shell', 'sp-cli-host-api-panel']

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

    def test_host_api_panel_loads_docs(self):
        js = shared_widget('sp-cli-host-api-panel')[0].read_text()
        assert '/docs' in js

    def test_host_api_panel_handles_empty_url(self):
        js = shared_widget('sp-cli-host-api-panel')[0].read_text()
        assert 'unavailable' in js.lower()

class Test_Detail_Host_Tabs:
    @pytest.mark.parametrize('name', ['docker', 'firefox', 'elastic', 'neko', 'vnc'])
    def test_detail_has_shell_tab(self, name):
        html = detail(name)[1].read_text()
        assert 'sp-cli-host-shell' in html

    @pytest.mark.parametrize('name', ['docker', 'firefox', 'elastic', 'neko', 'vnc'])
    def test_detail_has_host_api_tab(self, name):
        html = detail(name)[1].read_text()
        assert 'sp-cli-host-api-panel' in html
```

---

## Build Order

```
Task 4 (sp-cli-host-api-panel)  ─┐
Task 1 (sp-cli-host-shell)      ─┤→ Task 3 (tab wiring in details) → Task 5 (index.html) → Task 6 (tests)
Task 2 (sp-cli-host-terminal)   ─┘  (can merge after Task 1 works)
```

Tasks 1, 2, and 4 are independent of each other. Start with Task 1 (simpler, no xterm.js), Task 4 (trivial iframe), then Task 3 to wire them into detail panels.

---

## Constraints

- **No bundler.** All imports are ES module `import` statements. xterm.js is loaded from CDN with dynamic `import()`.
- **Shadow DOM.** All `SgComponent` subclasses use shadow DOM. `this.$('.foo')` queries within the shadow root — do not use `document.querySelector` inside a component.
- **3-file pattern.** Every component has `.js` + `.html` + `.css`. The HTML is the shadow template; CSS scopes to `:host`.
- **No framework.** Tab switching is plain JS + CSS. No React, no Vue, no Alpine.
- **API key from vault-bus only.** Never hardcode or store the API key in the component state beyond the lifetime of the `open()` call. Read from `vault-bus.js` on each `open(stack)`.
- **Graceful degradation.** If `host_api_url` is empty, render a clear "not yet available" message — never a broken iframe or a 404 error visible to the user.
- **Import new shared widgets inside the detail JS** (not only in `index.html`) so they are always loaded when the detail is loaded.

---

## Local Dev Setup

Until the backend ships, test against a local mock server:

```bash
# Install fast-api and run a minimal host control plane mock
pip install fastapi uvicorn
uvicorn mock_host_api:app --port 9000
```

Or use `json-server` / any HTTP mock that responds to `GET /host/status` and `POST /host/shell/execute`.

The detail component's `open(stack)` call can be triggered from the browser console for quick testing:

```javascript
document.querySelector('sp-cli-docker-detail').open({
    stack_name: 'test',
    type_id:    'docker',
    host_api_url:            'http://localhost:9000',
    host_api_key_vault_path: '/ec2/test/host-api-key',
})
```

---

## Acceptance Checklist (complete before pushing)

- [ ] `sp-cli-host-shell` trio exists and is non-empty
- [ ] `sp-cli-host-api-panel` trio exists and is non-empty
- [ ] `sp-cli-host-terminal` trio exists and is non-empty (Task 2, can ship after Task 1)
- [ ] Docker/Firefox/Elastic/Neko/VNC detail HTML files each have Terminal + Host API tabs
- [ ] Tab switching works without page reload or data re-fetch
- [ ] Terminal widget shows "unavailable" when `host_api_url` is empty
- [ ] Host API iframe shows white background (no dark theme bleed-through)
- [ ] `index.html` has script tags for all three new shared widgets
- [ ] All 6 new test cases in `Test_Host_Control_Widgets` pass
- [ ] All 10 new test cases in `Test_Detail_Host_Tabs` pass
- [ ] All existing 141+ tests still pass
