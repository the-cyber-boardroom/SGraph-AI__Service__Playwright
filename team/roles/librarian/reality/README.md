# Reality — What Actually Exists

This folder is the canonical, **code-verified** record of what the SG Playwright Service actually implements.

**Entry point:** [`index.md`](index.md) — master domain map. Read it first.

---

## Why This Exists

Agents were confusing ideas described in briefs, dev-specs, and voice memos with features that actually exist in code. Proposed endpoints and service classes were being described as "done"; planned phases were treated as delivered.

**This folder fixes that.** Every claim here was verified by reading source code, not documentation.

---

## Structure (Domain Tree)

The reality system is a **fractal domain tree**. Each domain covers one coherent system area. Each domain file stays under ~300 lines. When a file grows too large, it splits into sub-files linked from the domain index.

```
reality/
  README.md              ← this file
  index.md               ← master entry point: all domains + status
  changelog.md           ← pointer log: date | domain updated | one-liner

  playwright-service/    ← Core FastAPI service (routes, schemas, Step__Executor)
  agent-mitmproxy/       ← Sibling mitmproxy package
  cli/                   ← sp-cli + Fast_API__SP__CLI duality
  host-control/          ← sgraph_ai_service_playwright__host (container runtime + shell)
  ui/                    ← Static-site dashboard (sp-cli-* web components)
  vault/                 ← Vault primitives + per-plugin writer
  lets/                  ← Log Event Tracking System (CF inventory + events + consolidate)
  infra/                 ← Docker, CI, ECR, Lambda deploy, EC2, observability
  qa/                    ← Tests, deploy-via-pytest, smoke tests
  security/              ← JS allowlist, vault-key hygiene, AppSec rules
```

Each domain directory contains:

- `index.md` — EXISTS items + PROPOSED summary + links to sub-files
- `proposed/index.md` — full list of proposed features for this domain
- Sub-files (created when `index.md` exceeds ~300 lines)

---

## Rules (Non-Negotiable)

1. **If it's not in a domain index, it does not exist.** No agent may claim a feature is "working" or "shipped" unless it appears in the appropriate domain's EXISTS section.
2. **Proposed features must be labelled.** If an agent describes something not in the EXISTS section, they must write: `"PROPOSED — does not exist yet."`
3. **Code authors update the domain index.** When code ships that adds, removes, or changes an endpoint, UI page, schema, or test, update the relevant domain's `index.md` in the same commit.
4. **The Librarian verifies and maintains.** The Librarian cross-checks domain indexes against the codebase, runs the routine in [`../DAILY_RUN.md`](../DAILY_RUN.md), and updates [`changelog.md`](changelog.md) with a pointer entry.
5. **Fractal growth rule.** When any file exceeds ~300 lines, split it. Never let files grow large — create a sub-file and link from the index.
6. **Briefs are aspirations, not facts.** A brief describing routes, capture flows, or deployment targets does NOT mean those features exist. Always cross-check against the relevant domain.

---

## When to Read It

- **Starting a session** — read [`index.md`](index.md) and the relevant domain.
- **Processing a human brief** — cross-check brief claims against the relevant domain.
- **Creating a debrief** — confirm what's real vs. proposed via the domain indexes.
- **Writing any review or assessment** — ground the analysis in what exists.
- **Describing the service externally** — only claim what's verified.

---

## Migration Status (2026-05-02)

The reality system is in transition from version-stamped monoliths to the domain tree. Today:

- **`index.md`** is the master entry point.
- **`host-control/`** is the first migrated domain (pilot).
- **`v0.1.31/01..15__*.md`** remain authoritative for the other nine domains until each is migrated. See [`index.md`](index.md) "Migration shim" table for the per-domain source.
- **`changelog.md`** records updates from 2026-05-02 forward.

The migration is queued in the Librarian's [`../DAILY_RUN.md`](../DAILY_RUN.md) backlog (B-001 … B-009), one domain per session.

---

## Historical Archive

Pre-domain-tree reality snapshots, preserved for reference:

- [`v0.1.31/`](_archive/v0.1.31/README.md) — split-file reality doc covering v0.1.31 → v0.1.46+. Authoritative for un-migrated domains.
- [`v0.1.29__what-exists-today.md`](_archive/v0.1.29__what-exists-today.md) — superseded by `v0.1.31/`.
- [`v0.1.24__what-exists-today.md`](_archive/v0.1.24__what-exists-today.md) — superseded.
- [`v0.1.13__what-exists-today.md`](_archive/v0.1.13__what-exists-today.md) — superseded.
- [`v0.1.12__what-exists-today.md`](_archive/v0.1.12__what-exists-today.md) — superseded.

Old single-file naming was `v{version}__what-exists-today.md`. The v0.1.31 split used numbered sub-files inside a versioned folder. Both are retained as-is; new content goes into the domain tree only.
