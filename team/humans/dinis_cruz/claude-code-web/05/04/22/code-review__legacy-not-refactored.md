# Code Review — Legacy paths not yet refactored to `sg_compute/` / `sg_compute_specs/`

- **Repo:** `SGraph-AI__Service__Playwright`
- **Branch:** `dev` (up to date with `origin/dev`)
- **Working version:** `v0.1.171` (pyproject) / `v0.1.170` (root `version` file — drift!)
- **Reviewer date (UTC):** 2026-05-04 22:xx
- **Scope:** legacy backend trees only (frontend `__api_site/` excluded by request)

═══════════════════════════════════════════════════════════════════════════════
## 1. Summary
═══════════════════════════════════════════════════════════════════════════════

The repo is in a textbook "copy, don't move" dual-write state. None of the four
legacy backend packages have been retired. Three of them are still 100 %
load-bearing for the running services:

1. `sgraph_ai_service_playwright/` is what the **Playwright Lambda image actually
   bakes and runs** — `lambda_entry.py` and the playwright dockerfile both pin
   the legacy path. The copy under `sg_compute_specs/playwright/core/` is a
   ~88-file mirror with import paths rewritten but is NOT imported by anything.
2. `sgraph_ai_service_playwright__cli/` is the **only** sp-cli implementation
   referenced by `Fast_API__SP__CLI`, the sp-cli Lambda Dockerfile, and 17 of
   the 23 `scripts/*.py` typer entries. Worse, **`sg_compute_specs/` schemas
   reach back into `__cli/` for primitives** (`__cli/aws`, `__cli/catalog`,
   `__cli/core`, `__cli/ec2`, `__cli/image`, `__cli/observability`) — the new
   tree is structurally dependent on the old.
3. `agent_mitmproxy/` is the **only** mitmproxy package CI builds and ECR
   ships; `sg_compute_specs/mitmproxy/` is dead-code mirror.
4. `sgraph_ai_service_playwright__host/` is the **only legacy package that is
   actually orphaned**. Nothing outside the package imports it; the host
   Dockerfile and CI exclusively reference `sg_compute/host_plane/`. This one
   can be deleted today.

Drift severity: For Playwright + mitmproxy + host, the differences are mostly
import-path rewrites + cosmetic header changes — low data-drift risk. For
elastic and ec2/observability primitives the legacy tree has features the new
tree never received (lets/, fast_api/, plugin/, ~200 extra LOC in
`Elastic__AWS__Client.py`).

═══════════════════════════════════════════════════════════════════════════════
## 2. Per-package status table
═══════════════════════════════════════════════════════════════════════════════

| # | Package / Sub-package | Status | Drift vs new path | Recommendation |
|---|---|---|---|---|
| 1 | `sgraph_ai_service_playwright/` (whole) | LOAD-BEARING | 88 files differ — import-path rewrites only | KEEP (canonical) → eventually MIGRATE to `sg_compute_specs/playwright/core/` once consumers cut over |
| 2 | `sg_compute_specs/playwright/core/` (mirror) | DUPLICATE (dead) | — | DELETE or convert to shim re-exporting legacy |
| 3 | `sgraph_ai_service_playwright__cli/aws/` | LOAD-BEARING | Used by `sg_compute_specs/*` AND legacy | NOT-MIGRATED → MIGRATE to `sg_compute/primitives/` or `sg_compute/platforms/aws/` |
| 4 | `sgraph_ai_service_playwright__cli/catalog/` | LOAD-BEARING | Used by `Fast_API__SP__CLI` and `sg_compute_specs/*/manifest.py` | NOT-MIGRATED → MIGRATE to `sg_compute/control_plane/catalog/` |
| 5 | `sgraph_ai_service_playwright__cli/core/` (event_bus, plugin) | LOAD-BEARING | Used by `sg_compute_specs/*` plugin contracts | NOT-MIGRATED → MIGRATE to `sg_compute/control_plane/plugin/` |
| 6 | `sgraph_ai_service_playwright__cli/ec2/` | LOAD-BEARING | NOT migrated — `sg_compute/platforms/ec2/` only has helpers, NOT schemas/services/primitives | NOT-MIGRATED → MIGRATE schemas + services to `sg_compute/platforms/ec2/` |
| 7 | `sgraph_ai_service_playwright__cli/image/` | LOAD-BEARING | Used by playwright Build__Docker and sg_compute_specs Docker__SP__CLI | NOT-MIGRATED → MIGRATE to `sg_compute/control_plane/image/` |
| 8 | `sgraph_ai_service_playwright__cli/observability/` | LOAD-BEARING | Used by `sg_compute_specs/vnc/`, `__cli/fast_api/Routes__Observability` | NOT-MIGRATED → MIGRATE to `sg_compute/observability/` (no equivalent yet) |
| 9 | `sgraph_ai_service_playwright__cli/vault/` | LOAD-BEARING | No `sg_compute_specs/vault/` and no `sg_compute/vault/` | NOT-MIGRATED → MIGRATE (own slice) |
| 10 | `sgraph_ai_service_playwright__cli/elastic/` | LOAD-BEARING | High drift vs `sg_compute_specs/elastic/` — legacy has `lets/`, `fast_api/`, `plugin/`, `Elastic__AWS__Client.py` is 451 LOC vs 243 in new (different APIs) | KEEP legacy as canonical, RESYNC `sg_compute_specs/elastic/` from it (or DELETE the spec mirror) |
| 11 | `sg_compute_specs/elastic/` | DUPLICATE (drifted) | — | RESYNC or DELETE |
| 12 | `sgraph_ai_service_playwright__cli/elastic/lets/` | LOAD-BEARING | LETS sub-system; no migration target | NOT-MIGRATED → MIGRATE to `sg_compute/observability/lets/` (LETS briefs `v0.1.31/10,11,12` are still pending) |
| 13 | `sgraph_ai_service_playwright__cli/docker/` | LOAD-BEARING | Differs from `sg_compute_specs/docker/` (import paths + small re-organisations) | KEEP legacy until `Fast_API__SP__CLI` migrates; then DELETE legacy |
| 14 | `sg_compute_specs/docker/` (mirror) | DUPLICATE | Drifted (see legacy) | RESYNC |
| 15 | `sgraph_ai_service_playwright__cli/podman/` | LOAD-BEARING | scripts/podman.py uses legacy; spec mirror unused | KEEP, then DELETE mirror |
| 16 | `sg_compute_specs/podman/` (mirror) | DUPLICATE | — | RESYNC or DELETE |
| 17 | `sgraph_ai_service_playwright__cli/vnc/` | LOAD-BEARING | scripts/vnc.py uses legacy | KEEP, then DELETE mirror |
| 18 | `sg_compute_specs/vnc/` (mirror) | DUPLICATE | — | RESYNC or DELETE |
| 19 | `sgraph_ai_service_playwright__cli/prometheus/` | LOAD-BEARING | scripts/prometheus.py uses legacy | KEEP, then DELETE mirror |
| 20 | `sg_compute_specs/prometheus/` (mirror) | DUPLICATE | — | RESYNC or DELETE |
| 21 | `sgraph_ai_service_playwright__cli/opensearch/` | LOAD-BEARING | scripts/opensearch.py uses legacy | KEEP, then DELETE mirror |
| 22 | `sg_compute_specs/opensearch/` (mirror) | DUPLICATE | — | RESYNC or DELETE |
| 23 | `sgraph_ai_service_playwright__cli/neko/` | LOAD-BEARING | spec mirror unused | KEEP, then DELETE mirror |
| 24 | `sg_compute_specs/neko/` (mirror) | DUPLICATE | — | RESYNC or DELETE |
| 25 | `sgraph_ai_service_playwright__cli/firefox/` | LOAD-BEARING | spec mirror unused | KEEP, then DELETE mirror |
| 26 | `sg_compute_specs/firefox/` (mirror) | DUPLICATE | — | RESYNC or DELETE |
| 27 | `sgraph_ai_service_playwright__cli/lambda/` (briefs called for it) | DOES NOT EXIST | n/a | NOTE — already absent; deploy code lives in `__cli/deploy/` instead |
| 28 | `sgraph_ai_service_playwright__cli/lets/` (briefs called for it) | DOES NOT EXIST as top-level — folded under `__cli/elastic/lets/` | n/a | See row 12 |
| 29 | `sgraph_ai_service_playwright__cli/linux/` (briefs called for it) | DOES NOT EXIST — intentionally dropped | n/a | `scripts/linux.py` aliases `Podman__Service` → `Linux__Service`; ok |
| 30 | `sgraph_ai_service_playwright__host/` (whole) | DUPLICATE (orphaned) | 16 paths differ; new `sg_compute/host_plane/` adds `Routes__Host__{Auth,Docs,Logs,Pods}`, `pods/` package, `Schema__Host__Boot__Log` | DELETE — nothing outside the package imports it; tests under `tests/unit/sgraph_ai_service_playwright__host/` should be removed/migrated to `sg_compute__tests/host_plane/` |
| 31 | `agent_mitmproxy/` (whole) | LOAD-BEARING | 13 paths differ; cosmetic + import-path drift | KEEP as canonical; DELETE `sg_compute_specs/mitmproxy/` mirror or convert to shim |
| 32 | `sg_compute_specs/mitmproxy/` (mirror) | DUPLICATE | — | DELETE — CI does not build it; it has no consumers |
| 33 | `lambda_entry.py` (root) | LOAD-BEARING | n/a | KEEP — pinned by `CMD` in playwright dockerfile |
| 34 | `pyproject.toml` packages list | LOAD-BEARING | Lists `sgraph_ai_service_playwright`, `sgraph_ai_service_playwright__cli`, `sgraph_ai_service_playwright__host`, `scripts` — does NOT list `sg_compute*` | UPDATE — at minimum add `sg_compute` and `sg_compute_specs`; remove `__host` once that package is deleted |
| 35 | `version` (root `v0.1.170`) vs `pyproject.toml` (`v0.1.171`) | DRIFT | one tick stale | Author of last commit forgot to bump root `version` file (CI sync between `sgraph_ai_service_playwright/version` and `sg_compute/version` exists, but root `version` is separately maintained) |

═══════════════════════════════════════════════════════════════════════════════
## 3. What still needs migration (no equivalent under `sg_compute*` yet)
═══════════════════════════════════════════════════════════════════════════════

Ranked by how much new code already depends on the legacy module — the higher
the rank, the more the new tree is "blocked" on the migration.

### Tier 1 — blocks the whole new spec tree
1. **`__cli/ec2/` schemas + service** (`Schema__Ec2__*`, `Ec2__AWS__Client`,
   `Ec2__Service`, all `Safe_Str__*` primitives). `sg_compute/platforms/ec2/`
   only has the structural helpers (`EC2__AMI__Helper`, `Stack__Naming`, etc.)
   and `EC2__Platform.py`. The actual data classes still live in legacy and
   are imported by `sg_compute_specs/vnc/`, `sg_compute_specs/podman/`,
   `sg_compute_specs/prometheus/`, `sg_compute_specs/elastic/`. Until these
   move, the spec tree is permanently anchored to `__cli/ec2/`.
2. **`__cli/aws/Stack__Naming.py`** — used by every spec under
   `sg_compute_specs/`. Single-file, easy to lift into
   `sg_compute/platforms/aws/Stack__Naming.py`.
3. **`__cli/core/event_bus/` + `__cli/core/plugin/`** — the entire plugin
   contract (`Plugin__Registry`, `Schema__Stack__Event`, `Event__Bus`) used by
   every `sg_compute_specs/*/plugin/` and by `Fast_API__SP__CLI`. Should move
   to `sg_compute/control_plane/plugin/` and `sg_compute/control_plane/event_bus/`.
4. **`__cli/image/` schemas + `Image__Build__Service`** — used by the
   playwright legacy `Build__Docker__SGraph_AI__Service__Playwright` and by
   `Docker__SP__CLI`. Should move to `sg_compute/control_plane/image/`.
5. **`__cli/observability/`** — primitives (`Safe_Str__AWS__Region`) referenced
   from `sg_compute_specs/vnc/schemas/Schema__Vnc__Stack__Info.py`. The whole
   observability surface (AMP / Grafana / OpenSearch wiring, scripts/observability*.py)
   has zero `sg_compute/observability/` equivalent.
6. **`__cli/catalog/`** — `Stack__Catalog__Service`, `Routes__Stack__Catalog`,
   `Enum__Stack__Type`. `sg_compute_specs/*/manifest.py` files reference
   `Enum__Stack__Type` from this legacy path.

### Tier 2 — own slice, no consumers yet outside legacy
7. **`__cli/vault/`** — vault primitives, schemas, service, fast_api routes.
   Nothing in `sg_compute*` references it; it's an isolated migration.
8. **`__cli/elastic/lets/`** — the LETS Log Event Tracking System has its own
   pending briefs (`v0.1.31/10,11,12__lets-cf-*`). 4 sub-modules: `cf/`,
   `runs/`, `Call__Counter.py`, `Step__Timings.py`. No `sg_compute*` target
   exists.
9. **`__cli/fast_api/`** — the `Fast_API__SP__CLI` itself, exception handlers,
   Routes__Ec2__Playwright, Routes__Observability, lambda_handler. Once Tier 1
   lands, this can become `sg_compute/control_plane/Fast_API__Compute.py`-like.
10. **`__cli/deploy/`** — `Lambda__SP__CLI`, `Docker__SP__CLI`, `provision.py`,
    deploy_code.py, role/policy classes, `images/sp_cli/` Docker context. No
    `sg_compute*` deploy plane.

### Tier 3 — already covered by helpers in `sg_compute/platforms/ec2/` but old code still alive
11. **`__cli/docker/`, `__cli/podman/`, `__cli/vnc/`, `__cli/prometheus/`,
    `__cli/opensearch/`, `__cli/neko/`, `__cli/firefox/`** — every one of
    these has a partial mirror in `sg_compute_specs/`, but the legacy is the
    sole consumer of the `scripts/*.py` typer entry points and of
    `Plugin__Registry` discovery. The migration target is fine; the work is
    cutting consumers over.

═══════════════════════════════════════════════════════════════════════════════
## 4. Drift detection findings
═══════════════════════════════════════════════════════════════════════════════

Method: ran `diff -rq` across each legacy/new pair and sample-diffed several
representative files.

### Low-risk drift (cosmetic + import-path rewrites)
- `sgraph_ai_service_playwright/` ↔ `sg_compute_specs/playwright/core/`: 88
  diffs — every diff inspected is purely
  `from sgraph_ai_service_playwright.X` → `from sg_compute_specs.playwright.core.X`.
  The two trees are otherwise identical Python.
- `agent_mitmproxy/` ↔ `sg_compute_specs/mitmproxy/`: 13 paths differ. Diffs
  are `agent_mitmproxy.path` → `sg_compute_specs.mitmproxy.path` and one
  comment header change. New tree adds `core/`, `api/`, `manifest.py`,
  `tests/` (structural-only, mostly empty / placeholder).
- `__cli/{docker,podman,vnc,prometheus,opensearch,neko,firefox}` ↔
  `sg_compute_specs/<same>`: import-path rewrites + cosmetic comment changes.
  No logic drift detected in spot-checked files
  (`Docker__AWS__Client.py`, `Caller__IP__Detector.py`).
- `sgraph_ai_service_playwright__host/` ↔ `sg_compute/host_plane/`: 16 paths
  differ. The new tree is a SUPERSET — adds `Routes__Host__{Auth,Docs,Logs,Pods}`,
  the whole `pods/` sub-package, and `Schema__Host__Boot__Log`. Otherwise
  cosmetic / import-rewrite.

### High-risk drift (real code differences)
- **`__cli/elastic/` ↔ `sg_compute_specs/elastic/`** — DIVERGED.
  - `Elastic__AWS__Client.py` is 451 LOC in legacy vs 243 LOC in spec
    (521 diff lines). Different docstring intent ("ephemeral elastic+kibana
    lifecycle" vs generic), different method surface.
  - Legacy has `fast_api/`, `lets/`, `plugin/`, plus extra
    `List__Schema__Elastic__AMI__Info.py`, `List__Schema__Kibana__Saved_Object.py`,
    `List__Schema__Log__Document.py`, `Enum__Log__Level.py`,
    `Enum__Saved_Object__Type.py`. None of these exist in the spec mirror.
  - The spec mirror has `api/` and `manifest.py` that legacy lacks.
  - **Verdict:** the spec mirror is incomplete + outdated. If anyone copies
    from spec → legacy expecting it to be a superset, work is lost.

- **`version` files** — repo root `version` says `v0.1.170`, `pyproject.toml`
  says `v0.1.171`. Multiple version files are now in play
  (`version`, `image_version`, `sgraph_ai_service_playwright/version`,
  `sgraph_ai_service_playwright__cli/version`, `sg_compute/version`,
  `sg_compute_specs/version`, `agent_mitmproxy/version`,
  `sg_compute_specs/mitmproxy/version`, etc.). CI explicitly syncs
  `sg_compute/version` from `sgraph_ai_service_playwright/version`, but no
  job syncs the others.

═══════════════════════════════════════════════════════════════════════════════
## 5. Lambda packaging map — what gets shipped from where
═══════════════════════════════════════════════════════════════════════════════

| Lambda / Image | Dockerfile | Sources copied into image | CI workflow |
|---|---|---|---|
| **Playwright** (`sgraph_ai_service_playwright` ECR repo) | `sgraph_ai_service_playwright/docker/images/sgraph_ai_service_playwright/dockerfile` | Build context staged by `Build__Docker__SGraph_AI__Service__Playwright.build_request()`: `lambda_entry.py` + `image_version` (root) + `sgraph_ai_service_playwright/` (legacy package). **Code zip uploaded to S3 contains `sgraph_ai_service_playwright/`** (LWA hot-swap). | `.github/workflows/ci-pipeline.yml` (PACKAGE_NAME = `sgraph_ai_service_playwright`); image rebuild gate watches `sgraph_ai_service_playwright/**` and `sg_compute/**` (the latter only for the host-control sibling job inside the same workflow). |
| **Host control plane** (`sgraph_ai_service_playwright_host` ECR repo) | `docker/host-control/Dockerfile` | `docker/host-control/requirements.txt` + **`sg_compute/`** (NEW path only — legacy `__host/` not copied). `CMD` runs `sg_compute.host_plane.fast_api.lambda_handler:_app`. | `.github/workflows/ci__host_control.yml` (rebuild gate watches `sg_compute/**` + `docker/host-control/**`). |
| **SP CLI Lambda** (`sgraph_ai_service_playwright_sp_cli` style) | `sgraph_ai_service_playwright__cli/deploy/images/sp_cli/dockerfile` | Co-bakes ALL of: `sgraph_ai_service_playwright__cli/`, `sgraph_ai_service_playwright/`, `sg_compute_specs/`, `scripts/`, `sgraph_ai_service_playwright__api_site/`. Handler: `sgraph_ai_service_playwright__cli.fast_api.lambda_handler.handler`. Notably does NOT copy `sg_compute/` or `sgraph_ai_service_playwright__host/`. | `.github/workflows/ci__sp_cli.yml` (gate watches `__cli/**`, `__api_site/**`, `tests/unit/__cli/**`). |
| **Agent MITM** (`agent_mitmproxy` ECR repo) | `agent_mitmproxy/docker/images/agent_mitmproxy/Dockerfile*` | Built from `agent_mitmproxy/` (legacy) only. `sg_compute_specs/mitmproxy/` is not part of any image build. | `.github/workflows/ci__agent_mitmproxy.yml` (gate watches `agent_mitmproxy/**`). |

Three Lambdas; three independent images; only the host-control Lambda has
actually crossed over to the new tree. The mitmproxy Lambda is on legacy and
the playwright + sp-cli Lambdas are on a hybrid (legacy package + new specs
co-baked into sp-cli, legacy-only for playwright).

`scripts/run_sp_cli.py` (poetry script `sp-cli`) imports `Fast_API__SP__CLI`
from legacy `__cli/`. `scripts/provision_ec2.py` imports `agent_mitmproxy`
(legacy). All 17 sub-CLI scripts in `scripts/` (`docker_stack.py`, `elastic.py`,
etc.) import from legacy `__cli/<spec>/`.

═══════════════════════════════════════════════════════════════════════════════
## 6. Risk inventory — top 5 risks of leaving as-is
═══════════════════════════════════════════════════════════════════════════════

1. **Spec drift will be noticed by the wrong agent.** `sg_compute_specs/elastic/`
   already lacks `lets/`, `fast_api/`, `plugin/`, and 200+ lines of
   `Elastic__AWS__Client.py` that the legacy has. A future agent reading the
   spec mirror as "what we plan to build" will either silently lose features
   on a "rebase from spec" or mistake the spec mirror for a faithful copy.
   Severity: HIGH (data-loss-class bug for one well-meaning resync).

2. **`sg_compute_specs/` ↔ `__cli/` cyclic dependency cements the mess.**
   New spec schemas already import from legacy `__cli/aws/`, `__cli/catalog/`,
   `__cli/core/`, `__cli/ec2/`, `__cli/image/`, `__cli/observability/`. Each
   day this lives, the cost of `git rm`-ing the legacy paths grows. The proper
   fix is to lift those 6 directories into `sg_compute/` first, then rewire.

3. **Two independent `Fast_API__Host__Control` implementations exist; only one
   is deployed.** `sgraph_ai_service_playwright__host/fast_api/` has no
   `Routes__Host__Auth`, `Routes__Host__Pods`, etc. but it's still importable
   and indistinguishable from the new one if someone follows old import paths
   (e.g. an old debrief or an LLM hallucinated import). Run-time it would
   start a host-control plane missing four route groups.

4. **Version-file fan-out.** Eight to ten `version` files exist; only one
   sync job (sg_compute ← playwright). Already drifting:
   `version` (`v0.1.170`) vs `pyproject.toml` (`v0.1.171`). With more
   sub-package version files added, expect false claims of "released X" while
   `__cli/version` still lags. The reality doc itself depends on these files.

5. **Bus factor on the migration intent.** None of the legacy paths carry a
   `DeprecationWarning` shim or even a TODO/`SUPERSEDED` comment header
   pointing to the new path. If the original migration architect leaves /
   gets unloaded from context, the next agent reading
   `sgraph_ai_service_playwright/` has no in-tree signal that this is "the
   old one". Mitigation cost is small (one comment header per package); the
   absence is a smell.

═══════════════════════════════════════════════════════════════════════════════
## 7. Recommended cleanup order (FYI — out of scope to execute)
═══════════════════════════════════════════════════════════════════════════════

1. **DELETE `sgraph_ai_service_playwright__host/`** — orphaned, zero external
   importers, host-control image already runs from `sg_compute/host_plane/`.
   Migrate / drop tests under `tests/unit/sgraph_ai_service_playwright__host/`.
   Remove from `pyproject.toml` packages list. Smallest blast radius win.
2. **DELETE `sg_compute_specs/mitmproxy/`** (or convert to a shim re-exporting
   from `agent_mitmproxy`) — unused, will silently drift.
3. **DELETE `sg_compute_specs/playwright/core/`** (or shim) — same reason.
4. **MIGRATE Tier-1 sub-packages of `__cli/`** (`aws`, `core`, `image`,
   `catalog`, `ec2` schemas, `observability` primitives) **into `sg_compute/`**
   — this breaks the spec→legacy cyclic dependency. Then rewrite
   `sg_compute_specs/<spec>/schemas/*.py` imports.
5. **MIGRATE `__cli/vault/` and `__cli/elastic/lets/`** into `sg_compute/` as
   their own slices (LETS has pending briefs).
6. **RESYNC the spec mirrors** for `__cli/{docker,podman,vnc,elastic,
   prometheus,opensearch,neko,firefox}` from legacy (or just delete them — at
   that point there are no consumers).
7. **MIGRATE `Fast_API__SP__CLI` + `__cli/deploy/`** to `sg_compute/control_plane/`.
8. **CUT OVER `lambda_entry.py` and the playwright dockerfile** to bake from
   `sg_compute_specs/playwright/core/`. Last step — at that point legacy
   `sgraph_ai_service_playwright/` can be deleted.
9. **CUT OVER `agent_mitmproxy/` consumers** to use `sg_compute_specs/mitmproxy/`
   (or accept legacy as canonical and delete the spec mirror — that path is
   simpler).
10. **Add CI guard** — a unit test that fails if any file under `sg_compute*`
    imports from `sgraph_ai_service_playwright*` (prevents future regression
    once the migration completes).

═══════════════════════════════════════════════════════════════════════════════
## 8. Notes on legacy briefs vs. observed reality
═══════════════════════════════════════════════════════════════════════════════

- `__cli/lets/` (called for in `v0.1.31/10..12__lets-cf-*`) does NOT exist as a
  top-level — LETS landed under `__cli/elastic/lets/` instead. Migration is
  still pending; `sg_compute/observability/lets/` does not exist.
- `__cli/lambda/` (called for in earlier briefs) does NOT exist — deploy code
  landed in `__cli/deploy/` instead. Working as intended.
- `__cli/linux/` confirmed dropped intentionally; `scripts/linux.py` is a thin
  alias (`Podman__Service as Linux__Service`) and is harmless.
- The 8-spec copy from `__cli/` to `sg_compute_specs/` is incomplete: the
  legacy `fast_api/` and `plugin/` sub-folders were NOT copied for any spec.
  This is inconsistent with `sg_compute_specs/elastic/api/` existing — the
  new tree picked a different layout (`api/`) but never populated it.

═══════════════════════════════════════════════════════════════════════════════
## 9. Files referenced (absolute paths)
═══════════════════════════════════════════════════════════════════════════════

- `/home/user/SGraph-AI__Service__Playwright/lambda_entry.py`
- `/home/user/SGraph-AI__Service__Playwright/pyproject.toml`
- `/home/user/SGraph-AI__Service__Playwright/version`
- `/home/user/SGraph-AI__Service__Playwright/sgraph_ai_service_playwright/docker/images/sgraph_ai_service_playwright/dockerfile`
- `/home/user/SGraph-AI__Service__Playwright/sgraph_ai_service_playwright/docker/Build__Docker__SGraph_AI__Service__Playwright.py`
- `/home/user/SGraph-AI__Service__Playwright/docker/host-control/Dockerfile`
- `/home/user/SGraph-AI__Service__Playwright/sgraph_ai_service_playwright__cli/deploy/images/sp_cli/dockerfile`
- `/home/user/SGraph-AI__Service__Playwright/sgraph_ai_service_playwright__cli/fast_api/Fast_API__SP__CLI.py`
- `/home/user/SGraph-AI__Service__Playwright/sgraph_ai_service_playwright__cli/fast_api/lambda_handler.py`
- `/home/user/SGraph-AI__Service__Playwright/sgraph_ai_service_playwright__cli/elastic/service/Elastic__AWS__Client.py` (451 LOC)
- `/home/user/SGraph-AI__Service__Playwright/sg_compute_specs/elastic/service/Elastic__AWS__Client.py` (243 LOC)
- `/home/user/SGraph-AI__Service__Playwright/sg_compute_specs/vnc/schemas/Schema__Vnc__Stack__Info.py` (back-imports legacy `__cli/ec2/` and `__cli/observability/`)
- `/home/user/SGraph-AI__Service__Playwright/sg_compute/host_plane/fast_api/Fast_API__Host__Control.py`
- `/home/user/SGraph-AI__Service__Playwright/.github/workflows/ci-pipeline.yml`
- `/home/user/SGraph-AI__Service__Playwright/.github/workflows/ci__host_control.yml`
- `/home/user/SGraph-AI__Service__Playwright/.github/workflows/ci__sp_cli.yml`
- `/home/user/SGraph-AI__Service__Playwright/.github/workflows/ci__agent_mitmproxy.yml`
