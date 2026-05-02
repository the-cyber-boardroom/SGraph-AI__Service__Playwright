# Librarian Daily Run

**What this file is:** the daily playbook for Librarian sessions. Also serves as the persistent "important but not urgent" task queue — work the Librarian does when no urgent briefs are waiting.

Start every session by reading this file. End every session by updating it.

---

## Standard Routine (Every Session)

1. **Pull from dev** — `git fetch origin dev && git merge origin/dev`
2. **Read this file** — check ACTIVE TASKS and BACKLOG before doing anything else
3. **Read `activity-log.md`** — the previous session's continuity note (one-liner)
4. **Check for new briefs** — scan `team/humans/dinis_cruz/briefs/MM/[today]/` and any missed dates
5. **If new briefs exist:**
   - Process each (read fully, extract theme, SHIPPED vs PROPOSED, new endpoints / components / schemas)
   - Update the relevant **domain `index.md`** under `team/roles/librarian/reality/`
   - Append a pointer entry to `team/roles/librarian/reality/changelog.md`
   - File a master index at `team/roles/librarian/reviews/MM/DD/{version}__master-index__{description}.md` (folder created on first review)
6. **If no new briefs:**
   - Scan `origin/dev` for commits since last session — `git log --oneline origin/dev --since="<last session date>"`
   - Update the relevant domain `index.md` for any shipped code
   - Append a pointer entry to `changelog.md`
   - Pick **one task** from the BACKLOG below and work it
7. **Update `activity-log.md`** — date, version, one-line summary of the session
8. **Commit and push** — every session ends with a push to the feature branch

---

## Reality Document System

The reality document is a **domain tree** at `team/roles/librarian/reality/`. See [`reality/README.md`](reality/README.md) for the full rules.

**Entry point:** [`reality/index.md`](reality/index.md) — master table linking all 10 domains.

**Domains (current):**

| Domain | Covers |
|--------|--------|
| `playwright-service/` | Core FastAPI service, routes, schemas, Step__Executor, Browser__Launcher |
| `agent-mitmproxy/` | Sibling mitmproxy package (admin FastAPI, addons, reverse-proxied UI) |
| `cli/` | sp-cli + Fast_API__SP__CLI (the duality), observability, EC2, catalog, vault routes |
| `host-control/` | sgraph_ai_service_playwright__host (container runtime, shell executor, Routes__Host__*) |
| `ui/` | Static-site dashboard (sp-cli-* web component family, plugins, fractal-UI) |
| `vault/` | Vault primitives, per-plugin writer, sgit integration |
| `lets/` | Log Event Tracking System (CF inventory + events + consolidate) |
| `infra/` | Docker images, CI, ECR, Lambda deploy, EC2 provisioning, observability stack |
| `qa/` | Tests (unit, integration, deploy-via-pytest), smoke tests, test inventory |
| `security/` | JS allowlist, vault-key hygiene, security-group naming, AppSec rules |

**When processing a brief or commit:**

- Identify which domain(s) it affects (see the table above).
- Edit the relevant domain's `index.md` (or sub-file if one exists).
- If a domain file exceeds ~300 lines → split it (create a sub-file, link from the index).
- Never let files grow large — fractal principle: split before it hurts.

**Proposed items:** Each domain has a `proposed/` subdirectory. PROPOSED features live next to the domain they extend — not in a central mega-file. When `proposed/index.md` exceeds ~300 lines, split into topic files (e.g. `proposed/firefox-config-column.md`).

---

## ACTIVE TASKS

*(Move tasks here from BACKLOG when starting them; remove when complete.)*

None currently active.

---

## BACKLOG (Important But Not Urgent)

Work these when no urgent brief processing is needed. Pick **one per session**. Numbered sequentially — add new tasks freely (B-011, B-012, …) and never renumber.

### B-001 · Migrate domain — `playwright-service/`

**Status:** QUEUED
**What:** Convert `reality/v0.1.31/01__playwright-service.md` into `reality/playwright-service/index.md` + `reality/playwright-service/proposed/index.md`. Cross-check current code (`sgraph_ai_service_playwright/fast_api/`, `sgraph_ai_service_playwright/service/`) before copying — the v0.1.31 slice was last refreshed 2026-04-20 and the codebase has moved (firefox config endpoints, three-mode stack creation payload, etc. have landed since).
**Why:** Largest domain. The Architect, Dev and QA roles all read this first.
**Acceptance:** Domain index lists every live endpoint, every Type_Safe service class, every step action; proposed file lists deferred work pulled from `v0.1.31/05__proposed.md` filtered to this domain.

### B-002 · Migrate domain — `cli/`

**Status:** QUEUED
**What:** Consolidate `v0.1.31/06__sp-cli-duality-refactor.md`, `07__sp-cli-ec2-fastapi.md`, `09__sp-cli-observability-routes.md`, and the catalog-routes portion of `13__*.md` into `reality/cli/index.md`. Add the recent vault-routes work (`Routes__Vault__Plugin`) and the firefox-config routes if they live on the CLI app.
**Why:** Second-largest domain. Multiple slices currently fragmented.
**Acceptance:** Single index covering every route on `Fast_API__SP__CLI` plus the Typer command surface. Cross-link to `host-control/` for the host package interactions.

### B-003 · Migrate domain — `ui/`

**Status:** QUEUED
**What:** Consolidate `v0.1.31/13__sp-cli-linux-docker-elastic-catalog-ui.md`, `14__sp-cli-ui-sg-layout-vnc-wiring.md`, `15__sp-cli-ui-dev-agent-dashboard.md` into `reality/ui/index.md`. Bring in the post-fractal-UI changes already on dev (firefox card+detail, podman card+detail, stop-button polish, vault gate removal). Cross-link to the UI Architect orientation review.
**Why:** UI work is the most active surface. Agents currently read three separate slices.
**Acceptance:** Single index listing every `sp-cli-*` web component with file:line refs and every plugin folder. Reserved-but-unimplemented events documented under `proposed/`.

### B-004 · Migrate domain — `lets/`

**Status:** QUEUED
**What:** Consolidate `v0.1.31/10__lets-cf-inventory.md`, `11__lets-cf-events.md`, `12__lets-cf-consolidate.md` into `reality/lets/index.md`. The LETS surface is self-contained and a clean migration candidate.
**Why:** Smallest of the multi-slice domains; good warm-up.

### B-005 · Migrate domain — `agent-mitmproxy/`

**Status:** QUEUED
**What:** Convert `v0.1.31/02__agent-mitmproxy-sibling.md` into `reality/agent-mitmproxy/index.md`. Cross-check the addons (`addons/Default_Interceptor.py`, `Audit_Log.py`, `prometheus_metrics_addon.py`) and the admin endpoints.
**Why:** Sibling package; clean boundary.

### B-006 · Migrate domain — `infra/`

**Status:** QUEUED
**What:** Consolidate `v0.1.31/03__docker-and-ci.md` and `08__sp-cli-lambda-deploy.md` into `reality/infra/index.md`. Add the EC2 provisioning content from the firefox brief and the new `docker/host-control/` Dockerfile.
**Why:** DevOps reads this first.

### B-007 · Migrate domain — `qa/`

**Status:** QUEUED
**What:** Convert `v0.1.31/04__tests.md` into `reality/qa/index.md`. Refresh test counts (commit `11c2a08` reports 1653 unit tests).
**Why:** QA reads this first; the count is stale.

### B-008 · Migrate domain — `vault/`

**Status:** QUEUED
**What:** Seed `reality/vault/index.md` from the recently merged `Routes__Vault__Plugin` and `Vault__Plugin__Writer` work (no v0.1.31 slice exists for vault). Cross-reference with the post-fractal-UI brief 04.
**Why:** Domain has no current home in reality; first consumers (firefox MITM scripts, profiles) are landing.

### B-009 · Migrate domain — `security/`

**Status:** QUEUED
**What:** Extract security-critical content from `.claude/CLAUDE.md` (rules 10-15: JS allowlist, vault keys, AWS resource naming) and the allowlist sections of `v0.1.31/01__playwright-service.md` into `reality/security/index.md`.
**Why:** Cross-cutting security properties have no single home today; AppSec reviews need it.

### B-010 · Distribute `v0.1.31/05__proposed.md` across domain `proposed/index.md` files

**Status:** QUEUED
**What:** Walk the existing cross-cutting proposed list and place each item under its owning domain's `proposed/index.md`. Items that span multiple domains are duplicated (or referenced) per domain.
**Why:** Once domains are migrated, the central proposed file no longer makes sense. Each domain owns its own backlog.
**Depends on:** B-001 through B-009 (complete the migrations first).

### B-011 · Health scan — broken relative links across `team/` and `library/`

**Status:** QUEUED
**What:** Walk every `.md` file under `team/` and `library/`, extract relative links, verify each resolves. Report broken links in a health-scan review under `team/roles/librarian/reviews/MM/DD/`.
**Why:** Link rot accumulates silently. No prior scan on record.

---

## COMPLETED (Recent)

| Date | Task | Outcome |
|------|------|---------|
| 2026-05-02 | Pilot domain migration: `host-control/` | First domain migrated to the new format; serves as template for B-001 ... B-009. |
| 2026-05-02 | Reality document scaffolding (index.md, changelog.md, README rewrite) | 10-domain fractal tree designed; migration shim in place referencing v0.1.31 slices. |
| 2026-05-02 | DAILY_RUN.md + activity-log.md introduced | Daily routine + backlog established; session continuity record started. |
| 2026-05-02 | ROLE.md updated to reflect the domain tree | Primary Responsibilities, Workflow 1, Quality Gates, Tools, Starting a Session — all rewritten around DAILY_RUN, the domain tree, and the changelog. |

---

## Notes for the Librarian

- **One backlog task per session.** Do not try to clear the whole backlog at once — a single thorough migration is worth more than three rushed ones.
- **Update this file at session end.** Move completed tasks to the COMPLETED table. Adjust task descriptions if what you found differed from what was expected. Add new tasks freely (B-013 …) and never renumber.
- **Add tasks freely.** When you notice something that needs fixing but isn't urgent, add it to the BACKLOG.
- **Never skip the routine.** Even on "no brief" days, the routine produces value (dev scan, changelog entry, one backlog task).
- **The 30-second findability rule.** If a piece of knowledge exists in this repo but cannot be found in under 30 seconds, the Librarian has failed.
