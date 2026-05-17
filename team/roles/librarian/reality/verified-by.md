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
