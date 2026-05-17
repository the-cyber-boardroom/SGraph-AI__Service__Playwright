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
