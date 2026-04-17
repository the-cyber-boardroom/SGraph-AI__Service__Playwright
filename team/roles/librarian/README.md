# Librarian

Maintains knowledge connectivity, owns the reality document, produces master indexes. See [`ROLE.md`](ROLE.md).

---

## Directory Map

| Path | Purpose |
|------|---------|
| [`ROLE.md`](ROLE.md) | Full role definition |
| [`reality/`](reality/) | Canonical, code-verified record of what exists today |
| [`reviews/`](reviews/) | Dated master indexes + health scans |
| `activity-log.md` | Append-only session log *(created on first session)* |

---

## Reality Document

`reality/v{version}__what-exists-today.md` is the **single source of truth** for what the service actually implements. It was built by reading source code, not briefs or reviews.

### Rules

1. **If it's not in the reality doc, it does not exist.**
2. **Proposed features must be labelled** — `"PROPOSED — does not exist yet"`.
3. **Code authors update the reality doc** in the same commit as the code change.
4. **The Librarian verifies** — periodically cross-check the reality doc against the code.

The current file is [`reality/v0.1.11__what-exists-today.md`](reality/).
