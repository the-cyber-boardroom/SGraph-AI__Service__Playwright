# team/humans — HUMAN-ONLY

This tree is the private working area for human contributors. **Agents MUST NOT write here** except where explicitly designated (see below).

---

## Per-Human Folders

Each human gets a subfolder: `team/humans/{handle}/`.

- [`dinis_cruz/`](dinis_cruz/) — project lead

---

## Agent Access

| Path | Agent access |
|------|-------------:|
| `{handle}/briefs/` | **READ-ONLY** — treat as incoming mailbox; do NOT create files |
| `{handle}/debriefs/` | **READ-ONLY** — human-written retrospectives |
| `{handle}/claude-code-web/` | **WRITE** — agent outputs go here in `MM/DD/HH/` date-bucketed subfolders |

When an agent needs to produce something long-running or exploratory that isn't yet a formal review, it lives in `claude-code-web/`. Once promoted to a role review, the file moves under `team/roles/{role}/reviews/`.
