---
title: Aligning SG/Compute Lambdas with the osbot FastAPI + combined-deps pattern
date: 2026-05-20
authors: [vault-publish team]
status: draft / mapping doc — for review before implementation
target_version: v0.1.17
trigger: pydantic-core ImportError on the admin Lambda (native-wheel platform mismatch)
source_briefs:
  - team/humans/dinis_cruz/briefs/05/20/fast-api/v0.27.38__architect-to-dev__fastapi-lambda-index.md
  - team/humans/dinis_cruz/briefs/05/20/fast-api/v0.27.38__architect-to-dev__lambda-dependency-packaging.md
  - team/humans/dinis_cruz/briefs/05/20/fast-api/v0.27.38__architect-to-dev__serverless-fastapi-patterns.md
  - team/humans/dinis_cruz/briefs/05/20/fast-api/v0.27.38__architect-to-dev__new-lambda-quickstart.md
---

# Why this doc

The v0.1.16 admin Lambda split shipped a FastAPI app (`Fast_API__Admin`) deployed via
our bespoke `Lambda__Deployer` + `Setup__Admin__Lambda` flow. It fails at cold start
with a pydantic-core `ImportError` — the classic native-wheel platform mismatch. Rather
than band-aid the dependency list again, this is the moment to align our Lambda
deployment + FastAPI patterns with the **osbot-fast-api / osbot-fast-api-serverless**
conventions documented in the SG-Send architect briefs (and, crucially, **already used
elsewhere in this very repo** — see `sg_compute/control_plane/Fast_API__Compute.py`).

This doc maps the SG-Send brief patterns onto our SG/Compute vault-publish Lambdas and
proposes a phased adoption that (a) fixes the pydantic issue properly and (b) gives us a
reusable pattern for every future Lambda in this project.

---

# Root cause of the pydantic-core failure

Our `Lambda__Deployer._build_zip` packages dependencies by **copying the locally-installed
package directory** into the deploy ZIP:

```python
module = importlib.import_module(module_name)       # imports from the BUILD machine's venv
src    = module.__path__[0]                          # e.g. /usr/local/lib/python3.11/.../pydantic_core
shutil.copytree(src, dest, ...)                      # copies whatever arch/abi the build host has
```

For pure-Python packages (`osbot_utils`, `fastapi` itself) this is fine. For packages
with **compiled native extensions** — `pydantic_core` ships a `.so` built for a specific
(python-version, platform, abi) triple — the copied `.so` matches the **build machine**,
not the **Lambda runtime**. When the runtimes differ (our build host is python3.11 / the
local arch; Lambda is python3.12 / x86_64 or arm64), the `.so` fails to load:
`ImportError: ... cannot import ... pydantic_core._pydantic_core`.

The SG-Send pattern solves this exactly: it `pip install`s with explicit
`--platform manylinux2014_x86_64 --python-version <X> --implementation cp --abi cp<XX>
--only-binary=:all:`, which downloads the **manylinux wheel that matches the Lambda
runtime** rather than copying the build host's compiled artifacts. (Brief 1 §3, §8.)

---

# The SG-Send pattern (3 pillars)

From the four architect briefs:

### Pillar 1 — Combined-zip dependency packaging

- **Build time:** one `pip install` of the full pinned list targeting the Lambda's
  exact (python, platform, abi); strip clutter; zip once; upload to
  `s3://{account}--osbot-lambdas--{region}/lambdas-dependencies-combined/{base}-{sha256[:12]}.zip`.
  Content-addressable → idempotent (same deps ⇒ same key ⇒ skip).
- **Cold start:** single STS + single S3 GET + single unzip → `sys.path.insert(0, …)`;
  warm containers reuse the `/tmp` extraction (no S3 call). Gated on `AWS_REGION` so
  local tests import from the venv as normal.
- Two classes: `Lambda__Dependencies__Builder` + `Lambda__Dependencies__Loader`. Not yet
  in any published osbot package — full source in Appendix A of brief 1; destined to be
  upstreamed into `osbot_aws`.

### Pillar 2 — `Serverless__Fast_API` app base

- Subclass `Serverless__Fast_API` (from `osbot-fast-api-serverless`). Gives Mangum
  adapter, lifecycle (`setup()` → `app()` → `handler()`), CORS, OpenAPI/docs, MCP mount,
  Type_Safe config, `add_routes(RouteClass, **service_kwargs)` service injection.
- **No hand-rolled ASGI adapter** — Mangum is built in.

### Pillar 3 — `Fast_API__Routes` route classes

- Subclass `Fast_API__Routes`. `tag` → URL prefix; method name → path (convention:
  `__` ⇒ new segment, trailing param-name segment ⇒ `{param}`, `_` ⇒ `-`), OR
  `@route_path('/...')` for catch-alls / arbitrary URLs. Verb chosen by which
  `add_route_*` you call. Type_Safe schemas for bodies. Per-route auth via a
  `check_access_token(...)` call at the top of protected methods.

---

# Current state of our two Lambdas

| | `lambdas/admin/` | `lambdas/waker/` |
|---|---|---|
| Web framework | FastAPI, hand-rolled `Fast_API__Admin` (raw `FastAPI()` + sub-route registration) | none — plain `lambda_entry.handler` event router |
| Lambda adapter | our own `Lambda_To_ASGI` (≈100 LOC) | none (plain dict in/out) |
| Deps packaging | `Lambda__Deployer` copies local venv packages ← **the bug** | only `osbot_utils`/`osbot_aws` (pure Python, no native wheels → no bug) |
| Routes | methods on `Fast_API__Admin` (`/login`, `/api/v1/status`, …) | hardcoded `if path == …` short-circuits |
| Auth | `Admin__Auth` API-key cookie/header | none (waker is public) |
| Deploy CLI | `sg vp setup admin-lambda *` | `sg vp setup lambda *` |

The control plane (`sg_compute/control_plane/Fast_API__Compute.py`) **already** uses
`Serverless__Fast_API` + `Fast_API__Routes` + `Middleware__Check_API_Key`. Our admin
Lambda diverged from that established in-repo pattern by hand-rolling — this doc realigns.

---

# Gap analysis: admin Lambda vs the pattern

| Concern | Admin Lambda today | Pattern prescribes | Action |
|---------|--------------------|--------------------|--------|
| App base | raw `FastAPI()` in `Fast_API__Admin` | subclass `Serverless__Fast_API` | refactor |
| Adapter | custom `Lambda_To_ASGI` | Mangum (built into `Serverless__Fast_API.handler()`) | delete `Lambda_To_ASGI`, use base |
| Routes | inline methods + manual `@sub.get` | `Fast_API__Routes` subclass with `add_route_*` | refactor into `Routes__Admin` |
| Auth | `Admin__Auth.check()` in a middleware | per-route `check_access_token()` OR `Middleware__Check_API_Key` (control-plane style) | adopt one — lean to control-plane's middleware since admin is uniformly gated except `/api/v1/status` |
| Deps | `Lambda__Deployer` copies venv (breaks native wheels) | combined-zip Builder with platform-targeted pip | **the fix** — adopt Builder/Loader |
| Schemas | already Type_Safe (`Schema__*`) | Type_Safe | ✓ no change |

The waker has **no FastAPI** and works fine as a plain handler; it doesn't hit the
native-wheel bug. Decision needed (see Phase C) on whether to converge it too.

---

# Proposed phased adoption

## Phase A — combined-zip dependency packaging (fixes pydantic NOW)

Smallest change that resolves the cold-start failure.

1. Create `sg_compute/_for_osbot_aws/Lambda__Dependencies__{Builder,Loader}.py` from
   Appendix A of brief 1 (verbatim — they're stdlib + boto3 only). Single shared copy
   for the whole SG/Compute project, not per-Lambda.
2. Set the Builder's runtime triple to **match our Lambda runtime exactly**. We deploy
   `python3.12`; need to confirm arch (the CLAUDE.md says arm64 but `Setup__Admin__Lambda`
   uses `PYTHON_3_12` with default x86_64). The Builder constants
   (`LAMBDA_PYTHON='3.12'`, `LAMBDA_PLATFORM`, `LAMBDA_ABI='cp312'`) MUST match — this is
   the single most important correctness detail (brief 1 §8, brief 4 troubleshooting table).
3. Define `ADMIN__LAMBDA_DEPENDENCIES` pinned list (fastapi, starlette, pydantic,
   pydantic-core, etc. — every version pinned; the hash names the S3 object).
4. In `lambdas/admin/lambda_entry.py`, load deps before importing the app, gated on
   `AWS_REGION` (brief 1 §5 shape).
5. In `Setup__Admin__Lambda.create()`, call the Builder's `upload()` before deploying;
   ship a **thin** code zip (no bundled deps). Remove the `extra_modules` FastAPI list
   (it becomes the combined zip's job).
6. Pre-req: ensure the `{account}--osbot-lambdas--{region}` S3 bucket exists (the SG-Send
   convention). Add a `Setup__Admin__Deps__Bucket` check or fold into existing setup.

**Outcome:** admin Lambda cold-starts cleanly; deps are platform-correct manylinux
wheels; no more native-wheel ImportError. The bug class is gone for every future Lambda
that uses the Builder.

## Phase B — admin Lambda → `Serverless__Fast_API` + `Fast_API__Routes`

Align with the in-repo control-plane pattern; delete the hand-rolled adapter.

1. `Fast_API__Admin(Serverless__Fast_API)` — move route registration into
   `setup_routes()`; build `Admin__Auth`-equivalent gating either as a
   `Middleware__Check_API_Key` subclass (control-plane style, since admin is uniformly
   gated) OR keep per-route checks. The `/api/v1/status` public endpoint becomes an
   auth-free path (like the control plane's `_AUTH_FREE_PATHS`).
2. `Routes__Admin(Fast_API__Routes)` (and/or `Routes__Admin__Api`) — convert the inline
   methods (`/`, `/login`, `/logout`, `/slug/<slug>/`, `/api/v1/*`) to route-class
   methods. `/api/v1/status` and `/slug/{slug}/` need either the naming convention or
   `@route_path` (the `{slug}` path param maps cleanly via convention; the HTML pages at
   `/` and `/login` are literal).
3. Handler uses `with Fast_API__Admin() as _: _.setup(); handler = _.handler()` — Mangum
   replaces `Lambda_To_ASGI`.
4. **Delete** `lambdas/admin/Lambda_To_ASGI.py` (the hand-rolled adapter) and the
   `_get_dispatcher()` caching in `lambda_entry.py` — `Serverless__Fast_API` owns the
   warm-container app caching.
5. `Admin__Pages` (HTML rendering) is unaffected — it's just string templates the route
   methods return.

**Outcome:** admin Lambda matches `Fast_API__Compute`; one less bespoke adapter to
maintain; Mangum is battle-tested vs our ~100-LOC `Lambda_To_ASGI`.

## Phase C — waker decision (keep plain-handler OR converge)

The waker is a hot-path router (slug resolve → wake → proxy/warming-page). It has **no
FastAPI dependency** today, which is a feature: tiny ZIP, ~50-100ms faster cold start,
no pydantic/starlette in the bundle. Two options:

- **C1 (recommended): keep waker as a plain handler.** It doesn't benefit from FastAPI —
  it's a 6-way path switch + a state machine. Adopt only Phase A's combined-zip Builder
  IF it ever grows native deps (it won't soon). Document it as the "plain-handler Lambda"
  reference in the pattern doc.
- **C2: converge waker onto `Serverless__Fast_API` too** for uniformity. Costs the
  cold-start budget we deliberately reclaimed in v0.1.16 Phase 7. Only worth it if we
  want one single Lambda shape across the project.

Recommendation: **C1**. Two legitimate Lambda shapes — "plain handler" (waker, hot path,
no web framework) and "FastAPI app" (admin, control plane, richer surface). The pattern
doc codifies both.

## Phase D — codify the SG/Compute Lambda pattern

Write `library/guides/v0.1.17__sg_compute_lambda_pattern.md` capturing:
- The combined-zip dependency packaging (mandatory for any Lambda with native deps)
- The two Lambda shapes (plain-handler vs `Serverless__Fast_API`) and when to use each
- The Builder runtime-triple rule (the #1 footgun)
- Integration with our `Setup__*` CLI deploy flow
- A from-scratch checklist (mirroring brief 4)

This becomes the reference for the reaper Lambda, any future cert-management Lambda
(see the cert-strategy brief), metrics Lambdas, etc.

---

# Integration with our existing Setup__* CLI

SG-Send deploys via `Deploy__Serverless__Fast_API`. We deploy via `Setup__Admin__Lambda`
+ `Lambda__Deployer`. We do NOT have to replace our CLI — we keep `sg vp setup
admin-lambda create/update/...` as the operator surface, but change what it does
internally:

- **Before:** `Lambda__Deployer.deploy_from_folder(extra_modules=[fastapi, ...])`
  (copies venv packages → breaks native wheels).
- **After:** (1) `Lambda__Dependencies__Builder('sg-compute-admin', DEPS).upload()`,
  then (2) `Lambda__Deployer.deploy_from_folder(extra_modules=['osbot_utils'])` for the
  thin code zip (or keep deploying the full `vault_publish` tree minus the heavy deps).

`Lambda__Deployer` itself could grow a `combined_dependencies=` option that delegates to
the Builder, so both the bespoke CLI and a future `Deploy__Serverless__Fast_API` path can
share it.

---

# Open questions / decisions needed before implementing

1. **Lambda arch + python**: confirm we deploy `python3.12` on **x86_64** (Setup uses
   `PYTHON_3_12`; arch defaults to x86_64 unless specified). The Builder constants must
   match exactly. CLAUDE.md says "Python 3.12 / x86_64" for the main service but also
   "arm64" in places — need the authoritative answer for the **waker/admin** Lambdas
   specifically. **Blocking** for Phase A.
2. **Builder/Loader location**: `sg_compute/_for_osbot_aws/` (mirrors SG-Send) vs a more
   SG/Compute-native home? They're destined for `osbot_aws` upstream regardless.
3. **The S3 deps bucket**: `{account}--osbot-lambdas--{region}` — does it already exist in
   our account (SG-Send may have created it), or do we provision it? Add a setup check.
4. **Auth model for admin**: per-route `check_access_token` (SG-Send transfers style) vs
   `Middleware__Check_API_Key` subclass (our control-plane style). The control-plane
   precedent in this repo argues for the middleware approach.
5. **Phase C**: confirm C1 (keep waker plain) vs C2 (converge).
6. **Sequencing**: Phase A alone fixes the production bug. B/C/D are quality/consistency.
   Ship A first as a hotfix, then B-D as a follow-up? Or do A+B together since they touch
   the same files?

---

# Recommended next step

Ship **Phase A as a standalone hotfix** (fixes the pydantic cold-start failure with the
combined-zip Builder), gated on resolving open question #1 (the arch/python triple). Then
do **Phase B + D together** as the alignment slice, and decide **Phase C** explicitly.

Phase A is ~1 day; B+D ~1-2 days; C is a 1-line decision.
