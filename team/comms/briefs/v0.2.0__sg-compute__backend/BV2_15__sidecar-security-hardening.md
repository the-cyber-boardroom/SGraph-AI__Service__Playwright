# BV2.15 — Sidecar security hardening (cookie HttpOnly)

## Architect locks (ratified 2026-05-05)

See [`v0.2.1__finish/architect-locks.md`](../v0.2.1__finish/architect-locks.md):

- **Lock 1 — Cookie `HttpOnly=true`:** ✅ APPROVED. Flip in this phase.
- **Lock 2 — CORS origin allowlist:** ⏸ DEFERRED to v0.3. Production origins are not yet defined; the reflective `r".*"` stays for v0.2.1. **DO NOT change the CORS config in this PR.**

This phase is therefore **scoped down** from the original brief. Cookie hardening + test coverage only.

## Goal

Code review flagged 🔴 R2 — cookie `HttpOnly=false` combined with reflective CORS = JS-exfiltration surface from any origin. Flipping `HttpOnly=true` removes the JS-exfiltration leg (defence in depth), independent of the CORS regex.

R1 (the `r".*"` regex) and R3 (`SameSite=lax`) remain accepted in v0.2.1 — see architect-locks.md "threat model accepted in the interim".

## Tasks

### Task 1 — Cookie hardening

In `sg_compute/host_plane/fast_api/routes/Routes__Host__Auth.py` (or wherever the cookie is set):

1. Flip `httponly=True` (was `False`).
2. Set `Secure=True` when running behind HTTPS — read from env var `SG_COMPUTE__SIDECAR__SECURE_COOKIE` (default `True` for production; allow override to `False` for local dev over HTTP).
3. Keep `samesite='lax'` — required for the iframe pattern.
4. **Do not touch CORS configuration** — Lock 2 is deferred to v0.3.

### Task 2 — Test coverage

1. Add `Routes__Host__Auth` test coverage — set / clear cookie, redirect target, expired-key behaviour. **No mocks.**
2. Add negative-path tests — 401 with no auth, 401 with wrong key, 401 retains the (still-reflective) CORS headers.
3. Add an explicit assertion that the `Set-Cookie` header includes `HttpOnly` and (under HTTPS) `Secure`.

### Task 3 — Documentation

Update `architecture/03__sidecar-contract.md`:
- §2.2 Cookie attributes — flip `HttpOnly` to `true`.
- §3 CORS contract — leave the "Risk flagged" subsection in place; add a note that Lock 2 is deferred to v0.3 with a link to architect-locks.md.

## FE smoke gate (after merge to dev)

The frontend team will smoke-test the iframe pattern post-merge — see `v0.2.1__finish/frontend/SESSION_KICKOFF.md` "Smoke 2". The cookie's `HttpOnly=true` should NOT break the iframe pattern (the browser still sends the cookie automatically on the WebSocket upgrade). If the FE smoke surfaces a regression, "stop and surface" — do not paper over it.

## Acceptance criteria

- Cookie is `HttpOnly=True; Secure=True (when env says); SameSite=lax`.
- Iframe terminal still works in a browser smoke test (FE smoke debrief is the artefact).
- `Routes__Host__Auth` test file exists with set/clear/expired coverage.
- Negative-path test file exists.
- `unittest.mock.patch` count in `sg_compute__tests/host_plane/` is zero.
- CORS config is **unchanged** (Lock 2 deferred — verify no incidental edits to `Fast_API__Host__Control` CORS lines).
- Reality doc + architecture doc updated.
- PR description includes the `Set-Cookie` header from a live `curl -i` against `/host/auth/redeem` proving `HttpOnly`.

## Open questions

None — both locks ratified (Lock 1 approved; Lock 2 deferred to v0.3).

## Blocks / Blocked by

- **Blocks:** none.
- **Blocked by:** none — locks ratified.

## Notes

The iframe pattern relies on cookie auth. Flipping `HttpOnly=True` is **defence in depth** — it doesn't break the iframe (the browser still sends the cookie automatically) but it prevents JS exfiltration if the iframe page ever has an XSS bug.

The CORS allowlist work that originally lived in this brief is parked until v0.3 picks it up — don't sneak it in here.
