# SG Playwright Service — Agent Guidance

**Read this before starting any task.** This file is the single source of truth for all agents working on the Playwright service.

---

## MEMORY.md Policy

**Do NOT use MEMORY.md.** All persistent project knowledge is maintained by the Librarian in the repo itself.

---

## Reality Document — MANDATORY CHECK

**Before describing, assessing, or assuming what the Playwright service can do, READ:**

`team/explorer/librarian/reality/v0.1.0__what-exists-today.md`

### Rules (Non-Negotiable)

1. **If the reality document doesn't list it, it does not exist.**
2. **Proposed features must be labelled:** "PROPOSED — does not exist yet."
3. **Briefs are aspirations, not facts.** Cross-check against reality doc.
4. **Update the reality document when you change code.**

---

## Project

**SG Playwright Service** — browser automation API for the SG/Send ecosystem. Runs identically on laptop, CI, Claude Web, Fargate, and Lambda. Declarative step language, vault-integrated, Docker-image-based.

**Version file:** `sgraph_ai_service_playwright/version`

---

## Stack

| Layer | Technology | Rule |
|-------|-----------|------|
| Runtime | Python 3.12 / x86_64 | |
| Base image | `mcr.microsoft.com/playwright/python:v1.58.2-noble` | |
| Lambda adapter | AWS Lambda Web Adapter 1.0.0 | |
| Web framework | FastAPI via `Serverless__Fast_API` | Use `osbot-fast-api-serverless` |
| Type system | `Type_Safe` from `osbot-utils` | **Never use Pydantic. No Literals.** |
| AWS operations | `osbot-aws` | **Never use boto3 directly** |
| Browser | Playwright sync API | **Only `Step__Executor` touches `page.*`** |
| Testing | pytest, in-memory stack | **No mocks, no patches** |
| CI/CD | GitHub Actions, deploy-via-pytest | |

---

## Architecture

- **One Docker image** — same image runs on all 5 deployment targets
- **Lambda Web Adapter** — HTTP translation, not Mangum
- **lambda_handler.py** — separate file, fires up everything on import
- **Fast_API__Playwright__Service** — pure class, importable without side effects
- **25 endpoints** — 3 health + 5 session + 16 browser (Layer 0) + 1 sequence (Layer 3)
- **12 service classes** — strict responsibility separation
- **Stateless client** — `register_playwright_service__in_memory()` for test composition

---

## Key Rules

### Code Patterns

1. **All classes** extend `Type_Safe` — no plain Python classes
2. **Zero raw primitives** — no `str`, `int`, `float`, `list`, `dict` as attributes
3. **No Literals** — all fixed-value sets use `Enum__*` classes
4. **Schemas are pure data** — no methods
5. **Collection subclasses are pure type definitions** — no methods
6. **Every route returns `.json()` on a Type_Safe schema** — no raw dicts
7. **`═══` 80-char headers** — every file, every section
8. **Inline comments only** — no docstrings, ever
9. **No underscore prefix** for private methods

### Security

10. **Evaluate action is allowlist-gated** — `JS__Expression__Allowlist` defaults to deny-all
11. **No arbitrary code execution** — the shell-server pattern from OSBot-Playwright is not carried forward

### Responsibility Boundaries

12. **Step__Executor** is the ONLY class that calls `page.*` Playwright methods
13. **Artefact__Writer** is the ONLY class that writes to sinks
14. **Request__Validator** contains ALL cross-schema validation
15. **Routes have no logic** — pure delegation to `Playwright__Service`

### Class / File Naming

16. **Python identifier safety** — the spec uses names like `Docker__SGraph-AI__Service__Playwright__Base` with a hyphen in `SGraph-AI`. Python identifiers cannot contain hyphens. Normalised form:
    - Class names and module names use `SGraph_AI` (underscore) — e.g. `Docker__SGraph_AI__Service__Playwright__Base`
    - Repo root and test filenames retain `SGraph-AI` where the spec is explicit (filenames allow hyphens)

### Human Folders — Read-Only for Agents

17. **`team/humans/dinis_cruz/briefs/`** — HUMAN-ONLY. Agents must NEVER create files there.
18. **Agent outputs** go to `team/humans/dinis_cruz/claude-code-web/MM/DD/`

### Git

19. **Default branch:** `dev`
20. **Branch naming:** `claude/{description}-{session-id}`

---

## Dev Pack

The definitive specs for this project live in a vault-hosted dev pack. If you need to re-read:

```bash
sgit clone {VAULT_KEY} /tmp/playwright-dev-pack
```

Key files: `dev-specs/schema-catalogue-v2.md`, `dev-specs/routes-catalogue-v2.md`, `dev-specs/ci-pipeline.md`
