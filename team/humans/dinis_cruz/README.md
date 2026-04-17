# Dinis Cruz — Working Area

Private working area for Dinis Cruz (project lead).

| Path | Contents | Agent access |
|------|----------|-------------:|
| [`briefs/`](briefs/) | Raw, untriaged briefs written by Dinis | **READ-ONLY** |
| [`debriefs/`](debriefs/) | Human-written retrospectives | **READ-ONLY** |
| [`claude-code-web/`](claude-code-web/) | Agent outputs, date-bucketed `MM/DD/HH/` | **WRITE** |

## Rules for Agents

1. **Never create files under `briefs/`.** This is the human's inbox. Proposed briefs belong in `team/comms/briefs/` after triage.
2. **Never edit files under `debriefs/`.** These are first-person retrospectives.
3. **Write agent outputs under `claude-code-web/MM/DD/HH/`.** Use the current date and hour. One file per artefact.
4. **Promote, don't duplicate.** Once an agent output becomes a formal review, move it under `team/roles/{role}/reviews/` rather than copying.
