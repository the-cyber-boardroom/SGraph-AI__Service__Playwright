# 01 — Original Task & Plan

## What the operator asked for (paraphrased from session start)

> "Refactor the main playwright image. Consolidate API + CLI paths so both use the same code (API-first). The main Playwright EC2 should be as simple as possible — only Mitmproxy + Playwright. Refactor out the other containers (observability, VNC). Break those into 3 new sections modelled on the existing `sp el`/elastic pattern: OpenSearch, Prometheus, Nginx+VNC+Mitmproxy. Clean up the bloated main `sp` command list while doing this."

Plus, locked in during planning:

- Every EC2 / AMI must be **100% self-contained** — no external runtime dependencies. All configs / dashboards / scrape rules / auth material baked at AMI build time. Auth secrets generated at provision time, not fetched.
- Two distinct mitmproxy instances: one for the headless API path (in main `sp` EC2), one for the human-debug VNC viewer (in `sp vnc` stack).
- Clean slate — no live customers, no AMIs to preserve.

## The 8-doc plan (all approved + signed off)

Lives at `team/comms/plans/v0.1.96__playwright-stack-split__*.md`:

| Doc | Topic | Status |
|---|---|---|
| 01 | Overview — 8 locked decisions, success criteria | APPROVED |
| 02 | API consolidation — service-first; A1/A2/A3 signed | APPROVED |
| 03 | Strip the Playwright EC2 → 2 containers; S1/S2/S3 signed | APPROVED |
| 04 | `sp os` (OpenSearch) — folder layout, commands, tags; OS1–OS4 signed | APPROVED |
| 05 | `sp prom` (Prometheus) — folder layout, commands, scrape config; P1–P5 signed | APPROVED |
| 06 | `sp vnc` (Nginx+VNC+Mitmproxy) — renamed from `sp nvm` per N1; N1–N5 signed | APPROVED |
| 07 | Command cleanup + migration order; C1/C2 signed | APPROVED |
| 08 | Licensing & AWS Marketplace assessment | RESEARCH (legal review pending) |

All decisions + answers to the operator's open questions are recorded in each doc's "Sign-off log" section.

## Phased migration order

| Phase | Goal | Status |
|---|---|---|
| **A** | API consolidation foundation: `Stack__Naming` shared, `Image__Build__Service` shared, `Ec2__AWS__Client` full surface, typer `list`/`info`/`delete` reduced to wrappers, `delete-all` route added | ✅ done |
| **B5** | Build `sp os` (OpenSearch sister section) end-to-end | ✅ functionally complete (5g dashboard generator deferred) |
| **B6** | Build `sp prom` (Prometheus sister section) end-to-end | foundation (6a) done; 6b–6h ahead |
| **B7** | Build `sp vnc` (browser-viewer sister section) end-to-end | not started |
| **C** | Strip the Playwright EC2 → 2 containers (depends on B6 + B7 having compose fragments) | not started |
| **D** | Command cleanup + regrouping (`sp vault`, `sp ami`, drop `forward-*`) | not started |

## Key invariants (non-negotiable)

From CLAUDE.md + sign-offs:

1. Every class extends `Type_Safe` — no Pydantic, no plain Python classes
2. **No mocks, no patches** — real implementations + in-memory stack composition
3. One class per file (`Safe_*`, `Enum__*`, `Schema__*`, `Dict__*`, `List__*`)
4. `═══` 80-char headers; inline comments only
5. AWS calls go through `osbot-aws` where possible; narrow boto3 boundary acceptable for documented exceptions
6. SG GroupName must NOT start with `sg-` (AWS reserves that prefix for IDs)
7. AWS Name tag never doubles its section prefix
8. `_print_*` Console formatters live in Tier 2A (CLI rendering) — services raise typed exceptions and let the typer layer format them
