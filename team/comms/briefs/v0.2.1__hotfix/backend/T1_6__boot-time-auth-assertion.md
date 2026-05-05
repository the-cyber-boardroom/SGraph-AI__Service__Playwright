# T1.6 — Boot-time auth assertion (fail loud, not open)

🔴 **Tier 1 — security.** Part of the security hotfix bundle (one PR with T1.1-T1.5).

## What's wrong

The `/legacy/` mount preserves auth via `Fast_API__SP__CLI`'s middleware (the BV2.10 fix is correct) — **but only if `FAST_API__AUTH__API_KEY__VALUE` is set in the environment**. If the env var is unset (e.g. a misconfigured Lambda deploy, a forgotten `.env` file in a new env), the middleware accepts every request.

The same risk applies to the sidecar (`Fast_API__Host__Control`) — if booted without an API key env var, it goes wide-open.

## Why it matters

Lambda env vars are easy to forget. A misconfigured deploy ships a fully-open admin API + sidecars that accept any request. **Fail-open is worse than fail-loud.**

## Tasks

1. **Add a startup assertion** in `Fast_API__Compute.__init__` (or `setup_routes`):
   ```python
   import os
   key = os.environ.get('FAST_API__AUTH__API_KEY__VALUE', '')
   assert key, 'Fast_API__Compute refuses to start: FAST_API__AUTH__API_KEY__VALUE env var is unset'
   assert len(key) >= 16, 'Fast_API__Compute refuses to start: API key shorter than 16 characters'
   ```
2. **Add the same assertion** in `Fast_API__Host__Control` — sidecar refuses to boot without a strong key.
3. **Lambda startup behaviour** — the assertion fires during cold start; Lambda surfaces the error in CloudWatch and the function fails to initialise. This is the desired behaviour: a misconfigured deploy never reaches the public internet.
4. **Local-dev convenience** — provide a `.env.example` with a strong default key and a comment: "REPLACE THIS — this default is checked into git, useless in any real deployment".
5. **Test** — set the env var to empty / short, instantiate the class, expect `AssertionError` with the named message.

## Acceptance criteria

- `Fast_API__Compute` raises a clear `AssertionError` if `FAST_API__AUTH__API_KEY__VALUE` is missing or short.
- Same for `Fast_API__Host__Control`.
- Tests cover both the missing case and the too-short case.
- `.env.example` updated with the warning.
- Reality doc notes the boot-time assertion as part of the auth model.

## "Stop and surface" check

If you find a deployment env where the API key isn't set: **STOP**. Don't add a fallback default that lets it boot. Surface to DevOps to set the env var properly.

## Live smoke test

`unset FAST_API__AUTH__API_KEY__VALUE && python -c "from sg_compute.control_plane.Fast_API__Compute import Fast_API__Compute; Fast_API__Compute()"` → expect `AssertionError`.

## Source

Executive review T1.6; backend-late review §"BV2.10 — Top 3 security issue".
