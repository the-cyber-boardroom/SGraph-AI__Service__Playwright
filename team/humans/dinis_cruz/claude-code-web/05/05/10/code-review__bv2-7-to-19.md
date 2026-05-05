# Deep Code Review — BV2.7 → BV2.19 (v0.2.0 → v0.2.4)

Reviewer: Claude Code (Opus 4.7) — 2026-05-05 10:xx UTC
Scope: `dev` @ v0.2.4. Phases BV2.7, BV2.8, BV2.9, BV2.10, BV2.19.
Method: Brief vs commit diff vs current-tree code.

---

## Executive summary

Five phases shipped. The headline catch (BV2.10 auth-bypass) WAS caught and
corrected. But several quieter regressions slipped through, the most
serious being **the CI guard added by BV2.8 is not wired into any CI
workflow AND would currently fail on three files** introduced/edited by
BV2.10 itself. The Type_Safe `: object = None` cleanup is roughly
half-done. The vault endpoint URL diverges from the brief by accident
(double "vault" segment). BV2.19 ships into a packaging surface that
almost certainly does not include the spec UI files in the Lambda zip.

---

## BV2.7 — Migrate Tier-1 `__cli/` sub-packages → `sg_compute/`

**Commits:** `9983f91 phase-BV2.7+BV2.8a: migrate tier-1 __cli/ → sg_compute/ + CI import guard`

**Acceptance criteria check:**

| Criterion | Status | Evidence |
|---|---|---|
| `grep -rln 'from sgraph_ai_service_playwright__cli' sg_compute/ sg_compute_specs/` returns zero hits | PARTIAL at commit-time, FAILS today | At commit `9983f91` the cycle was broken. Today (after BV2.10) `sg_compute/control_plane/Fast_API__Compute.py:63`, `sg_compute/control_plane/legacy_routes/Routes__Ec2__Playwright.py:28-29`, `sg_compute/control_plane/legacy_routes/Routes__Observability.py:20` re-introduced the legacy import. See BV2.10 + BV2.8 below. |
| Tests green | DONE per commit message | 284 sg_compute + 299 spec tests passing per `9983f91`. |
| Reality doc updated | DONE | `team/roles/librarian/reality/sg-compute/index.md` updated. |
| Use `git mv` to preserve history | LOST IN MOST CASES | `git log --follow` on the moved files (e.g. `Schema__Stack__Event.py`) only returns the BV2.7 commit. The brief explicitly required `git mv`; the diff in `9983f91` shows the old paths were *never deleted* (they still live under `__cli/observability/primitives/` etc.) so this was a copy-and-rewrite, not a rename. History on the new files is detached from the legacy originals. |
| Brief naming: `sg_compute/platforms/ec2/aws/` | NOT DONE | Helpers landed at `sg_compute/platforms/ec2/helpers/` instead. The brief named the directory explicitly and rejected the `sg_compute/aws/` alternative — `helpers/` was a third, undocumented choice, decided silently by the implementer. |

**Project-rule violations:**
- Bypassed the brief's "Architect ratified `sg_compute/platforms/ec2/aws/`" call by quietly choosing `helpers/`. No decision record.
- `git mv` rule (preserve history) not honoured for the migration. Reduces forensics for the next refactor.

**Security concerns:** None.

**Bad decisions / shortcuts:**
- The brief said "leave the legacy `__cli/` paths intact for now — BV2.12 converts them to shims." The commit did this, but did not convert the legacy primitives to one-line re-exports either, so we now have **two source-of-truth copies** of `Schema__Stack__Event`, `Safe_Str__AWS__Region`, `Enum__Instance__State`, `Schema__Image__Build__Request`, etc. Any divergence between them will compile but fail at runtime in surprising ways. The brief assumes BV2.12 fixes this, but until then the legacy copies are live and unsynchronised.

**Verdict:** ⚠ Has issues. Migration mechanically completed but the directory choice diverges from the Architect ratification, history was not preserved, and the legacy duplicates were not converted to shims.

---

## BV2.8 — CI guard + fix `: object = None` Type_Safe bypass

**Commits:** `9983f91` (Task 1, CI guard) + `bade2ad fix(BV2.x): replace object=None bypasses ...` (Task 2)

**Acceptance criteria check:**

| Criterion | Status | Evidence |
|---|---|---|
| `tests/ci/test_no_legacy_imports.py` exists and passes | EXISTS, FAILS TODAY | `tests/ci/test_no_legacy_imports.py:12` — passes at commit time of `9983f91` but FAILS as of HEAD. Running the test logic locally returns 3 offenders: `sg_compute/control_plane/Fast_API__Compute.py`, `sg_compute/control_plane/legacy_routes/Routes__Ec2__Playwright.py`, `sg_compute/control_plane/legacy_routes/Routes__Observability.py`. The legacy_routes files are re-export shims and their inbound imports are unavoidable, but the test is binary. |
| **Test wired into CI** | NOT WIRED | `.github/workflows/ci-pipeline.yml:Job 1` runs `python -m pytest tests/unit/ -v --timeout=30 --ignore=tests/unit/agent_mitmproxy`. The `tests/ci/` directory (and `sg_compute__tests/`) is NEVER swept in any GH workflow. The "guard" is dead code unless someone runs it manually. |
| `grep -rn ': object = None' sg_compute_specs/` returns zero hits | FAILS — 39 hits | All 10 `*__AWS__Client.py` files still carry 5x `: object = None` each (sg, ami, instance, tags, launch). Plus `Local__Docker__SGraph_AI__Service__Playwright.py`, `Docker__SGraph_AI__Service__Playwright__Base.py`, `Docker__Agent_Mitmproxy__Base.py`. The `bade2ad` commit message admits this: *"object=None kept for 7 circular AWS__Client files (Type_Safe cannot resolve string ForwardRefs)"*. Acceptance criterion missed silently. |
| All spec tests still pass | Likely DONE | Commit message claims 313 passing. |

**Project-rule violations:**
- Type_Safe attribute-typing rule (`Zero raw primitives`, `no plain object`) is violated in 39 places. Same anti-pattern the phase was specifically meant to remove.
- One-class-per-file: not relevant.

**Security concerns:**
- 🟡 LOW: `: object = None` on AWS clients defeats Type_Safe runtime validation. If a caller injects the wrong helper (e.g. wrong-spec helper into another spec's client) Type_Safe won't catch it, so the wrong AWS API may be called against the wrong resource. Not exploitable, but a class of spec-cross-contamination bug we can't even detect.

**Bad decisions / shortcuts:**
- Discovered Type_Safe can't resolve string forward-refs → did the easy half (10 non-circular files) and silently kept the bypass on the harder half. No follow-up brief, no decision record. The phase is marked done in the debrief and the acceptance criterion is silently relaxed.
- CI guard test was authored but **never wired into any CI workflow**. The brief says "this test runs in CI and fails if any new code imports from the legacy tree" — that is not true today. Add `tests/ci/` to Job 1's pytest command, or fail the build differently.

**Verdict:** 🔴 Blocking issues. Both acceptance criteria are silently failing in the live tree. The CI guard isn't even invoked.

---

## BV2.9 — Migrate `__cli/vault/` → `sg_compute/vault/`

**Commits:** `464f3a8 phase-BV2.9: migrate vault layer to sg_compute/vault/; rename plugin→spec`

**Acceptance criteria check:**

| Criterion | Status | Evidence |
|---|---|---|
| `sg_compute/vault/` exists; legacy `__cli/vault/` is a shim | DONE | `sgraph_ai_service_playwright__cli/vault/service/Vault__Plugin__Writer.py` is a 5-line shim re-exporting `Vault__Spec__Writer as Vault__Plugin__Writer`. Same for `Routes__Vault__Plugin`. |
| `Vault__Plugin__Writer` → `Vault__Spec__Writer`, `plugin_id` → `spec_id` | DONE | `Schema__Vault__Write__Receipt` uses `spec_id`, primitive renamed `Safe_Str__Plugin__Type_Id` → `Safe_Str__Spec__Type_Id`. Old primitive at `sgraph_ai_service_playwright__cli/vault/primitives/Safe_Str__Plugin__Type_Id.py` is also a shim. |
| Endpoint paths follow `/api/vault/spec/{spec_id}/...` | NOT QUITE | `Routes__Vault__Spec.tag = 'vault'`, `__route_path__ = '/spec/{spec_id}/...'`. Mounted on `Fast_API__Compute` with `prefix='/api/vault'`. Net effective URL is `/api/vault/vault/spec/{spec_id}/...` (double `vault`) since osbot-fast-api appends the route's `tag` after the prefix. Brief explicitly said `/api/vault/spec/{spec_id}/...`. The route tests bypass the prefix and directly assert `/vault/spec/...`, which masks the bug. |
| All vault tests pass; no mocks | DONE | `sg_compute__tests/vault/` uses real `Spec__Registry`, real `Vault__Spec__Writer`. The legacy `tests/unit/sgraph_ai_service_playwright__cli/vault/` files were rewritten to import the new symbols too. No `unittest.mock.patch` in any vault test. |
| Rewrite Ollama/Open_Design tests without `unittest.mock.patch` | DONE | Two new test files added. |
| Reality doc updated | DONE | `team/roles/librarian/reality/sg-compute/index.md` has the vault entry. |

**Project-rule violations:**
- `Vault__Spec__Writer.write_handles_by_spec : dict` is a raw `dict` annotation. Project rule: zero raw primitives (`Schema__Vault__Spec__Handles__Map` or a `Dict__Spec_Id__Handles` collection class would be the correct shape). Type_Safe accepts `dict` but the rule disallows it.
- `Vault__Spec__Writer` returns `tuple` from every public method. Untyped tuple. The route handler unpacks `(receipt, err)` positionally and the type system can't enforce it.
- `Routes__Vault__Spec.list_spec` returns a raw dict `{'spec_id': ..., 'receipts': [...]}` instead of a `Schema__*` envelope (project rule §6: "every route returns `.json()` on a Type_Safe schema — no raw dicts"). `delete` returns `{}` likewise.
- The route handler imports `HTTPException` directly and raises it from a private `_raise()` helper that begins with an underscore — project rule §9: "no underscore prefix for private methods". Same for the `_STATUS_FOR_ERROR` module constant (low-grade nit; constants are fine).

**Security concerns:**
- 🟡 MEDIUM: `Vault__Spec__Writer.write()` is a stub — it produces a receipt but performs no I/O ("persistence stubbed"). The route returns a 200 with a SHA-256 receipt that LOOKS like a successful write. **Any client who PUTs a secret to `/api/vault/...` will receive a `200` and a receipt and assume the secret was stored.** It wasn't. If the dashboard's vault-picker UI ships against this, users will believe their MITM script / credentials are saved when they aren't.
- 🟡 LOW: `vault_attached: bool = False` defaults to false — protects against the above silently-discarded write IF the boot wiring keeps it false. But `Fast_API__Compute._mount_control_routes` instantiates `Vault__Spec__Writer(spec_registry=self.registry)` without setting `vault_attached`, so it defaults false → any write attempt returns 409. Net: routes are wired but unusable. Brief task 8 ("Update reality doc — vault is its own domain") is done; reality should also flag *vault is wired but inert*.
- 🟢 INFO: 10 MB hard cap is sensible. SHA-256 is computed before validation — wastes CPU on rejected bodies. Fine for now.

**Bad decisions / shortcuts:**
- Stubbed-but-200 is dangerous (see above). A stub should return `501 Not Implemented` + `{detail: 'vault persistence not yet wired'}`, not a fake 200 receipt.
- The endpoint-path drift (`/api/vault/vault/spec/...`) was not caught by tests because the tests mount without a prefix. Add an integration test against the mounted Fast_API__Compute.
- Tests were duplicated rather than retargeted: both `sg_compute__tests/vault/` and `tests/unit/sgraph_ai_service_playwright__cli/vault/` exist and assert the same thing. Twice the surface, twice the maintenance.

**Verdict:** ⚠ Has issues. Mechanically complete, but the URL is wrong, the writer silently no-ops, and several project rules are violated.

---

## BV2.10 — Fold `Fast_API__SP__CLI` into `control_plane/` with `/legacy/` mount

**Commits:**
- `453de85 phase-BV2.10: fold Fast_API__SP__CLI legacy routes into Fast_API__Compute at /legacy/` (BROKEN first attempt)
- `54f349f fix(BV2.10): use Fast_API__SP__CLI sub-app for /legacy mount (not direct route wiring)` (CORRECTED)

**Acceptance criteria check (against final state at HEAD):**

| Criterion | Status | Evidence |
|---|---|---|
| `Fast_API__Compute` serves both `/api/*` and `/legacy/*` | DONE | `Fast_API__Compute._mount_legacy_routes` mounts `Fast_API__SP__CLI().setup().app()` at `/legacy`. Test `test_api_health_still_reachable` + `test_legacy_catalog_types_is_auth_gated` confirm both. |
| Every legacy URL response carries `X-Deprecated` | DONE | ASGI wrapper `_with_deprecated_headers` prepends `(b'x-deprecated', b'true')` and migration-path on every `http.response.start`. Tests `test_legacy_catalog_has_deprecated_header`, `test_legacy_docker_has_deprecated_header`, `test_legacy_ec2_has_deprecated_header` confirm. |
| `pyproject.toml` script entry-points run via `Fast_API__Compute` | DONE for `scripts/run_sp_cli.py`, NOT EVALUATED for the package's `[tool.poetry.scripts]` entries (`sg-play`, etc.) | `scripts/run_sp_cli.py:36` calls `Fast_API__Compute().setup().app()`. The other entry-points still target their original CLIs. |
| Tests pass | DONE | 12 new tests in `test_Legacy__Routes__Mount.py`, all green per commit msg. |
| `Routes__Vault__*` from `__cli/` deletion plan / shims | DONE | Shim files in `__cli/` re-export. |
| `git mv` to preserve history | DONE | `git log --follow sg_compute/control_plane/legacy_routes/Routes__Ec2__Playwright.py` traces back through the `__cli/` location — history preserved this time. |

**Project-rule violations:**
- `_mount_legacy_routes`, `_mount_spec_ui_static_files`, `_register_exception_handlers`, `_add_deprecated_header_middleware`, `_make_service`, `_live_platform`, `_live_pod_manager` all use the underscore-prefix-private convention forbidden by rule §9.
- Local imports inside `_mount_legacy_routes` (`from sgraph_ai_service_playwright__cli...`) bypass the BV2.7 cycle-break — this is the exact pattern the CI guard was meant to detect, and it slips because (a) it's inside a method body so the guard's regex catches it (it does match `from sgraph_ai_service_playwright`) and (b) the guard isn't wired into CI.
- The ASGI wrapper `_with_deprecated_headers` is a free function inside a method (not a Type_Safe class, not in its own file). Rule §21 (one class per file) doesn't apply because it's a function, but the team has been strict about wrapping such things.

**Security concerns:**
- 🟢 RESOLVED: The fix preserves API-key auth on `/legacy/*` because mounting an ASGI sub-app at a path keeps that sub-app's middleware chain in the request flow. Test `test_legacy_catalog_types_is_auth_gated` (asserts `401`) is the canonical proof.
- 🟡 LOW: The `_with_deprecated_headers` wrapper appends `x-deprecated: true` even on 401 / 5xx responses — fine, but the header is also added on the 401 from the auth middleware, which is helpful for clients but reveals that `/legacy` routes exist (no info-leak material).
- 🟡 LOW: `Fast_API__SP__CLI` is set up at every `Fast_API__Compute().setup()` call. This means every test that builds a `Fast_API__Compute` does the full SP-CLI plugin discovery (filesystem walk under `PLUGIN_FOLDERS`). Test isolation gets weaker.
- 🟡 MEDIUM: `_mount_legacy_routes` sets up the legacy app **after** `_mount_spec_routes` (and after the spec UI mount). If the SP-CLI plugin registry registers a handler that touches AWS at import-time, every test will hit AWS. The brief said the SP CLI's setup should NOT touch AWS — verify this hasn't drifted.
- 🔴 HIGH: The legacy `Fast_API__SP__CLI` is mounted **unconditionally** in production. If the auth-key env var isn't set in some deploy environment, the legacy surface (which includes EC2 mutations, /catalog, plugin routes) becomes wide-open. The dev fix preserved auth WHEN configured — confirm `FAST_API__AUTH__API_KEY__VALUE` is required for boot, not optional.

**Bad decisions / shortcuts:**
- The first attempt (`453de85`) wired the legacy routes directly into `Fast_API__Compute`, importing route classes and constructing `Plugin__Registry`, `Stack__Catalog__Service`, `Ec2__Service`, `Observability__Service` directly. Reasoning recorded in the dev's log was *"osbot_fast_api_serverless isn't installed"*. **This was wrong on two counts:** (1) it's a `[tool.poetry.dependencies]` entry — it's installed; (2) even if it weren't, the right answer is to fix the dep, not to circumvent the security boundary. The fix in `54f349f` mounts the full SP-CLI sub-app — preserving the API-key middleware AND the type-safe exception handlers AND `Plugin__Registry` discovery in one stroke.
- Legacy imports re-introduced into `sg_compute/`. CI guard fires (locally) but isn't run.
- The `_mount_legacy_routes` function instantiates and tears down a full `Plugin__Registry` per-call in production AND in tests. Slow boot.

**Verdict:** ⚠ Has issues. Auth correctly preserved on the second try, but the cycle-break is broken in CI guard terms and the legacy surface is mounted unconditionally.

---

## BV2.10 first-attempt vs fix — postmortem

### What the first attempt did

`453de85` registered `Routes__Stack__Catalog`, `Routes__Ec2__Playwright`, `Routes__Observability` and every plugin route class **directly on `Fast_API__Compute`** at `/legacy/<tag>/...` via `self.add_routes(...)`.

`Fast_API__Compute` extends `osbot_fast_api.api.Fast_API`, **not** `Serverless__Fast_API`. The auth gate (`Middleware__Check_API_Key`, subclassed as `_Middleware__UI_Bypass`) lives on `Fast_API__SP__CLI` (a `Serverless__Fast_API` subclass). By wiring the routes onto a different parent, the dev ALSO had to copy the `_legacy_deprecation` middleware in by hand AND would have had to copy the API-key middleware in by hand — they did the first, forgot the second.

Net effect of `453de85` had it shipped: every legacy URL would have been **publicly reachable, no API key required**, including:
- `DELETE /legacy/ec2/playwright/delete-all` (terminate every EC2 instance in the account)
- `POST /legacy/ec2/playwright/create` (spin up arbitrary instances on the operator's bill)
- `POST /legacy/{plugin}/...` for every plugin (docker, elastic, neko, etc.)
- `GET /legacy/observability/*` (operational telemetry leakage)

This is exactly the user's hot-button: "the dev was about to bypass `Fast_API__SP__CLI` ... because they thought `osbot_fast_api_serverless` wasn't installed." Confirmed.

### What the fix does

`54f349f` replaces the body of `_mount_legacy_routes` with:

```python
legacy_app = Fast_API__SP__CLI().setup().app()
async def _with_deprecated_headers(scope, receive, send): ...
self.app().mount('/legacy', _with_deprecated_headers)
```

This mounts the **whole `Fast_API__SP__CLI` ASGI app** (with its API-key middleware in place) at `/legacy`. Starlette's `Mount` runs the sub-app's middleware chain when routing to it, so the API-key gate fires before any handler. The deprecation headers are added by an ASGI wrapper that intercepts `http.response.start` and appends two header tuples. Tests now assert `401` (auth fires) on every legacy path including `/legacy/nonexistent/path`.

### Lessons

1. **"Library not installed" should be questioned before circumventing a boundary.** It was a project dependency.
2. **Sub-app mounting ≠ route wiring.** Sub-app inherits its own middleware; route wiring uses the parent's.
3. **The auth-bypass was caught only because the user reviewed.** No automated check would have caught it. Recommend: add a smoke test that asserts every `/legacy/*` path returns 401 without the API key.
4. **The `Fast_API__Compute` class itself is NOT a `Serverless__Fast_API`** — it has no auth middleware of its own. Its modern `/api/*` routes are also unauthenticated by default. This is a separate, latent risk: see "Top issues" below.

### Are there similar risks elsewhere?

Yes:
- `Fast_API__Compute` itself has no auth on `/api/*`. Modern routes (`/api/specs`, `/api/nodes`, `/api/stacks`, `/api/vault`) are wide-open. The vault writer doesn't write yet (so the leak is bounded), but `Routes__Compute__Nodes` POST will trigger AWS instance creation if `vault_attached` is bypassed in another phase.
- `Fast_API__Compute` doesn't extend `Serverless__Fast_API`, so the same pattern (mount as sub-app) needs to be applied to it before it ships to production. This is implicit in BV2.11 (Lambda cutover) but not explicit.

---

## BV2.19 — `StaticFiles` mount for per-spec UI assets

**Commits:**
- `d3abb01 brief(BV2.19): StaticFiles mount`
- `9802b58 brief(BV2.19): remove Cache-Control middleware — CF handles caching`
- `603eda3 phase-BV2.19: StaticFiles mount for per-spec UI assets in Fast_API__Compute`

**Acceptance criteria check:**

| Criterion | Status | Evidence |
|---|---|---|
| `GET /api/specs/docker/ui/...` returns `200` with correct `Content-Type` once `docker` has a `ui/` folder | DONE in tests | `test_mount_activated_when_ui_folder_exists`, `test_mount_content_type_javascript`. |
| `GET /api/specs/ollama/ui/anything` returns `404` (no `ui/` folder) | DONE | `test_mount_only_for_spec_with_ui_folder`. |
| No `Cache-Control` header set by application | DONE | `test_no_cache_control_header_set` (text truncated; assertion is on lack of header). |
| `sg_compute_specs = ["*/ui/**/*"]` in `pyproject.toml` package-data | NOT DONE — wrong file, wrong key | The change landed in the **outer** `pyproject.toml` as `include = [..., "sg_compute_specs/*/ui/**/*"]` under `[tool.poetry]`. But the outer pyproject's `packages = [...]` list does NOT include `sg_compute_specs` (only `sgraph_ai_service_playwright`, `sgraph_ai_service_playwright__cli`, `scripts`). Poetry's `include` field only affects *included* packages, so this glob is a no-op for the poetry build. The actual `sg_compute_specs` distribution is built from `sg_compute_specs/pyproject.toml` (setuptools), and that file's `[tool.setuptools.package-data]` is `sg_compute_specs = ["*/version", "playwright/core/version"]` — **does NOT include `*/ui/**/*`**. Net result: when the spec wheel is built, `ui/` files will NOT be packaged. Lambda will not have them. The mount will silently no-op in production. |
| `tests/ci/test_no_legacy_imports.py` still passes | FAILS (see BV2.10) | Test was passing at BV2.19 commit time; later BV2.10 rebroke it. |

**Project-rule violations:**
- `Spec__UI__Resolver.ui_root_override : str = ''` is a raw string — a dedicated `Safe_Str__Path` would be the project-correct shape (rule §2 zero raw primitives).
- `_mount_spec_ui_static_files` underscore-prefix violates rule §9.
- The mount call uses `StaticFiles(directory=str(ui_path))` — `directory` is also a raw string. (FastAPI/Starlette API; can't be helped.)

**Security concerns:**
- 🟡 LOW: `StaticFiles` follows symlinks by default. If a spec's `ui/` folder contains a symlink to `/etc/passwd` (or to vault files), it will be served. Lock down with `StaticFiles(directory=..., follow_symlinks=False)` (Starlette ≥ 0.31).
- 🟡 LOW: Mount happens **before** any auth — by design, but means UI assets are public. That's correct for UI bundles, but the resolver discovers the directory by `importlib.import_module(f'sg_compute_specs.{spec_id}')`. If `spec_id` were ever influenced by user input (it isn't here — comes from `Spec__Registry`), this would be an arbitrary-import vector.
- 🟡 LOW: No `Cache-Control` is correct for the CF-fronted production path. In dev (uvicorn), the browser will cache aggressively by default. Operators iterating on UI in dev will hit stale-asset confusion. The brief justifies "CF handles caching" — fair, but the dev story needs a `--no-cache` story or a query-string buster.

**Bad decisions / shortcuts:**
- The packaging change (criterion 4) was placed in the wrong file under the wrong build system — looks done in the diff, isn't done at runtime. Verify with `python -m build sg_compute_specs/ --wheel --outdir /tmp/d && unzip -l /tmp/d/*.whl | grep ui/`. I expect zero hits.
- `Spec__UI__Resolver` has `ui_root_override` for tests but not a `Path` type — `: str = ''` then `Path(self.ui_root_override)`. Mixing `str` and `Path` over the same attribute.

**Verdict:** ⚠ Has issues. Code works in tests; packaging broken for production.

---

## Top 5 issues across all 5 phases (severity-ordered)

### 1. 🔴 BV2.19 — Spec UI files will not ship to Lambda (packaging broken)

The brief's package-data line was put in the OUTER pyproject (poetry-managed) under `include`, but the outer build doesn't package `sg_compute_specs`. The INNER `sg_compute_specs/pyproject.toml` (setuptools) does NOT include `*/ui/**/*`. When FV2.6's spec UIs are built into a wheel for Lambda, the `ui/` folders are excluded. The static-file mount will silently no-op in production. Test today by building `sg_compute_specs` wheel and listing contents.

**Fix:** Add `sg_compute_specs = ["*/version", "playwright/core/version", "*/ui/**/*"]` to `sg_compute_specs/pyproject.toml:[tool.setuptools.package-data]`.

### 2. 🔴 BV2.8 — CI guard test is not wired into CI; would FAIL today

`tests/ci/test_no_legacy_imports.py` is not run by any GH workflow. Job 1 in `ci-pipeline.yml` runs `pytest tests/unit/` only. Even if it were, it would fail today because BV2.10 introduced 3 legacy imports under `sg_compute/control_plane/`. The "guard against regression" phase shipped a guard that doesn't guard.

**Fix:** Add `tests/ci/` (and probably `sg_compute__tests/`) to the unit-test pytest invocation. Decide whether the legacy imports inside `_mount_legacy_routes` and `legacy_routes/Routes__*` are an exception (probably yes — they're the bridge) and whitelist them in the test.

### 3. 🔴 BV2.10 — Legacy surface mounted unconditionally; if API-key env var is missing in any deploy env, EC2/observability/plugin routes are wide-open

`Fast_API__Compute._mount_legacy_routes` always mounts `Fast_API__SP__CLI`. The auth gate (`Middleware__Check_API_Key`) is configured by env var — if the var is missing, the middleware no-ops (depending on the `osbot_fast_api` default). Need to assert at boot that the API key is set, OR make legacy mount opt-in via env flag, OR refuse boot in production without the key.

**Fix:** In `Fast_API__Compute.setup()` (or in `_mount_legacy_routes`), `assert os.environ.get('FAST_API__AUTH__API_KEY__VALUE'), 'legacy routes require API key'`. Or gate `_mount_legacy_routes` behind an `enable_legacy: bool = True` Type_Safe attribute that ops can flip off.

### 4. 🟡 BV2.9 — Vault writer is a no-op stub that returns 200 + receipt

Writers return a SHA-256 receipt without writing anything. Any client believing the receipt is being lied to. Combine with future spec UIs that prompt users for credentials → users will think their secrets are persisted. Recommend: return `501 Not Implemented` until persistence is wired, OR set `vault_attached` per environment and refuse writes when false (currently does — but the mount path always sets it false → all writes return 409, which contradicts the 200-stub-receipt path. The 200 path is reachable by setting `vault_attached=True` in tests; once anyone flips it for "smoke testing", the silent-no-op fires.)

### 5. 🟡 BV2.8 — Half the `: object = None` bypasses remain (39 hits in `*__AWS__Client.py` files); acceptance criterion silently relaxed

The brief's criterion was *zero* hits. The implementer hit a Type_Safe forward-ref limitation, fixed the easy half, and quietly left the rest. Type_Safe runtime validation does not protect AWS-client composition. Cross-spec contamination (passing the wrong helper into the wrong client) compiles and runs.

**Fix:** Either resolve the circular-import properly (TYPE_CHECKING + protocol classes), OR file a follow-up brief explicitly carving out the exception, OR migrate to a Type_Safe-native dependency-injection pattern (Type_Safe bases for the helpers + abstract attribute typing).

---

## Honourable mentions (lower severity, worth tracking)

- BV2.7 `git mv` not honoured for any moved file — history detached.
- BV2.7 Architect-ratified directory `sg_compute/platforms/ec2/aws/` was silently changed to `helpers/`. No decision record.
- BV2.9 Endpoint URL is `/api/vault/vault/spec/{spec_id}/...` (double `vault`) due to prefix + tag stacking. Brief said `/api/vault/spec/{spec_id}/...`. Tests don't catch it because they mount without prefix.
- BV2.9 Routes return raw dicts (`{'spec_id': ..., 'receipts': [...]}`, `{}`) — rule §6 says everything goes through `Schema.json()`.
- BV2.9 `Vault__Spec__Writer.write_handles_by_spec : dict` is a raw dict — rule §2.
- BV2.9 Test files duplicated under `tests/unit/sgraph_ai_service_playwright__cli/vault/` AND `sg_compute__tests/vault/`. Pick one.
- BV2.10 `Fast_API__Compute` instantiates `Fast_API__SP__CLI` (full plugin discovery) on every test setup → slow tests, weaker isolation.
- BV2.19 `StaticFiles` does not pass `follow_symlinks=False` — minor symlink-leak surface.
- BV2.19 `ui_root_override` typed as `str`; should be a `Safe_Str__Path` or `Path` attribute.
- All five phases use `_underscore_prefix` private methods — rule §9 is being widely ignored.

---

## What the user should do next

1. **Wire `tests/ci/` and `sg_compute__tests/` into `ci-pipeline.yml` Job 1.** Without this, every "guard" test added is decorative.
2. **Add a smoke test** asserting `GET /legacy/<anything>` returns `401` without API key, and `Fast_API__Compute` boot fails if the API key env var is unset in a `production` mode.
3. **Fix `sg_compute_specs/pyproject.toml` package-data** to include `*/ui/**/*`. Verify by `python -m build sg_compute_specs/ --wheel`, list wheel contents.
4. **Fix the vault endpoint URL** (drop the double `vault`) OR document the `tag` + `prefix` combination explicitly, then add a `Fast_API__Compute`-level integration test that exercises the mounted URL.
5. **Decide on the `: object = None` bypass** — either fix all 39 sites or write a follow-up brief that carves out the exception with rationale.
6. **Audit `Fast_API__Compute` itself for auth.** It does not extend `Serverless__Fast_API`. The modern `/api/*` routes are unauthenticated by default. Same trap as the BV2.10 first attempt, but on the modern surface.

---

## Key file references

- `sg_compute/control_plane/Fast_API__Compute.py` — the core wiring. Lines 51 (legacy mount), 62-76 (legacy mount body, has the legacy import), 78-89 (UI mount), 91-100 (modern routes).
- `sg_compute/vault/service/Vault__Spec__Writer.py` — stubbed writer.
- `sg_compute/vault/api/routes/Routes__Vault__Spec.py` — raw-dict returns.
- `sg_compute/core/spec/Spec__UI__Resolver.py` — UI resolver.
- `tests/ci/test_no_legacy_imports.py` — orphan CI guard.
- `sg_compute_specs/pyproject.toml` — missing `*/ui/**/*` package-data.
- `pyproject.toml` (outer) — wrong place for the UI glob.
- `.github/workflows/ci-pipeline.yml` — Job 1 only sweeps `tests/unit/`.
- `sgraph_ai_service_playwright__cli/fast_api/Fast_API__SP__CLI.py` — the auth-bearing parent the BV2.10 first attempt would have bypassed.
- `sg_compute_specs/docker/service/Docker__AWS__Client.py:32-36` — canonical example of remaining `: object = None`.
- `sg_compute__tests/control_plane/test_Legacy__Routes__Mount.py` — proves auth gate fires post-fix.
