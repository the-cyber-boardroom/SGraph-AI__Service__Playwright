# 02 — Open threads

Ranked by what's most actionable in a single slice.

## 1. Brand the caddy-security login page (next slice — small)

**Goal:** replace the default green caddy-security login form with one that
matches SG/Send styling.

**Where to edit:**
- `sgraph_ai_service_playwright__cli/vnc/service/Vnc__Caddy__Template.py`
  → `CADDYFILE_TEMPLATE` → `authentication portal sg_portal { ui { ... } }`.
- caddy-security has `theme custom`, `logo URL`, and per-template
  overrides. See greenpau/caddy-security docs for the `ui` block options.
- For full HTML/CSS overrides we need to bind-mount a templates dir into
  the caddy container. Add the template files under
  `sgraph_ai_service_playwright__cli/vnc/caddy_assets/templates/` and
  mount in `Vnc__Compose__Template.COMPOSE_TEMPLATE`.

**Tests to add:** `test_Vnc__Caddy__Template.py` — assert the customised
`title`, `logo_url`, etc. appear in the rendered Caddyfile.

**Done when:** `https://{ip}/login` shows the SG/Send logo + title and the
form has our colours. Manual smoke test is fine; no need for a live deploy
test in this slice.

## 2. Cookie-based mitmweb probe (small)

**Goal:** restore `flow_count` in `sp vnc health`.

The probe currently hits `/healthz` for liveness, and `/mitmweb/flows`
without a JWT cookie returns 302. Make `flows_listing()` log in first,
keep the cookie, then fetch flows.

**Where to edit:**
- `sgraph_ai_service_playwright__cli/vnc/service/Vnc__HTTP__Base.py`
  → already wraps `requests` and threads through `username` + `password`.
  Add a `session()` helper that does POST `/login` once and returns a
  `requests.Session` with the cookie.
- `sgraph_ai_service_playwright__cli/vnc/service/Vnc__HTTP__Probe.py`
  → `flows_listing` uses the new session helper.

**Tests:** unit + the existing `_Fake_HTTP` shape needs a `session()`
method. Add `test_flows_listing__authenticated` to the probe tests.

**Done when:** `sp vnc health --password X` reports a non-`-1` `flow_count`.

## 3. Deploy-via-pytest test for the caddy build (medium)

**Goal:** catch caddy-security plugin breakage before an operator hits it.

Pattern is documented in `library/guides/v3.1.1__testing_guidance.md` —
deploy tests live under `tests/deploy/` and run sequentially
(`test_1__create`, `test_2__health`, `test_3__delete`).

**Sketch:**
```python
# tests/deploy/sgraph_ai_service_playwright__cli/vnc/test_caddy_deploy.py
class test_caddy_deploy(TestCase):
    def test_1__create_stack(self):     # sp vnc create with auto-generated password
        ...
    def test_2__caddy_healthz_ok(self): # GET /healthz returns 200 within 5 min
        ...
    def test_3__login_form_renders(self):  # GET /login returns 200 with HTML
        ...
    def test_4__authenticated_root_proxies_to_chromium(self):  # POST /login then GET / through requests.Session
        ...
    def test_9__delete_stack(self):
        ...
```

The big risk this catches: Caddy 2-builder tag moves, caddy-security
release breaks the Caddyfile DSL, or AL2023 docker can't fetch the
xcaddy modules.

**Effort:** half-day; needs an AWS profile with EC2 + IAM + SSM perms.

## 4. Wire VNC routes into Fast_API__SP__CLI (small)

**Goal:** `sp vnc list` should also be reachable as `GET /vnc/stack/list`.

The Tier-2B route classes already exist:
- `sgraph_ai_service_playwright__cli/vnc/fast_api/routes/Routes__Vnc__Stack__List.py`
- `Routes__Vnc__Stack__Info`, `Routes__Vnc__Stack__Create`, `Routes__Vnc__Stack__Delete`, `Routes__Vnc__Health`, `Routes__Vnc__Flows`.

What's missing: the registration call in `Fast_API__SP__CLI.add_routes()`.
See how `prom` and `os` are registered there — copy that shape.

**Caveat:** the `create_stack` route uses the `body: dict` workaround
(see `Routes__Prometheus__Stack` for the pattern) because Pydantic schema
generation chokes on Type_Safe nested types directly.

**Tests:** mirror `tests/unit/sgraph_ai_service_playwright__cli/prometheus/fast_api/`
structure for VNC.

## 5. Optional GitHub OIDC backend on the same Caddy portal (medium)

**Goal:** enable `Sign in with GitHub` on the login page; gate by org
membership.

caddy-security supports `oauth2 github` as a backend. Add it as a SECOND
`backend` in the same `authentication portal sg_portal { backend ... }`.
The local password backend stays — operators can still use the password
when GitHub is unreachable.

**Effort:** half-day if you already have a GitHub OAuth app; up to 1.5
days if you need to provision the OAuth app + figure out the
`the-cyber-boardroom` org-membership claim.

## 6. Update or delete the v0.1.118 branded-login brief (admin task)

The brief at `team/comms/briefs/v0.1.118__vnc-branded-login/` was written
BEFORE the Caddy swap shipped. It still recommends "Option 1 — FastAPI
auth sidecar" as the primary path, but we picked Option 2 (Caddy).

Two clean options:
- (a) Delete the brief — it's superseded by the actual implementation.
- (b) Update `04__decision.md` to record "Picked Option 2 — Caddy" with a
  one-paragraph rationale and a pointer to commit `b9123d1`.

Recommend (b) so future-you can find the decision rationale.

## 7. Admin UI integration (cross-team)

There's a parallel brief at `team/comms/briefs/v0.1.118__admin-ui-vnc-iframe-pane/`
covering iframe embedding the chromium viewer in the admin dashboard.
Note: with Caddy in place, the "Approach B pre-warm fetch" hack from
that brief becomes unnecessary — once the user logs in via Caddy's
`/login`, the JWT cookie is inherited by the iframe automatically.
Update that brief if the admin UI team starts the work.

## Lower-priority backlog (scope creep — only if specifically requested)

- Caddy `tls internal` still produces a cert from a local CA; browsers
  show "Not Secure". For real "no warning" we'd need DNS + ACME, which
  breaks the throwaway model. Track in `team/comms/briefs/` if revisited.
- Logout link injected into the noVNC viewer overlay — out of scope per
  `02__login-page-spec.md` in the branded-login brief.
- Per-user accounts — currently single-user (`operator`). Trivial to
  extend (caddy-security `users.json` can hold many users).
