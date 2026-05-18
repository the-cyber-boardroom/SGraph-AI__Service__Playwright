---
title: "Reality — Verified-By Rolling Log"
file: verified-by.md
maintainer: Librarian
purpose: Append-only one-line-per-session signal of recent verification work. Tells a reader what was last cross-checked against code, when, and by which commit range.
---

# Reality — Verified-By Rolling Log

One paragraph per session. New entries appended to the bottom. Pattern (steal from `sgai-tools`):

> Reality verified through `{date}` via `{method}` against commits `{first}..{last}` — `{one-line summary}` ({author}).

---

Reality verified through `2026-05-17` via `ontology-proposal research pass` against commits `ce981e5..ab0c380` — audited the full reality tree (4 flat monoliths + `v0.1.31/` archive + new domain tree), `library/catalogue/`, `team/comms/`, and the past-week shipped work (vault-publish spec, vault-app TLS, `sg aws` CLI build-out, `sg repl`, Playwright-as-spec); cross-referenced patterns against `sgai-send` and `sgai-tools` Librarian outputs. Findings filed under `team/roles/librarian/reviews/05/17/v0.2.25__ontology-and-taxonomy-proposal.md`. No domain `index.md` rewritten (those land in Phase 2 — M-003 / M-004). (Librarian/Claude)

Reality verified through `2026-05-17` via `ontology rollout implementation pass` — same v0.2.25 line. Migrated all 9 unmigrated domains into the fractal tree (M-003), split `sg-compute/index.md` (M-004), seeded `proposed/index.md` for all 11 domains (M-005). VERIFY markers were left in 4 domains (`playwright-service`, `agent-mitmproxy`, `ui`, `qa`/`infra`) for the post-BV2.11/BV2.12 package deletions (`sgraph_ai_service_playwright/`, `agent_mitmproxy/`) — next session should reconcile these against the actual current code under `sg_compute_specs/playwright/` and `sg_compute_specs/mitmproxy/`. Tracked as `M-014`. Also surfaced: 19 broken links in the reality tree (tracked as `M-015`) and an endpoint-count discrepancy between CLAUDE.md (25) and wired routes (23) (`M-013`). (Librarian/Claude)

Reality verified through `2026-05-17 PM` via `dev sync + intake pass` against `origin/dev` head commit `759dfaa` (fast-forwarded from `ab0c380` — 94 commits, no merge conflicts). Root `version` now **v0.2.28**. v0.2.29 work-stream (Foundation + Slices A–H of `sg aws`) landed on dev; Dev/Architect had already authored the 7 new `cli/aws-*.md` reality files + the umbrella `cli/aws.md`, plus updated `cli/index.md` and `sg-compute/index.md`. Librarian intake added the changelog block, bumped `as_of` on all 8 catalogue shards from v0.2.25 → v0.2.28, bumped reality master index version, minted `INC-004` (regression `bcd33439` overwrote Slice B/C/D CLI with `NotImplementedError`; fixed in `c4cc6ea0`) and `INC-005` (direct `boto3` usage spread to 6 slices and 9 client files — CLAUDE.md rule 13 violation, Architect flagged H-1 HIGH). Snapshot under `library/catalogue/_snapshots/v0.2.25/` retained as historical — the next snapshot will be `v0.2.28/`, deferred to the M-016 task. (Librarian/Claude)

Reality verified through `2026-05-17 PM-late` via `Librarian finalisation pass` against commit `759dfaa` — closed M-013 (CLAUDE.md endpoint count), M-014 (7 VERIFY markers across 5 domain indexes: playwright-service, agent-mitmproxy, ui, qa, infra — full rewrites where needed, all under 300-line cap), M-015 (broken links 19 → **0** in reality tree), M-016 (catalogue snapshot `_snapshots/v0.2.28/` cut, `findings.md` refreshed with v0.2.25 → v0.2.28 deltas). M-014 surfaced 4 new INC candidates — `INC-006` (`tests/unit/scripts/test_provision_mitmproxy_ec2.py` dead placeholder) and `INC-007` (`Routes__Web` accepts all HTTP methods, security envelope rests on outer FastAPI auth gate) minted; 2 architectural notes (UI plugin sub-folder verification → `M-018`; `SIDECAR_ATTACH` capability without UI affordance → `M-019`) deferred. Only M-017 (CLAUDE.md rule proposal for INC-004 regression pattern) remains DEFERRED — awaits Architect confirmation. (Librarian/Claude)
