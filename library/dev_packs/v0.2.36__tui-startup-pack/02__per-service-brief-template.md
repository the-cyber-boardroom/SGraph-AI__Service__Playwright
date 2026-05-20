---
title: "Per-Service TUI Brief — TEMPLATE (copy, replace {SERVICE}, fill in)"
file: 02__per-service-brief-template.md
author: Architect (Claude)
date: 2026-05-20 (UTC hour 23)
repo: SGraph-AI__Service__Playwright @ claude/review-cf-logging-docs-QYfEq (v0.2.36 line)
status: TEMPLATE — copy this file per service; do not edit it in place.
parent: README.md
---

# Per-Service TUI Brief — TEMPLATE

> **How to use.** Copy this file to `team/humans/dinis_cruz/claude-code-web/MM/DD/HH/` (or `team/comms/`), rename it (e.g. `v{ver}__arch-brief__tui-{service}.md`), then replace every `{SERVICE}` and fill each section. Delete these instructions and the `‹guidance›` notes before committing. Read `01__tui-playbook.md` first; pick screen shapes from `03__screen-idiom-catalogue.md`. Keep the **art-of-the-possible stance** — this is an exploration brief, not a production spec.

---
---
title: "Architect Brief — {SERVICE} TUI (exploration set, real-time data)"
file: v{VER}__arch-brief__tui-{service}.md
author: {AGENT}
date: {YYYY-MM-DD} (UTC hour {HH})
repo: SGraph-AI__Service__Playwright @ {branch} ({version} line)
status: BRIEF — exploration set, not production.
parent: library/dev_packs/v0.2.36__tui-startup-pack/01__tui-playbook.md
---

# Architect Brief — {SERVICE} TUI

> Exploration, not production (see playbook §1). Each screen is a learning artefact.

## 1. What real data exists *today*  ‹the most important section — be ruthlessly honest›

‹What does this service produce/hold that is real and available right now? Where does it live (bucket / log group / API)? Volume and cadence? What is PROPOSED vs EXISTS? If most of the interesting state is PROPOSED, say so — that changes whether a TUI is worth building yet.›

| Data / resource | EXISTS / PROPOSED | Where it lives | Volume / cadence |
|---|---|---|---|
| {…} | {…} | {…} | {…} |

## 2. The primitives that back it

‹Which `sg aws {service}` subcommands / client classes already read this? Are they pure reads? List them — these are what the TUI renders. (Run `sg aws {service} --help`; check `sgraph_ai_service_playwright__cli/aws/{service}/`.)›

| Primitive | Reads | Pure read? | File |
|---|---|---|---|
| {…} | {…} | {…} | {…} |

## 3. The data-source seam  ‹playbook §2.2›

‹Can the TUI read the source directly without a heavy backend in the live loop? What's the render chain: list → fetch → (transform?) → render? What stateful backend (if any) should stay an optional downstream consumer rather than the spine?›

## 4. Candidate screens (3–6)  ‹pick idioms from `03__screen-idiom-catalogue.md`›

| # | Screen | Question it answers | Real data today? | Idiom (cat.) | Interactivity | Update |
|---|--------|---------------------|------------------|--------------|---------------|--------|
| 1 | {…} | {…} | {…} | {Live Tail / Flow Map / Topology / Inspector / Dashboard / Comparison / Simulator} | {Low/Med/High} | {rate} |
| 2 | {…} | … | | | | |
| … | | | | | | |

‹For each screen, add a short ASCII sketch and a "what this teaches" line. Favour screens that run on real data you have now.›

## 5. Simulate opportunities  ‹playbook §6›

‹Does this service have transformations or mutations worth a dry-run preview screen? What field-diff / change-set would it show? What gates the write (`SG_AWS__{SERVICE}__ALLOW_MUTATIONS`)?›

## 6. Honesty notes  ‹playbook §7›

‹What's PROPOSED that a viewer might assume is live? What can't the primitives confirm (mark `⚠ UNVERIFIED` in-UI)? Any synthetic data and how it's labelled?›

## 7. Deployment-chain checklist  ‹inherit from playbook §4›

- [ ] update ≤ 5–10 Hz
- [ ] first frame < 100 ms
- [ ] keyboard-primary
- [ ] graceful resize
- [ ] `LANG`/`TERM` at container level
- [ ] `…-tui-diagnose` subcommand

## 8. Acceptance criteria (exploration-grade)

| # | Criterion | Verification |
|---|---|---|
| 1 | N screens runnable as commands | `sg-{service}-tui <name>` works |
| 2 | Live screens read real data, no heavy backend in loop | runs with {backend} down |
| 3 | Honest status labels throughout | no mockup implies PROPOSED is live |
| 4 | Runs over SSM + `docker exec`, < 100 ms first frame | tested in the chain |
| 5 | Per-screen notes captured (kept / discarded / why) | learning documented |

## 9. Open questions

| Question | Notes |
|---|---|
| {…} | {…} |

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
