# Playwright debrief — architect response pack (2026-05-30)

Source: the v0.2.47 driving session by @Content. Three input docs (the guide they wrote
for the next Claude session, the bugs+FR debrief, the probe-batch addendum) plus the
architect's 8-phase implementation plan.

## Read in this order

| # | File | What |
|---|------|------|
| 00.a | [`00__a__guide-from-the-session.md`](00__a__guide-from-the-session.md) | The session's own "next-Claude" guide. Confirms our v0.2.45 guide is mostly right; adds BUG-1 (URL fragment `:`) and the `networkidle` ≠ "SPA rendered" gotcha. |
| 00.b | [`00__b__debrief-bugs-and-feature-requests.md`](00__b__debrief-bugs-and-feature-requests.md) | Headline report: 2 reproducible bugs (BUG-1, BUG-2) + FR-1..FR-7. |
| 00.c | [`00__c__addendum-probe-batch-reframe.md`](00__c__addendum-probe-batch-reframe.md) | **Most important.** Reframes the whole API: agents need *navigate-once / probe-many* for understanding, not a linear action pipeline. Introduces the proposed `/pw/inspect` endpoint. |
| 01 | [`01__implementation-plan.md`](01__implementation-plan.md) | **The plan.** 8 phases (Φ1..Φ8), what's IN each, what's OUT, the explicit non-goals, risks, and the four questions for owner ratification before Φ1 starts. |

## One-paragraph summary

Two real bugs to fix first (one is likely my own regression from slice A); a quick-wins
block that kills the blind-wait anti-pattern in days; a DOM-reads phase that ends "I don't
know what to wait on"; a console+network capture phase; **then the new headline feature:
`/pw/inspect` probe-batch** that converts the service from an action-pipeline into a
debugging instrument; shadow-DOM + context-level capture; opt-in stateful sessions; and
finally the async engine. Async drops from P2 to Φ8 because real-world driving shows sync
works fine once the verbs are real. Non-goals (live screencast, CDP relay, native
assertions, retries, streaming) are listed explicitly in plan §2 with reasons.
