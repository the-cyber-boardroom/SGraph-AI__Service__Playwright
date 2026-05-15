# SG Playwright Service — Agent Guidance

**Read this before starting any task.** This file is the single source of truth for all agents working on the Playwright service.

---

## MEMORY.md Policy

**Do NOT use MEMORY.md.** All persistent project knowledge is maintained by the Librarian in the repo itself.

---

## Reality Document — MANDATORY CHECK

**Before describing, assessing, or assuming what the Playwright service can do, READ the current reality doc.**

Start here: [`team/roles/librarian/reality/README.md`](../team/roles/librarian/reality/README.md) — it points at the current `v{version}__what-exists-today.md` and lists supersession rules. The filename is version-stamped; the README always tracks the current one, so you do not need to edit this CLAUDE.md on every version bump.

### Rules (Non-Negotiable)

1. **If the reality document doesn't list it, it does not exist.**
2. **Proposed features must be labelled:** "PROPOSED — does not exist yet."
3. **Briefs are aspirations, not facts.** Cross-check against reality doc.
4. **Update the reality document when you change code.**

The canonical location moved from `team/explorer/librarian/reality/` to `team/roles/librarian/reality/` on 2026-04-17 to align with the `team/roles/{role}/` convention. The old path contains a SUPERSEDED stub pointer.

---

## Where Knowledge Lives

| Kind | Path | Authority |
|------|------|-----------|
| **Project catalogue** | [`library/catalogue/README.md`](../library/catalogue/README.md) | **Start here for orientation.** Fractal index of all packages, services, tests, schemas, and AWS resources. Read before any new task. |
| What exists today | `team/roles/librarian/reality/v{version}__what-exists-today.md` | **Canonical.** If not here, it does not exist. |
| Contracts / specs | `library/docs/specs/` | Aspiration until reality-doc confirms |
| Research | `library/docs/research/` | Context, not spec |
| Style / patterns | `library/guides/` | Non-negotiable once adopted |
| Historical context | `library/reference/v{version}__arch-brief.md`, `library/reference/v{version}__decisions-log.md` | Append-only |
| Onboarding briefs | `library/briefing/` | Numbered reading order |
| Roadmap | `library/roadmap/phases/v{version}__phase-overview.md` | Phase status (✅/🟡/❌/⚠) |
| Role definitions | `team/roles/{role}/ROLE.md` | What each agent persona owns |
| Phase debriefs | `team/claude/debriefs/` + `index.md` | Per-slice retrospective |
| Session handover guide | [`team/claude/debriefs/SESSION_HANDOVER_GUIDE.md`](../team/claude/debriefs/SESSION_HANDOVER_GUIDE.md) | Meta-template for "wrap up this session" |
| Cross-role briefs / plans / changelog | `team/comms/` | Communication between roles |
| Human inbox (HUMAN-ONLY) | `team/humans/dinis_cruz/briefs/` | Agents NEVER write here |
| Agent outputs | `team/humans/dinis_cruz/claude-code-web/MM/DD/HH/` | Scratch space, promote to reviews when formal |

---

## Roles

Six personas, one shared codebase. Pick the role that fits the task before you start:

| Role | Owns | Read |
|------|------|------|
| **Architect** | API contracts, schemas, boundaries | [`team/roles/architect/ROLE.md`](../team/roles/architect/ROLE.md) |
| **Dev** | Implementation, tests, refactors | [`team/roles/dev/ROLE.md`](../team/roles/dev/ROLE.md) |
| **QA** | Test strategy, deploy-via-pytest assertions | [`team/roles/qa/ROLE.md`](../team/roles/qa/ROLE.md) |
| **DevOps** | CI, Docker image, ECR, Lambda | [`team/roles/devops/ROLE.md`](../team/roles/devops/ROLE.md) |
| **Librarian** | Reality doc, cross-references, indexes | [`team/roles/librarian/ROLE.md`](../team/roles/librarian/ROLE.md) |
| **Historian** | Decision log, debrief index, phase summaries | [`team/roles/historian/ROLE.md`](../team/roles/historian/ROLE.md) |

---

## Project

**SG Playwright Service** — browser automation API for the SG/Send ecosystem. Runs identically on laptop, CI, Claude Web, Fargate, and Lambda. Declarative step language, vault-integrated, Docker-image-based.

**Version file:** `sgraph_ai_service_playwright/version`

---

## Stack

| Layer | Technology | Rule |
|-------|-----------|------|
| Runtime | Python 3.12 / x86_64 | |
| Base image | `mcr.microsoft.com/playwright/python:v1.58.0-noble` | v1.58.2 is not published |
| Lambda adapter | AWS Lambda Web Adapter 1.0.0 | |
| Web framework | FastAPI via `Serverless__Fast_API` | Use `osbot-fast-api-serverless` |
| Type system | `Type_Safe` from `osbot-utils` | **Never use Pydantic. No Literals.** |
| AWS operations | `osbot-aws` | **Never use boto3 directly** (narrow documented exception for the Lambda Function URL two-statement permission fix) |
| Browser | Playwright sync API | **Only `Step__Executor` touches `page.*`** (`Browser__Launcher` handles process lifecycle) |
| Testing | pytest, in-memory stack | **No mocks, no patches** |
| CI/CD | GitHub Actions, deploy-via-pytest | |

---

## Architecture

- **One Docker image** — same image runs on all 5 deployment targets
- **Lambda Web Adapter** — HTTP translation, not Mangum
- **lambda_handler.py** — separate file, fires up everything on import
- **Fast_API__Playwright__Service** — pure class, importable without side effects
- **25 endpoints** — 3 health + 5 session + 16 browser (Layer 0) + 1 sequence (Layer 3)
- **12 service classes** — strict responsibility separation (10 live today)
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
7. **`═══` 80-char headers** — every file, every section. **Python files only.** In Markdown, `#` is heading syntax — a `# ═══` header block renders as a stack of H1s on GitHub. For Markdown deliverables (briefs, plans, debriefs, reviews) use YAML frontmatter — see [`library/guides/v0.2.15__markdown_doc_style.md`](../library/guides/v0.2.15__markdown_doc_style.md).
8. **Inline comments only** — no docstrings, ever
9. **No underscore prefix** for private methods

### Security

10. **Evaluate action is allowlist-gated** — `JS__Expression__Allowlist` defaults to deny-all
11. **No arbitrary code execution** — the shell-server pattern from OSBot-Playwright is not carried forward
12. **No AWS credentials in Git.** Live in GH Actions repository secrets only. Never in `.env.example`, never in any committed file.
13. **No vault keys in Git.** Vault keys (e.g. `sgit` dev-pack key) are shared out-of-band. If one appears in a diff, block the commit.

### AWS Resource Naming

14. **Security group `GroupName` must NOT start with `sg-`.** AWS reserves the `sg-*` prefix for security group IDs and rejects `CreateSecurityGroup` with `InvalidParameterValue` if the GroupName matches that pattern. Use a suffix instead (e.g. `{stack}-sg`) or a non-`sg-` prefix. Tracked precedent: `scripts/provision_ec2.py:83` (`SG__NAME = 'playwright-ec2'`), `sgraph_ai_service_playwright__cli/elastic/service/Elastic__AWS__Client.py` (`sg_name_for_stack` helper).
15. **AWS Name tag — never double-prefix.** When the logical name already carries the namespace (e.g. `elastic-quiet-fermi`), do not wrap it again into `elastic-elastic-quiet-fermi`. Use a helper that prefixes only when missing — see `aws_name_for_stack` in `Elastic__AWS__Client.py`.

### Responsibility Boundaries

16. **Step__Executor** is the ONLY class that calls `page.*` Playwright methods (with `Browser__Launcher` carve-out for process lifecycle)
17. **Artefact__Writer** is the ONLY class that writes to sinks
18. **Request__Validator** contains ALL cross-schema validation
19. **Routes have no logic** — pure delegation to `Playwright__Service`

### Class / File Naming

20. **Python identifier safety** — the spec uses names like `Docker__SGraph-AI__Service__Playwright__Base` with a hyphen in `SGraph-AI`. Python identifiers cannot contain hyphens. Normalised form:
    - Class names and module names use `SGraph_AI` (underscore) — e.g. `Docker__SGraph_AI__Service__Playwright__Base`
    - Repo root and test filenames retain `SGraph-AI` where the spec is explicit (filenames allow hyphens)
21. **One class per file.** Every `Safe_*`, `Enum__*`, `Schema__*`, and `List__*` / `Dict__*` collection class lives in its own file named exactly after the class. When a module would otherwise declare multiple such classes, replace it with a same-named folder containing per-class files. Callers import from the class file directly. Registries (module-level constants + helper functions, e.g. `STEP_SCHEMAS`) are the one exception — they live in a single `*_registry.py` under `dispatcher/` because they are logic, not a schema.
22. **`__init__.py` stays empty.** Every package inside `sgraph_ai_service_playwright/` uses an empty `__init__.py`. Never re-export symbols — callers import from the fully-qualified per-class path. Never commit an empty `__init__.py` in a folder that shares a name with a sibling `.py` module: Python's import system prefers the package and every import under the module breaks.

### Human Folders — Read-Only for Agents

23. **`team/humans/dinis_cruz/briefs/`** — HUMAN-ONLY. Agents must NEVER create files there.
24. **`team/humans/dinis_cruz/debriefs/`** — HUMAN-ONLY. Agents must NEVER edit files there.
25. **Agent outputs** go to `team/humans/dinis_cruz/claude-code-web/MM/DD/HH/`

### Debrief Depth

26. **Every slice gets a debrief** under `team/claude/debriefs/`, indexed in `team/claude/debriefs/index.md`.
27. **Debriefs classify failures** using the good-failure / bad-failure convention:
    - **Good failure** — surfaced early, caught by tests, informed a better design.
    - **Bad failure** — silenced, worked around, or re-introduced. A bad failure is an implicit follow-up request.
28. **Commit hash is backfilled** into the debrief index once the Dev commit lands. The Historian chases stragglers.
29. **Session handover** — when the user says "wrap up this session" (or similar), follow [`team/claude/debriefs/SESSION_HANDOVER_GUIDE.md`](../team/claude/debriefs/SESSION_HANDOVER_GUIDE.md). It defines the required sections, naming, gathering steps, and quality bar. Don't improvise.

### Git

29. **Default branch:** `dev`
30. **Branch naming:** `claude/{description}-{session-id}`
31. **Agents never push to `dev` directly.** Open a PR from the feature branch.

---

## Testing — Non-Negotiable

1. **No mocks. No patches.** Use `register_playwright_service__in_memory()` and `in_memory_stack`-style composition.
2. **Assert on contracts** — schemas, status codes, persisted artefacts — not implementation details.
3. **Real Chromium for integration tests.** Gate on `SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE`; skip cleanly when absent.
4. **Deploy-via-pytest.** Deploy tests are numbered (`test_1__create_lambda`, `test_2__invoke__health_info`, ...) and run top-down.

Full guidance: [`library/guides/v3.1.1__testing_guidance.md`](../library/guides/v3.1.1__testing_guidance.md).

---

## Dev Pack (vault-hosted; mirrored to `library/`)

The authoritative dev pack is vault-hosted. A 2026-04-17 mirror of the dev pack lives under `library/`:

| Vault path | In-repo mirror |
|------------|----------------|
| `dev-specs/schema-catalogue-v2.md` | `library/docs/specs/v0.20.55__schema-catalogue-v2.md` |
| `dev-specs/routes-catalogue-v2.md` | `library/docs/specs/v0.20.55__routes-catalogue-v2.md` |
| `dev-specs/ci-pipeline.md` | `library/docs/specs/v0.20.55__ci-pipeline.md` |
| `guidance/*` | `library/guides/v*.md` |
| `briefing/*` | `library/briefing/v0.20.55__*.md` |
| `reference/*` | `library/reference/v0.20.55__*.md` |

If you need to re-sync from vault:

```bash
sgit clone {VAULT_KEY} /tmp/playwright-dev-pack
```

Vault key is shared out-of-band — do NOT commit it.

---

## First Session

1. `git fetch origin dev && git merge origin/dev`
2. Read `sgraph_ai_service_playwright/version`.
3. **Read [`library/catalogue/README.md`](../library/catalogue/README.md)** — fractal index of all packages, services, tests, and AWS resources. This is the fastest orientation.
4. Read the current reality doc under `team/roles/librarian/reality/`.
5. Read the role definition under `team/roles/{role}/ROLE.md` that matches your task.
6. Read the relevant debriefs under `team/claude/debriefs/`.
7. Check open briefs / plans under `team/comms/`.
8. Only then start writing code.
