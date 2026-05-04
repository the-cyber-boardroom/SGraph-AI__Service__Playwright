# 09 — Team and Roles

→ [Catalogue README](README.md)

Six agent personas, one shared codebase. Always choose the role that matches your task before starting.

---

## The Six Roles

| Role | Owns | ROLE.md |
|------|------|---------|
| **Architect** | API contracts, schemas, architectural boundaries | `team/roles/architect/ROLE.md` |
| **Dev** | Implementation, tests, refactors | `team/roles/dev/ROLE.md` |
| **QA** | Test strategy, deploy-via-pytest assertions | `team/roles/qa/ROLE.md` |
| **DevOps** | CI, Docker image, ECR, Lambda provisioning | `team/roles/devops/ROLE.md` |
| **Librarian** | Reality doc, cross-references, indexes | `team/roles/librarian/ROLE.md` |
| **Historian** | Decision log, debrief index, phase summaries | `team/roles/historian/ROLE.md` |

---

## Where Each Role's Output Lives

| Role | Primary output paths |
|------|---------------------|
| Architect | `library/docs/specs/`, `library/docs/research/` |
| Dev | `sgraph_ai_service_playwright/`, `sgraph_ai_service_playwright__cli/`, `tests/` |
| QA | `tests/deploy/`, `tests/integration/`, `library/guides/` |
| DevOps | `.github/workflows/`, `scripts/provision_*.py`, `docker/` |
| Librarian | `team/roles/librarian/reality/v{version}/`, `library/catalogue/` |
| Historian | `library/reference/v{version}__decisions-log.md`, `team/claude/debriefs/index.md` |

---

## Reality Doc — Update Obligation

When code changes, update the corresponding file under `team/roles/librarian/reality/v0.1.31/`.

| Code area | Reality file to update |
|-----------|----------------------|
| Playwright service endpoints / service classes | `01__playwright-service.md` |
| agent_mitmproxy | `02__agent-mitmproxy-sibling.md` |
| Docker images + CI | `03__docker-and-ci.md` |
| Tests | `04__tests.md` |
| SP CLI — aws/deploy/ec2/image/observability | `06__sp-cli-duality-refactor.md` |
| SP CLI — EC2 FastAPI routes | `07__sp-cli-ec2-fastapi.md` |
| SP CLI — Lambda deploy | `08__sp-cli-lambda-deploy.md` |
| SP CLI — Observability routes | `09__sp-cli-observability-routes.md` |
| LETS inventory slice | `10__lets-cf-inventory.md` |
| LETS events slice | `11__lets-cf-events.md` |
| LETS consolidate slice | `12__lets-cf-consolidate.md` |

---

## Debrief Index

Location: `team/claude/debriefs/index.md`

Every work slice gets a debrief. Format: `team/claude/debriefs/{date}__{slice-name}.md`

**Good failure** — surfaced early, caught by tests, informed a better design.
**Bad failure** — silenced, worked around, or re-introduced. Implicit follow-up request.

Recent debriefs (most recent first):

- `2026-04-26__playwright-stack-split__phase-B__step-6a__sp-prom-foundation.md`
- `2026-04-26__playwright-stack-split__phase-B__step-5f4b__create-stack-wired.md`
- `2026-04-26__playwright-stack-split__phase-B__step-5f4a__launch-helper.md`
- `2026-04-26__playwright-stack-split__phase-B__step-5i__sp-os-typer.md`
- `2026-04-26__lets-cf-events__*.md` (3 files)
- `2026-04-26__lets-cf-inventory__*.md` (3 files)

---

## Communication Channels

| Path | Purpose |
|------|---------|
| `team/comms/briefs/` | Cross-role background briefs and proposals |
| `team/comms/plans/` | Numbered execution plans for multi-slice work |
| `team/comms/changelog/` | Cross-role change log |
| `team/comms/qa/` | QA findings |

---

## Human Inbox Rules (CRITICAL)

- `team/humans/dinis_cruz/briefs/` — **HUMAN-ONLY. Agents MUST NEVER create files here.**
- `team/humans/dinis_cruz/debriefs/` — **HUMAN-ONLY. Agents MUST NEVER edit files here.**
- Agent scratch outputs go to: `team/humans/dinis_cruz/claude-code-web/{MM}/{DD}/{HH}/`

---

## Branch and Commit Rules

| Rule | Value |
|------|-------|
| Default branch | `dev` |
| Branch naming | `claude/{description}-{session-id}` |
| Agents never push to `dev` directly | Open a PR from the feature branch |
| Commit style | `type(scope): description` |

---

## Cross-Links

- `team/roles/librarian/reality/v0.1.31/README.md` — what exists today
- `team/claude/debriefs/index.md` — debrief index
- `/.claude/CLAUDE.md` — full rules (sections: Roles, Git, Testing, Key Rules)
