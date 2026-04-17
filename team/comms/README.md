# team/comms — Cross-Role Communication

This is the shared surface between roles. Anything that crosses a role boundary — a question, a plan, a changelog entry, a QA brief — lives here rather than in a role's own folder.

---

## Directory Map

| Path | Purpose | Audience |
|------|---------|----------|
| [`briefs/`](briefs/) | Human → team briefs forwarded from `team/humans/dinis_cruz/briefs/` (only once triaged) | All roles |
| [`plans/`](plans/) | Cross-role plans — `{version}__{description}.md` | All roles |
| [`changelog/`](changelog/) | Dated changelog entries using the good-failure / bad-failure convention | All roles |
| [`qa/`](qa/) | QA briefs + cross-role questions | QA, Dev, Architect |

---

## Rules

1. **Version prefix every file** — `v{version}__{description}.md`. Versions match `sgraph_ai_service_playwright/version`.
2. **One topic per file** — don't accumulate unrelated ideas in one brief.
3. **Link back to the source** — a brief derived from a human memo should cite the memo by path.
4. **Close out** — once a brief / plan is delivered, move it to an `archive/` subfolder with the closing-commit hash.

---

## When to Write What

| Situation | Location |
|-----------|----------|
| Asking another role a question | `qa/questions/v{version}__{short-question}.md` |
| Proposing a multi-role plan | `plans/v{version}__{plan-name}.md` |
| Recording a released slice | `changelog/YY-MM-DD/v{version}__{description}.md` |
| Human brief received, needs triage | `briefs/v{version}__{brief-name}.md` |

---

## Related

- Role-specific reviews → `team/roles/{role}/reviews/`
- Phase debriefs → `team/claude/debriefs/`
- Human-only briefs (untriaged) → `team/humans/dinis_cruz/briefs/` *(agents NEVER write here)*
