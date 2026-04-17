# QA Communication

Cross-role QA artefacts — briefs QA writes to Dev/Architect, and questions any role asks of QA.

---

## Directory Map

| Path | Purpose |
|------|---------|
| [`briefs/`](briefs/) | QA → Dev/Architect briefs — e.g. "this contract needs a test-strategy review" |
| [`questions/`](questions/) | Open questions from any role to QA |
| [`QA_START_HERE.md`](QA_START_HERE.md) | Entry point for a QA-role agent starting a session |

---

## Naming

`v{version}__{description}.md`

## Lifecycle

1. Brief / question written.
2. Target role responds (in-place or via a review file).
3. Once resolved, annotate `**Status: Resolved (commit X)**` and move to `archive/`.
