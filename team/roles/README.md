# Team — Roles

Per-role definitions for the SG Playwright Service. Every agent operating on the project adopts one of these roles (or a composition of them) for a session and produces reviews in `team/roles/{role}/reviews/MM/DD/`.

The pattern is borrowed from `SGraph-AI__App__Send` — each role has:

- `ROLE.md` — full definition (identity, responsibilities, workflows, quality gates, escalation, AI-agent guidance)
- `README.md` — one-paragraph summary + pointers
- `reviews/MM/DD/` — dated review outputs
- `activity-log.md` — append-only session log *(created on first session)*

---

## Roles

| Role | Core Mission |
|------|--------------|
| [`architect/`](architect/) | Own API contracts, schemas, and component boundaries per the specs in `library/docs/specs/`. Guard `Type_Safe` + no-Pydantic + no-boto3. |
| [`dev/`](dev/)             | Implement service classes, routes, and step executors from Architect specs. Follow one-class-per-file + `═══` headers + no mocks. |
| [`qa/`](qa/)               | Test strategy; unit + integration + deploy + smoke. Real Chromium. No `unittest.mock`. Deploy-via-pytest. |
| [`devops/`](devops/)       | CI pipeline, Docker image, ECR push, Lambda deploy. All 5 deployment targets run the same image. |
| [`librarian/`](librarian/) | Maintain the reality document, master indexes, library/ cross-references, and `.issues/` if adopted. |
| [`historian/`](historian/) | Chronological decision trail, phase debriefs, commit-hash backfill, retrospectives. |

---

## Composition vs. Specialisation

A single Claude Code session can act as multiple roles — e.g. Dev implementing a slice, then Librarian updating the reality document in the same commit. What matters is that the **outputs** go to the correct role directory. This makes the Librarian's cross-cutting index possible.

## Human-Only Folders

- `team/humans/dinis_cruz/briefs/` — **HUMAN-ONLY**. Agents never write here.
- Agent outputs go to `team/humans/dinis_cruz/debriefs/MM/DD/` or `team/humans/dinis_cruz/claude-code-web/MM/DD/`.
