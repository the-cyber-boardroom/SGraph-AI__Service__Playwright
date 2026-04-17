# Historian

Preserves the chronological decision trail. Owns the decisions log and the debriefs index. See [`ROLE.md`](ROLE.md).

---

## Directory Map

| Path | Purpose |
|------|---------|
| [`ROLE.md`](ROLE.md) | Full role definition |
| [`reviews/`](reviews/) | Dated phase summaries + post-mortems |
| `activity-log.md` | Append-only session log *(created on first session)* |

---

## Key Outputs

| Artefact | Path |
|----------|------|
| Decisions log | [`library/reference/v{version}__decisions-log.md`](../../../library/reference/) |
| Debrief index | [`team/claude/debriefs/index.md`](../../claude/debriefs/index.md) |
| Phase summaries | [`reviews/YY-MM-DD/v{version}__phase-{n}-summary.md`](reviews/) |

---

## Complementary to Librarian

- **Librarian** — what exists now (reality doc)
- **Historian** — how we got here (decisions log + debrief index)

Neither owns the other's artefact. Both cross-reference.
