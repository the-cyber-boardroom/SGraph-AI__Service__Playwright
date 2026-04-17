# Reality — What Actually Exists

This folder contains the canonical, **code-verified** record of what the SG Playwright Service actually implements.

---

## Why This Exists

Agents were confusing ideas described in briefs, dev-specs, and voice memos with features that actually exist in code. This created a false picture of the product — proposed endpoints and service classes were described as "done", and planned phases were treated as delivered.

**This folder fixes that.** Every claim here was verified by reading source code, not documentation.

---

## Rules (Non-Negotiable)

1. **If it's not in the reality document, it does not exist.** No agent may claim a feature is "working" or "shipped" unless it appears here.
2. **Proposed features must be labelled.** If an agent describes something that isn't in the reality document, they must explicitly write: `"PROPOSED — does not exist yet."`
3. **Code authors update this document.** When a Dev commits code that adds, removes, or changes an endpoint, service class, step action, or test, they must update the reality document in the same commit.
4. **The Librarian verifies.** The Librarian periodically cross-checks the reality document against the codebase and flags divergences.
5. **Briefs are aspirations, not facts.** A brief describing routes, capture flows, or deployment targets does NOT mean those features exist. Always cross-check against this document.

---

## When to Read It

- **Starting a session** — read alongside the current brief / debriefs
- **Processing a human brief** — cross-check brief claims against reality
- **Creating a debrief** — confirm what's real vs. proposed
- **Writing any review or assessment** — ground the analysis in what exists
- **Describing the service externally** — only claim what's verified

---

## Current Document

- [`v0.1.10__what-exists-today.md`](v0.1.10__what-exists-today.md) *(current)*

Previous versions are kept for historical reference and should be clearly marked as superseded.

---

## Naming Convention

`v{version}__what-exists-today.md` where `{version}` matches `sgraph_ai_service_playwright/version` at the time of writing.

Only one current version exists at a time.
