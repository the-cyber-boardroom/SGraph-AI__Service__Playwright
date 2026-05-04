# BV2.15 — Sidecar security hardening (cookie + CORS)

## Goal

Code review flagged 🔴 R1, R2, R3 — reflective CORS (`allow_origin_regex=r".*"` + `allow_credentials=True`) plus cookie `httponly=false` plus `samesite=lax` is a credential-theft / CSRF surface.

This phase locks the security model. **Architect must lock the cookie + CORS decisions before this phase starts** — see `architecture/00__README.md` open questions.

## Tasks

### Task 1 — Cookie hardening

In `sg_compute/host_plane/fast_api/routes/Routes__Host__Auth.py` (or wherever the cookie is set):

1. Flip `httponly=True` (was `False`).
2. Verify the iframe pattern still works in browser smoke test — the cookie should be sent automatically; JS shouldn't need to read it.
3. Set `Secure=True` when running behind HTTPS — read from env var `SG_COMPUTE__SIDECAR__SECURE_COOKIE` (default `True` for production).
4. Keep `samesite='lax'` — required for the iframe pattern.

### Task 2 — CORS origin allowlist

In `Fast_API__Host__Control.py`:

1. Replace `allow_origin_regex=r".*"` with `allow_origins=[...]` driven by an env var `SG_COMPUTE__SIDECAR__CORS_ALLOWED_ORIGINS` (comma-separated).
2. Default value (operator-friendly): `http://localhost:8000,http://localhost:8080`.
3. Production value (set in Lambda env or EC2 user-data): the dashboard's deployed origins.
4. If the env var is unset, default to a strict empty list (force production deployments to be explicit).
5. Document the env var in `architecture/03__sidecar-contract.md` § CORS contract.

### Task 3 — Test coverage

1. Add `Routes__Host__Auth` test coverage — set / clear cookie, redirect target, expired-key behaviour. **No mocks.**
2. Add negative-path tests — 401 with no auth, 401 with wrong key, 401 retains CORS headers.
3. Add a test for the env-var-driven origin allowlist — set env, assert CORS headers reflect the allowlist.

### Task 4 — Documentation

Update `architecture/03__sidecar-contract.md`:
- §3 CORS contract — remove the "Risk flagged" subsection; add the locked configuration.
- §2.2 Cookie attributes — flip `HttpOnly` to `true`.

## Acceptance criteria

- Cookie is `HttpOnly=True; Secure=True (when env says); SameSite=lax`.
- Iframe terminal still works in a browser smoke test.
- CORS allowlist is environment-driven; no `r".*"` regex anywhere in `Fast_API__Host__Control`.
- `Routes__Host__Auth` test file exists with set/clear/expired coverage.
- Negative-path test file exists.
- `unittest.mock.patch` count in `sg_compute__tests/host_plane/` is zero.
- Reality doc + architecture doc updated.

## Open questions

- **Architect locks** before this phase starts:
  - `httponly=true` (recommended, default).
  - Origin allowlist (recommended over r".*").

## Blocks / Blocked by

- **Blocks:** none.
- **Blocked by:** Architect ratification of the two security questions above.

## Notes

The iframe pattern relies on cookie auth. Flipping `HttpOnly=True` is **defence in depth** — it doesn't break the iframe (the browser still sends the cookie automatically) but it prevents JS exfiltration if the iframe page ever has an XSS bug.
