# Architect locks needed before BV2.15

**Two decisions** the Architect must lock before BV2.15 (sidecar security hardening) opens. Both are flagged as open questions in `team/comms/briefs/v0.2.0__sg-compute__architecture/00__README.md`.

---

## Lock 1 — Cookie `HttpOnly=true` flip

### Question

Currently the sidecar's auth cookie has `HttpOnly=false` (set by `Routes__Host__Auth.set_auth_cookie`). Code review flagged this as 🔴 R2: combined with the reflective CORS, JS exfiltration of the cookie is possible from a malicious origin.

### Recommended decision

**Flip to `HttpOnly=true`.**

### Why this is safe for the iframe pattern

The cookie is consumed by the BROWSER, not by JS. The iframe loads `/host/shell/page` → browser includes the cookie automatically on the WebSocket upgrade. JS in the iframe doesn't need to read the cookie. Defence-in-depth: even if a future XSS bug appears in the iframe page, the cookie is exfiltration-proof from JS.

### Risk

**None known.** The iframe pattern is currently working with `HttpOnly=false` only because nothing actively reads `document.cookie` to check for the auth cookie's presence. Verify in the FE smoke test post-BV2.15 that the Terminal tab + Host API tab still work.

### Decision

[ ] **Approved** — flip to `HttpOnly=true`.
[ ] **Deferred** — keep `HttpOnly=false` and document the threat model accepted.
[ ] **Other** — specify.

---

## Lock 2 — CORS origin allowlist

### Question

Currently the sidecar's `Fast_API__Host__Control` uses `allow_origin_regex=r".*"` + `allow_credentials=True`. Code review flagged this as 🔴 R1: any origin can reflect the cookie.

### Recommended decision

**Replace `r".*"` with an explicit allowlist read from env var.**

```python
SG_COMPUTE__SIDECAR__CORS_ALLOWED_ORIGINS = "http://localhost:8000,http://localhost:8080,https://admin.sgraph.ai"
```

Default for unset env var: empty list (force production deployments to be explicit). Local dev: include `http://localhost:8000`.

### What origins should be in the allowlist?

The dashboard origins. Today:
- `http://localhost:8000` (local dev)
- `http://localhost:8080` (alternative local dev port)
- The dashboard's deployed origins (Lambda Web Adapter URL, CF distribution, etc.)

Operator + DevOps to confirm production origins before the BV2.15 PR opens.

### Risk

If the allowlist is wrong, the dashboard breaks (CORS preflight fails). Mitigation: BV2.15 includes a negative-path test asserting that an unknown origin gets a CORS rejection.

### Decision

[ ] **Approved** — env-var-driven allowlist; default empty.
[ ] **Approved with default** — env-var-driven allowlist; sensible local-dev default included.
[ ] **Deferred** — keep `r".*"` and document the threat model accepted.
[ ] **Other** — specify.

### If approved — list of production origins

To be filled by Operator/DevOps before the PR opens:

- `https://...`
- `https://...`

---

## Once locked

Update [`v0.2.0__sg-compute__backend/BV2_15__sidecar-security-hardening.md`](../v0.2.0__sg-compute__backend/BV2_15__sidecar-security-hardening.md) "Open questions" section with the ratified decisions, then the BE dev can pick up BV2.15.

The decisions also propagate into [`v0.2.0__sg-compute__architecture/00__README.md`](../v0.2.0__sg-compute__architecture/00__README.md) "Open questions" table — strike the two rows when locked.
