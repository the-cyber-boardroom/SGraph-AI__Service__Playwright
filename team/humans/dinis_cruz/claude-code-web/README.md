# claude-code-web — Agent Outputs

This is where agents write working files that are not yet formal role reviews. Think of it as the scratchpad the human can browse at the end of a session.

## Naming

`MM/DD/HH/{short-description}.md`

- `MM/DD/HH/` — date + hour in UTC. Multiple files in the same hour are fine.
- Short descriptor in kebab-case.

## Promotion

If an agent output becomes a formal review, move it under `team/roles/{role}/reviews/YY-MM-DD/v{version}__{description}.md`. Leave a pointer stub behind if the original is referenced elsewhere.

## What NOT to Write Here

- Code — that goes in `sgraph_ai_service_playwright/`.
- Formal role reviews — those go in `team/roles/{role}/reviews/`.
- Reality-doc updates — those go in `team/roles/librarian/reality/`.
- Decision-log entries — those go in `library/reference/`.
