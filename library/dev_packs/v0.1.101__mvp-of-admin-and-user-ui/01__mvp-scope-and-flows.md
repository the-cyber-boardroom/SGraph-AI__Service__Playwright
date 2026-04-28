# 01 — MVP Scope and Flows

**Status:** PROPOSED
**Read after:** `README.md`
**Read before:** `02__backend-changes.md`, `03__ui-design-and-components.md`

---

## What gets built

Two static apps + three small backend additions. That's it. Everything else listed in the larger v0.22.19 commercial brief is deferred.

```
sgraph_ai_service_playwright__api_site/
├── index.html              ← existing — landing page, [Admin] / [Provision] buttons
├── admin/
│   ├── index.html          ← cross-stack dashboard
│   └── admin.js            ← page controller
├── user/
│   ├── index.html          ← per-type "Start" cards
│   └── user.js             ← page controller
├── shared/
│   ├── api-client.js       ← THE ONLY fetch boundary
│   ├── catalog.js          ← caches /catalog/types
│   ├── poll.js             ← health-poll loop with back-off
│   ├── tokens.css          ← shared CSS variables
│   └── components/
│       ├── sg-api-client.js
│       ├── sg-auth-panel.js
│       ├── sg-header.js
│       ├── sg-stack-grid.js
│       ├── sg-stack-card.js
│       ├── sg-create-modal.js
│       └── sg-toast-host.js
├── cookie.js               ← existing, kept
└── storage.js              ← existing, kept
```

The existing `app.js`, `health.js`, `style.css`, and `index.html` files in the root of `__api_site/` are absorbed: their useful patterns (X-API-Key flow, cookie storage, link building) move into `shared/` modules. The root `index.html` evolves into a landing page that links to `/admin/` and `/user/`.

## The phasing decision (why three live tiles + two stubs)

Per the brief README: linux + docker + elastic are live in this MVP. OpenSearch and VNC are "coming soon" tiles — visible in both UIs, greyed out, no [Start] button.

**Why three live and not five:**

- Two (linux + docker only) is too thin for a demo. Three diverse stack types — bare Linux (~60s boot), Docker host (~10 min boot, slower demo punch), and Elastic+Kibana (~90s boot, visually different output) — makes the demo land.
- Five (adding opensearch + vnc) requires either waiting for `sp vnc` to ship (multi-day Dev work, separate brief) or a half-built tile that breaks confidence in the demo. Neither is acceptable.

**Why "coming soon" tiles instead of just hiding the unsupported types:**

- Demonstrates the catalog mechanism — adding a new type is a config-line change.
- Sets expectation with the demo audience that this is a platform, not a fixed list.
- Gives Sonnet the right shape for the grid component from day one (handles `available=false` entries) so adding live ones later is config, not refactor.

## The component architecture (one-pager)

Full detail in doc 03; here is the shape so the flows below make sense.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Browser                                       │
│                                                                        │
│  /admin/index.html  ┐                  ┌──── /user/index.html         │
│   admin.js  ─────── │                  │ ───── user.js                 │
│   (page             │  shared/         │  (page                        │
│    controller)      │  components/     │   controller)                 │
│                     │                  │                               │
│                     ├── sg-stack-grid  │                               │
│                     ├── sg-stack-card  │                               │
│                     ├── sg-create-modal│                               │
│                     ├── sg-auth-panel  │                               │
│                     ├── sg-header      │                               │
│                     ├── sg-toast-host  │                               │
│                     │                  │                               │
│                     ├── sg-api-client ◄┴──── ONLY fetch boundary       │
│                     │                                                  │
│                     └── poll.js, catalog.js, tokens.css                │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │ HTTPS, X-API-Key
                                     ▼
                        Fast_API__SP__CLI  (existing)
                        + Routes__Linux__Stack       (PR-1, mount existing)
                        + Routes__Docker__Stack      (PR-1, mount existing)
                        + Routes__Stack__Catalog     (PR-2, NEW)
                        + Routes__Elastic__Stack     (PR-3, NEW)
```

## The two UIs

### Admin UI — cross-stack dashboard

**Purpose:** one operator looking at everything, across all stack types, all at once.

**Page composition:**

```
┌──────────────────────────────────────────────────────────────────────┐
│ <sg-header> SG Playwright — Admin     [Settings ⚙]  [Refresh ↻]      │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│ Active Stacks (across all types)                                     │
│ <sg-stack-grid mode="admin-table">                                   │
│   ┌────────┬───────────────┬────────┬───────────────┬─────────────┐  │
│   │ Type   │ Name          │ State  │ Public IP     │ Actions     │  │
│   ├────────┼───────────────┼────────┼───────────────┼─────────────┤  │
│   │ linux  │ linux-quiet…  │ READY  │ 18.132.60.220 │ Info │ Stop │  │
│   │ docker │ docker-bold…  │ READY  │ 3.10.42.118   │ Info │ Stop │  │
│   │ elastic│ elastic-bold… │ STARTING│ —            │ —    │ Stop │  │
│   └────────┴───────────────┴────────┴───────────────┴─────────────┘  │
│                                                                      │
│ Stack Types (click any to provision)                                 │
│ <sg-stack-grid mode="type-cards">                                    │
│   [Linux ✓]  [Docker ✓]  [Elastic ✓]  [OpenSearch ⏳]  [VNC ⏳]       │
│                                                                      │
│ Recent Activity (last 10, in-memory only — not persisted in MVP)     │
│   22:14:08  Started linux-quiet-fermi    (3.0s)                      │
│   22:13:50  Stopped docker-old-curie     (1.2s)                      │
└──────────────────────────────────────────────────────────────────────┘
<sg-toast-host>                                                         │
<sg-create-modal>  (hidden until invoked)                               │
<sg-auth-panel>    (hidden if API key valid in localStorage)            │
```

What "admin" means in this MVP: anyone with the API key. There is no role separation. The admin UI just gives a wider lens — everything across all types, including disabled ones, plus a recent-activity strip that doesn't persist between page loads.

### User UI — per-type provisioning

**Purpose:** an operator who knows what kind of stack they want, clicks "Start", waits, gets access details.

**Page composition:**

```
┌──────────────────────────────────────────────────────────────────────┐
│ <sg-header> SG Playwright — Provisioning      [Settings ⚙]           │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│ Start a new environment                                              │
│ <sg-stack-grid mode="user-cards">                                    │
│ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ ┌──────┐   │
│ │ 🐧 Linux   │ │ 🐳 Docker  │ │ 🔍 Elastic │ │OpenSearch│ │ VNC  │   │
│ │            │ │            │ │            │ │ COMING   │ │COMING│   │
│ │ Bare       │ │ AL2023 +   │ │ Elastic +  │ │ SOON     │ │ SOON │   │
│ │ AL2023.    │ │ Docker CE. │ │ Kibana on  │ │          │ │      │   │
│ │ SSM only.  │ │            │ │ EC2.       │ │          │ │      │   │
│ │            │ │            │ │            │ │          │ │      │   │
│ │ ~60s boot  │ │ ~10min     │ │ ~90s boot  │ │ disabled │ │disab.│   │
│ │ [ Start ]  │ │ [ Start ]  │ │ [ Start ]  │ │          │ │      │   │
│ └────────────┘ └────────────┘ └────────────┘ └──────────┘ └──────┘   │
│                                                                      │
│ Active stacks (yours — but in MVP "yours" = "all", no per-user yet)  │
│ <sg-stack-grid mode="user-active">                                   │
│   linux-quiet-fermi   READY    18.132.60.220   [Details] [Stop]      │
└──────────────────────────────────────────────────────────────────────┘
<sg-create-modal>  (with progress; appears after [Start])               │
<sg-toast-host>                                                         │
<sg-auth-panel>                                                         │
```

The "coming soon" tiles are read directly from `/catalog/types` where `available=false`. **No client-side feature flag.** Adding OpenSearch in a follow-up brief is one server-side line: flip `available` to `true` for OPENSEARCH in `Stack__Catalog__Service`. Same for VNC.

## The provisioning flow (the demo's centrepiece)

```
═══════════════════════════════════════════════════════════════════════════
USER UI FLOW — "Start a Linux stack"
═══════════════════════════════════════════════════════════════════════════

t=0      User clicks "Start" on the Linux tile
         └─ user.js reads catalog entry for LINUX (cached from page load)
         └─ user.js shows <sg-create-modal type="linux">

           ┌─────────────────────────────────────────────────────────┐
           │ Start a Linux stack                              [✕]    │
           │                                                         │
           │  Region:        [eu-west-2 ▼]                           │
           │  Instance type: [t3.medium ▼]                           │
           │  Auto-stop:     [ 4 ▼] hours                            │
           │                                                         │
           │  ▼ Advanced (collapsed)                                 │
           │                                                         │
           │                              [ Cancel ]  [ Start → ]    │
           └─────────────────────────────────────────────────────────┘

t=0.1    User clicks [Start →]
         └─ user.js calls api-client.createStack('linux', {region, instance_type, max_hours})
         └─ api-client: POST /linux/stack
                Body:    { stack_name: "", region: "eu-west-2",
                           instance_type: "t3.medium", from_ami: "",
                           caller_ip: "", max_hours: 4, extra_ports: [] }
                Headers: X-API-Key: <from localStorage>

         Server: Linux__Service.create_stack(...)
              ├─ Linux__SG__Helper          creates SG (Stack__Naming.sg_name_for_stack)
              ├─ Linux__AMI__Helper         resolves latest AL2023 AMI (since from_ami="")
              ├─ Linux__User_Data__Builder  renders cloud-init bash
              └─ Linux__Launch__Helper      runs the instance via Ec2__AWS__Client

t=2-5s   Server returns Schema__Linux__Create__Response:
              {
                "stack_info": {
                  "stack_name":     "linux-quiet-fermi",
                  "instance_id":    "i-0a1b2c3d…",
                  "region":         "eu-west-2",
                  "ami_id":         "ami-…",
                  "instance_type":  "t3.medium",
                  "state":          "PENDING",
                  "public_ip":      "",
                  "allowed_ip":     "82.46.x.x",
                  "uptime_seconds": 0
                },
                "message":     "stack launched",
                "elapsed_ms":  3000
              }

         user.js swaps the create form for a progress panel:

           ┌─────────────────────────────────────────────────────────┐
           │ Provisioning linux-quiet-fermi                          │
           │                                                         │
           │ [████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 5%               │
           │                                                         │
           │ Status:  PENDING  (waiting for instance to start)       │
           │ Elapsed: 0:03                                           │
           │ Expected: ~1:00                                         │
           │                                                         │
           │                                       [ Cancel & Stop ] │
           └─────────────────────────────────────────────────────────┘

t=5s     user.js starts polling: GET /linux/stack/linux-quiet-fermi/health
         └─ poll.js cadence: every 3s for first 30s, then 5s, capped at 300s for linux

t=8s     Health = { state: "PENDING", healthy: false, ssm_reachable: false,
                    message: "instance not yet running" }
         └─ Bar advances to ~10% (interpolated against expected_boot_seconds)
         └─ Status text updates: "PENDING (instance starting)"

t=30s    Health = { state: "RUNNING", healthy: false, ssm_reachable: false,
                    message: "instance running, SSM not yet reachable" }
         └─ Bar at ~50% (state transition is the strongest signal of progress)
         └─ Status text: "RUNNING (waiting for SSM agent)"

t=55s    Health = { state: "RUNNING", healthy: true, ssm_reachable: true,
                    message: "ssm-reachable" }
         └─ user.js stops polling, fetches GET /linux/stack/linux-quiet-fermi
            for full Schema__Linux__Info (now includes public_ip)
         └─ Bar fills to 100%, panel transitions to:

           ┌─────────────────────────────────────────────────────────┐
           │ ✅ linux-quiet-fermi is READY               (54.2s)      │
           │                                                         │
           │ Public IP:    18.132.60.220                              │
           │ Instance:     i-0a1b2c3d…                                │
           │ State:        RUNNING                                    │
           │ Allowed IP:   82.46.x.x                                  │
           │                                                         │
           │ Connect via SSM:                                         │
           │   aws ssm start-session --target i-0a1b2c3d…  [📋 Copy]  │
           │                                                         │
           │ Auto-stops in 4 hours.                                   │
           │                                                         │
           │            [ Done ]                          [ Stop ]    │
           └─────────────────────────────────────────────────────────┘

t=…      User clicks [Done]: modal closes, returns to tile grid + active strip
         User clicks [Stop]: api-client.deleteStack('linux','linux-quiet-fermi')
              ├─ DELETE /linux/stack/linux-quiet-fermi
              ├─ on success, modal closes
              └─ refresh /catalog/stacks; active strip updates
═══════════════════════════════════════════════════════════════════════════
```

The same flow applies to docker (~10 min boot, max-poll 600s — matches the `--wait` flag) and elastic (~90s boot, similar pattern). The progress bar's `expected_boot_seconds` comes from the catalog entry per type.

## Polling design (`poll.js`)

| Window | Cadence | Why |
|---|---|---|
| 0–30s | 3s | Maximum demo responsiveness during the first state transitions |
| 30–120s | 5s | Most state changes happen before this; 5s is fine |
| 120s+ | 10s | Long-tail boot (docker CE installing) — don't hammer the API |
| Tab hidden (`document.visibilityState !== 'visible'`) | paused | Save calls; resume on visibility change |
| 3 consecutive network errors | exponential back-off, then "Connection lost" UI | Server-side provisioning continues; user can [Retry] |
| Wall-clock max | 300s for linux/elastic, 600s for docker | Matches the CLI `--wait` timeouts. Beyond this, show "Boot taking longer than expected" with [Wait another 60s] / [Stop and tear down]. |

The progress bar interpolates against the catalog entry's `expected_boot_seconds`, **capped at 95% until `healthy=true`**. No fake easing. Health is the truth; the bar shows known checkpoints.

## Connection panel — shared between UIs

Both UIs use the same `<sg-auth-panel>`. Lifted from the existing `__api_site/index.html`, generalised. Stores three values in localStorage:

| localStorage key | Purpose | Default |
|---|---|---|
| `sp-cli-base-url` | API base | `window.location.origin` |
| `sp-cli-api-key` | The key | (none — prompts on first visit) |
| `sp-cli-api-key-name` | Header name | `X-API-Key` |

The panel auto-shows when:

- No API key is in localStorage on page load.
- Any API call returns 401.
- The user clicks the [Settings ⚙] button in `<sg-header>`.

On successful save, the panel runs `GET /` (which exists today, returns a small status payload from `osbot-fast-api`) to verify auth, shows green tick or error, then collapses.

## Error handling — what each HTTP code means to the UI

| Code | Cause | UI behaviour |
|---|---|---|
| 200 | Success | Render data |
| 401 | Missing/invalid API key | Show `<sg-auth-panel>`, stop |
| 404 | Stack not found by name | Toast: "Stack no longer exists", refresh the list |
| 422 | Type_Safe validation failed (`register_type_safe_handlers`) | Show field-level error in the create modal |
| 500 | AWS or backend exploded | Toast with the message body, do NOT auto-retry |
| 5xx (network) | Lost connection | Treat as "connection lost" pattern in the polling design above |

The 422 handler is wired in `Fast_API__SP__CLI.setup()` via `register_type_safe_handlers(self.app())` and reliably surfaces Type_Safe primitive validation errors. The UI can trust 422 to mean "your request body was wrong", not "the server is broken".

## What's deliberately rough in the MVP

These exist as bullets so reviewers don't ask "why didn't you handle X" — answer is "deliberately deferred":

- **No persistence of recent activity.** The activity strip in admin UI is in-memory; refresh wipes it. Real activity log is its own follow-up.
- **No cancel-during-boot.** The [Cancel & Stop] button on the progress modal does fire `DELETE /{type}/stack/{name}` but if the AWS launch is mid-flight, the delete may race the create. Acceptable for the MVP; surfacing the race nicely is a polish item.
- **No multi-region UI.** Region is a per-create dropdown defaulting to `eu-west-2`; the active-stacks list shows all stacks in the region the API is configured for. Multi-region orchestration is out of scope.
- **No bulk delete in user UI.** Admin UI has [Stop] per row; no [Stop All]. (The `DELETE /{type}/stack/delete-all` endpoint exists for ec2/playwright but the linux/docker/elastic services don't expose a delete-all method consistently. Adding one for the MVP is unnecessary.)
- **No type filter in admin grid.** Cross-section table shows everything together. Filter UI is trivial to add later if the active list grows.
- **No real-time updates.** Polling, not WebSockets. If the user has the admin tab open, they see updates within the polling window. Acceptable.

## What good looks like at the end of this MVP

- A demo-able workflow: log in, click start, watch progress, see READY, copy the SSM command, stop the stack.
- Three live tiles, two coming-soon tiles, all driven by one server-side catalog.
- The two UIs share components and a single fetch boundary — adding a tile is config, not refactor.
- The full stack runs locally on `localhost:8080` (per `scripts/run_sp_cli.py`) with no auth, and on the deployed Lambda with the X-API-Key.
- Test coverage on the new backend pieces matches the existing `linux/docker` patterns (~10 unit tests per route class via `osbot-fast-api` TestClient, plus a mounting test on `Fast_API__SP__CLI`).
- `grep` proofs that the layering rules hold (no fetch outside the client, no localStorage outside the auth boundary).

That is the whole MVP. Doc 02 specifies the exact backend changes; doc 03 specifies the exact UI structure.
