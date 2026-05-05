# T1.1 — `Fast_API__Compute` extends plain `Fast_API`, not `Serverless__Fast_API`

🔴 **Tier 1 — security.** Part of the security hotfix bundle (one PR with T1.2-T1.6).

## What's wrong

`sg_compute/control_plane/Fast_API__Compute.py` extends `osbot_fast_api.Fast_API` (plain) instead of `osbot_fast_api_serverless.Fast_API__Serverless` (which adds the `_Middleware` API-key auth chain by default). **Every `/api/*` route added in BV2.3, BV2.4, BV2.5 is unauthenticated by default.**

This is the same class of mistake the human caught for BV2.10 — but at the architectural base-class level, so it affects the entire `/api/*` surface, not just `/legacy/*`.

## Why it matters

- `POST /api/nodes` — anyone can launch / terminate EC2 instances.
- `GET /api/specs` — anyone can read the catalogue.
- `GET /api/nodes` — anyone can enumerate the running infrastructure inventory.
- `GET /api/health` — fine to be public.

The legacy `/legacy/*` mount is correctly auth'd (BV2.10 fix). The native `/api/*` surface is not.

## Tasks

1. **Find the class definition** — `sg_compute/control_plane/Fast_API__Compute.py:NN` `class Fast_API__Compute(Fast_API):`
2. **Change the base class** to `Serverless__Fast_API` (or whatever the canonical Type_Safe-friendly auth-bearing base is in `osbot_fast_api_serverless`).
3. **Verify auth middleware is wired** — read the parent class's `setup()` / `setup_routes()` to confirm `_Middleware` (or equivalent) is in the chain.
4. **Add a negative-path test** — `tests/.../test_Fast_API__Compute__auth.py` that hits `GET /api/specs` and `POST /api/nodes` with NO `X-API-Key` header and asserts `401`.
5. **Verify auth-free paths** are explicit — `_AUTH_FREE_PATHS` should be a small allowlist (likely just `/api/health`, `/api/health/ready`). Document each carve-out in code.

## Acceptance criteria

- `Fast_API__Compute` extends a `Serverless__Fast_API`-style base.
- Negative-path test: `GET /api/specs` → 401 without key, 200 with valid key.
- Negative-path test: `POST /api/nodes` → 401 without key, 200/202 with valid key (gate also fixed by T1.4).
- `_AUTH_FREE_PATHS` is an explicit allowlist with comments.
- No regression on legacy `/legacy/*` (still 401 without key).

## "Stop and surface" check

If you find yourself thinking _"osbot_fast_api_serverless isn't available in this env, I'll bypass it"_: **STOP**. Use Python 3.12 — the package is there. Surface to Architect if it isn't.

## Live smoke test

Spin up `Fast_API__Compute` locally; `curl http://localhost:8000/api/specs` (no key) → expect 401. `curl -H "X-API-Key: $KEY" http://localhost:8000/api/specs` → expect 200.

## Source

Executive review T1.1; backend-early review §"Top 1 security issue".
