# v0.1.118 — Branded login for sp vnc stacks (alternatives to HTTP Basic auth)

**Status:** PROPOSED — pick one, then write a follow-up implementation brief
**Companion to:** `v0.1.118__admin-ui-vnc-iframe-pane/`
**Replaces:** the current `auth_basic` block in `Vnc__User_Data__Builder.NGINX_DEFAULT_CONF`

---

## Why move off HTTP Basic

| Pain today | Symptom |
|---|---|
| Browser-native popup | Looks broken, can't be styled, jarring inside an iframe |
| No branding | "operator" literal + ugly modal — no place for our logo, hint text, or "forgot password?" copy |
| No session UX | Re-prompts when cookies cleared; no "remember me", no logout button |
| Cross-origin iframe pre-warm hack | `02__auth-flow.md` had to invent a hidden `fetch()` to seed the auth cache — fragile |
| No 2FA / MFA path | Hard-coded `operator:bcrypt` is the ceiling |

---

## Bar we want to clear

A small, brandable login page served from `https://{public_ip}/login`. User
enters the password, gets a signed cookie, sees the chromium viewer.
Survives a refresh. Logout button visible. Iframe-friendly. Zero extra
provisioning steps for the operator.

---

## Five alternatives

Ranked from least to most invasive. Pick one in `04__decision.md`.

### 1. **FastAPI auth sidecar + `nginx auth_request`** ★ recommended

Add a 4th container (`sg-auth`) running a tiny FastAPI app — same stack as
the rest of this repo, same `Type_Safe` patterns. Endpoints:

- `GET  /login`   → branded HTML form (tailwind / our existing CSS).
- `POST /login`   → verifies password via bcrypt, sets `sg-vnc-session=<HMAC token>` HttpOnly Secure cookie, redirects to `/`.
- `GET  /auth`    → returns 200 if the cookie HMAC matches; 401 otherwise. Called by nginx on every request.
- `POST /logout`  → clears the cookie.

nginx config switches from `auth_basic` to:

```nginx
location = /auth { internal; proxy_pass http://sg-auth:8000/auth; }
location /login  { proxy_pass http://sg-auth:8000/login; }

location / {
    auth_request     /auth;
    error_page 401   = @login_redirect;
    proxy_pass       http://chromium:3000/;
    ...
}

location @login_redirect { return 302 /login?next=$request_uri; }
```

**Pros**
- Pure Python, fits the rest of the codebase (one new tier-1 service per `team/roles/architect/ROLE.md`).
- Full control over branding — we ship one `login.html` template.
- Cookie-based, so iframes Just Work after first login.
- Easy to extend later: TOTP, magic-link email, GitHub OAuth.

**Cons**
- One more container in the compose template (small — `python:3.12-slim` + `fastapi[standard]` + `passlib[bcrypt]`).
- Need to bake the bcrypt hash into a file the auth service reads at boot (already do this for nginx htpasswd — reuse the same file).

**Effort:** ~half-day for the slice (sidecar Dockerfile + 1 FastAPI app + nginx conf swap + tests).

---

### 2. **Caddy instead of nginx**

Replace nginx with Caddy and use the `caddy-security` plugin (or `forward_auth` to a tiny verifier).

Caddy 2 has a richer auth story baked in (`basicauth` is still ugly, but
`forward_auth` to anything cookie-based is one line). Combined with a
`templates` directive Caddy can serve a styled login page directly.

**Pros**
- Same one-binary simplicity; fewer moving parts than nginx + sidecar.
- Auto-HTTPS via internal CA — would also remove the self-signed-trust
  prompt for the iframe (bonus win).

**Cons**
- Swaps a dependency the project has already standardised on.
- Caddy module ecosystem is smaller and a bit more bleeding-edge.
- Needs its own `Caddyfile` template — equivalent surface area to (1).

**Effort:** ~full day; bigger swap.

---

### 3. **OAuth2-Proxy in front of nginx**

Drop in `oauth2-proxy` configured against an OIDC provider (GitHub,
Cognito, our own keycloak). It has a built-in branded sign-in page
(`--display-htpasswd-form`) AND can do real OIDC for SSO.

**Pros**
- Battle-tested, drop-in container.
- Free MFA / org-membership gates if we wire it to GitHub or Cognito.
- The login page is themable.

**Cons**
- Adds a real dependency on an OIDC provider (or we use its built-in
  htpasswd mode, which is essentially (1) but in Go).
- Heavyweight for an ephemeral debug stack.
- No way to brand "this is the SG/Send debug viewer for stack
  vnc-clever-noether" without forking the templates.

**Effort:** ~half-day if we go htpasswd-mode; full day with OIDC.

---

### 4. **Authelia or Authentik**

Full SSO portal in front of nginx. Real branding portal, MFA, audit log,
session management dashboard.

**Pros**
- The polished answer. Good if `sp vnc` becomes more than a debug tool.

**Cons**
- Massive overkill for an ephemeral one-operator debug stack.
- Needs a Postgres or sqlite + extra config files.
- Cold-start time on a t3.large is meaningful.

**Effort:** 1-2 days.

Recommend NOT picking this for sp vnc; revisit if/when we have a real
multi-user dashboard.

---

### 5. **Cloudflare Access / AWS Cognito (managed, no auth on the box)**

Don't run auth on the EC2 at all. Put a CF or Cognito gate in front of a
public DNS name pointing at the EC2.

**Pros**
- No code; the auth UI is fully managed and brandable.
- Real TLS cert (no self-signed prompt for the iframe).
- MFA, conditional access, audit log free.

**Cons**
- Requires a real DNS name per stack (or a shared `*.vnc.sg.example`).
- The whole "ephemeral, throwaway" model gets harder — DNS records to
  reap, CF apps to provision/delete.
- Adds a hard dependency on a managed service to do local dev.
- The `--open` SG flag becomes meaningless; we'd lock SG to CF egress IPs
  instead.

**Effort:** 2-3 days, mostly on the DNS + CF Tunnel plumbing.

Recommend revisiting if we ever expose `sp vnc` to non-engineers.

---

## Files in this brief

- `01__architecture-sketch.md` — concrete shape of the recommended option (1)
- `02__login-page-spec.md` — what the branded page should contain
- `03__cookie-and-session.md` — token shape, expiry, rotation
- `04__decision.md` — TBD, owner picks one
