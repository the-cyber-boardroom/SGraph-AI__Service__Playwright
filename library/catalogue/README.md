# Library Catalogue — SG Playwright Service

The SG Playwright Service is a browser-automation API (FastAPI + Playwright) that also
hosts a CLI/HTTP control plane for ephemeral cloud stacks (EC2, Elastic/Kibana,
OpenSearch, Prometheus) and a LETS pipeline that indexes CloudFront logs into Elasticsearch.
It runs identically on laptop, CI, Claude Web, Fargate, and AWS Lambda.

**Current version:** `v0.1.100`  
**Reality docs:** `team/roles/librarian/reality/v0.1.31/` (canonical source of truth)

---

## Map of Maps

| File | What it covers | Who reads it |
|------|---------------|--------------|
| `01__project-overview.md` | Two packages, stack, key rules | Everyone — read first |
| `02__cli-packages.md` | All sub-packages under `sgraph_ai_service_playwright__cli/` | Dev adding a new CLI section |
| `03__lets-pipeline.md` | L-C-E-T-S pipeline, all 4 slices, index patterns | Dev working on LETS |
| `04__elastic-stack.md` | Elastic/Kibana stack management, HTTP client, dashboards | Dev touching `sp el` |
| `05__playwright-service.md` | FastAPI browser API, 18 endpoints, service classes | Dev touching the Playwright Lambda |
| `06__scripts-and-cli.md` | Every script in `scripts/`, Typer app tree | Dev running or extending CLI |
| `07__testing-patterns.md` | No-mocks rule, `*__In_Memory` pattern, test layout | Dev writing new tests |
| `08__aws-and-infrastructure.md` | Lambda, EC2, S3, OpenSearch, ECR, IAM, CI | DevOps / Architect |
| `09__team-and-roles.md` | 6 agent roles, debrief index, human inbox rules | All agents |

---

## New-Session Quick-Start (read in order)

1. `/.claude/CLAUDE.md` — project rules, stack constraints, non-negotiables
2. `team/roles/librarian/reality/v0.1.31/README.md` — what exists today (index)
3. `sgraph_ai_service_playwright/version` — current package version
4. This file (`library/catalogue/README.md`) — orient yourself in the graph
5. `library/catalogue/01__project-overview.md` — architecture snapshot
6. The catalogue file for your concern area (02–09 above)
7. `team/roles/{role}/ROLE.md` — your role's responsibilities
8. `team/comms/` — any open briefs or plans for your area
9. `team/claude/debriefs/index.md` — what each prior slice delivered

---

## Key Cross-Links

| Destination | Path |
|-------------|------|
| Reality doc index | `team/roles/librarian/reality/v0.1.31/README.md` |
| Project rules | `/.claude/CLAUDE.md` |
| Testing guide | `library/guides/v3.1.1__testing_guidance.md` |
| Schema catalogue (spec) | `library/docs/specs/v0.20.55__schema-catalogue-v2.md` |
| Routes catalogue (spec) | `library/docs/specs/v0.20.55__routes-catalogue-v2.md` |
| Debrief index | `team/claude/debriefs/index.md` |
| Open plans | `team/comms/plans/` |
