# SG Playwright Service

Browser automation FastAPI service for the SG/Send ecosystem. Runs identically on laptop, CI, Claude Web, Fargate, and Lambda from a single Docker image. Declarative step language, vault-integrated.

## Stack

| Layer          | Technology                                                   |
|----------------|--------------------------------------------------------------|
| Runtime        | Python 3.12 / x86_64                                         |
| Base image     | `mcr.microsoft.com/playwright/python:v1.58.2-noble`          |
| Lambda adapter | AWS Lambda Web Adapter 1.0.0                                 |
| Web framework  | FastAPI via `Serverless__Fast_API` (`osbot-fast-api-serverless`) |
| Type system    | `Type_Safe` from `osbot-utils` (no Pydantic, no Literals)    |
| AWS operations | `osbot-aws` (no direct boto3)                                |
| Browser        | Playwright sync API (only `Step__Executor` touches `page.*`) |
| Testing        | pytest, in-memory stack (no mocks)                           |
| CI/CD          | GitHub Actions, deploy-via-pytest                            |

## Repo layout

```
sgraph_ai_service_playwright/       Package code
  schemas/                          Primitives, enums, schemas, collections
  fast_api/                         Routes + lambda_handler.py
  service/                          12 service classes
  dispatcher/                       Step schema registries
  client/                           Stateless client + registration helpers
  docker/                           Docker infrastructure classes + images/
  consts/                           env_vars.py, version.py
tests/
  unit/         integration/        docker/         deploy/
team/explorer/                      6 roles (Explorer team)
.github/workflows/                  CI pipeline (base + per-branch wrappers)
```

## Status

**Phase 0 in progress** — repo skeleton, Dockerfile, CI workflow scaffolding.
See `.claude/CLAUDE.md` for agent guidance and `team/explorer/librarian/reality/` for the code-verified feature inventory.

