# 03 — Codebase map

The CLI / base classes / FastAPI surface — where to look when a task lands.

## Top-level layout

```
sgraph_ai_service_playwright/        # The runtime service (FastAPI + Playwright). Mostly stable.
sgraph_ai_service_playwright__cli/   # The `sp` CLI implementation — this is where most new work happens.
agent_mitmproxy/                     # Companion service — referenced as the "previous EC2 deployment" pattern.
scripts/                             # Tier-2A typer wrappers — one per `sp` subgroup. Thin.
tests/unit/                          # No mocks, no patches. Use _Fake_* subclasses.
tests/deploy/                        # Deploy-via-pytest. Numbered tests run sequentially.
team/                                # Roles, briefs, plans, debriefs, reality docs. Read-mostly for agents.
library/                             # Catalogue, guides, references. Read-only.
```

## The CLI Tier model

Every `sp <section>` subgroup follows the same three-tier shape:

| Tier | Role | Where it lives |
|------|------|----------------|
| **Tier 1** — pure logic | `<Section>__Service` orchestrates per-concern helpers. Lazy `setup()` wires sub-services. No I/O at construction time. | `sgraph_ai_service_playwright__cli/<section>/service/` |
| **Tier 2A** — typer CLI | `scripts/<section>.py` calls one Tier-1 method per command and renders via `Renderers`. | `scripts/` + `sgraph_ai_service_playwright__cli/<section>/cli/Renderers.py` |
| **Tier 2B** — FastAPI routes | `Routes__<Section>__*` calls the same Tier-1 method, returns `.json()` of a `Schema__*`. | `sgraph_ai_service_playwright__cli/<section>/fast_api/routes/` |

The Tier-1 service is **the only place you put business logic**. Routes are
mechanical; the typer CLI is mechanical. Reading or changing one tier
should never need you to also touch the other.

## Sister-section template (for a brand-new subgroup)

Look at any existing subgroup (`prometheus`, `opensearch`, `vnc`) for the
exact file shape. The repeating pattern under `sgraph_ai_service_playwright__cli/<section>/`:

```
primitives/    Safe_Str__*, Safe_Int__*, etc. — one class per file.
enums/         Enum__* — one per file.
schemas/       Schema__* — pure data, no methods.
collections/   List__Schema__* — pure type definition, no methods.
service/       Tier-1 service + its helpers.
cli/           Renderers (rich tables / panels) for the typer wrapper.
fast_api/      Routes__* under fast_api/routes/.
```

## Key files in the just-shipped Caddy slice

| File | What it does | When you'd touch it |
|------|--------------|---------------------|
| `vnc/service/Vnc__Caddy__Template.py` | Renders Caddyfile + Dockerfile + users.json | Branding/MFA/OIDC changes |
| `vnc/service/Vnc__Compose__Template.py` | docker-compose.yml renderer | Adding/removing containers |
| `vnc/service/Vnc__User_Data__Builder.py` | EC2 user-data bash | Boot-time setup changes |
| `vnc/service/Vnc__Service.py` | Tier-1 orchestrator | New sp vnc operations |
| `vnc/service/Vnc__HTTP__Probe.py` | Health probes | Probe surface changes |
| `vnc/service/Vnc__SG__Helper.py` | Security group ops | Network/ingress changes |
| `vnc/service/Vnc__AWS__Client.py` | AWS facade (boto3) | AWS API surface changes |
| `scripts/vnc.py` | typer wrapper for `sp vnc` | New CLI commands/flags |

## Base classes / patterns you'll hit constantly

### Type_Safe (osbot-utils)
- Every class extends `Type_Safe`. Plain Python classes are forbidden.
- Class attributes use typed primitives — never bare `str`, `int`, `list`, `dict`.
- Constructor enforces types; access raises if you set a wrong type.

### Safe_Str / Safe_Int primitives
- Most primitives in this repo subclass `Safe_Str` from osbot-utils.
- Each carries a regex (`regex = re.compile(...)`), a length bound, and
  optional `allow_empty` / `trim_whitespace`.
- Construction validates; assignment validates. Coercion is intentional
  (a `dict` set on a typed attribute will `.from_json()`).

### Enums
- `Enum__*` classes — never use Python `Literal`.
- Values are usually short lowercase strings.

### Schemas
- Pure data. No methods. No `__init__` overrides.
- Field defaults are required unless the field is genuinely optional.

### Collections
- `List__Schema__*` is a typed list. Inherits from `osbot_utils ... Type_Safe__List`.
- No methods on the collection class.

### Tests — `_Fake_*` over mocks
Every test file uses **real subclasses** that override the I/O seam:

```python
class _Fake_AWS_Client:
    def __init__(self, instance_helper):
        self.instance = instance_helper

class _Fake_Instance__Helper:
    def list_stacks(self, region): return self.world
    def find_by_stack_name(self, region, stack_name): ...
```

`unittest.mock`, `monkeypatch`, `patch` are NOT used. The seam is the
`setup()` method on the Tier-1 service — tests inject fakes after `setup()`.

## FastAPI specifics

### Fast_API__SP__CLI
The single FastAPI app that mounts every subgroup's routes. Lives at
`sgraph_ai_service_playwright__cli/fast_api/Fast_API__SP__CLI.py`. New
subgroups register here.

### The `body: dict` workaround
Pydantic schema generation chokes on Type_Safe types with nested
`Schema__*` fields. The standard workaround in this repo:

```python
def post_create(body: dict) -> Schema__Stack__Create__Response:
    request = Schema__Stack__Create__Request.from_json(body)
    return service.create_stack(request)
```

Used in `Routes__Prometheus__Stack`, `Routes__Vnc__Stack__Create` (when wired).

### Tests for routes
Use `Fast_API__Test__Client` from osbot-fast-api-serverless. Compose the
in-memory stack via `register_<section>_service__in_memory()` helpers.
See `tests/unit/sgraph_ai_service_playwright__cli/prometheus/fast_api/routes/`
for working examples.

## Patterns to AVOID (these will get caught in review)

- `unittest.mock` / `@patch` / `monkeypatch` — use `_Fake_*` subclasses.
- Pydantic — never. We use `Type_Safe` exclusively.
- `Literal[...]` — use `Enum__*`.
- Re-exports in `__init__.py` — `__init__.py` files stay empty; import from the
  fully-qualified per-class path.
- Docstrings — never. Inline comments only, and only when the WHY is non-obvious.
- `boto3` direct calls — go through `osbot-aws` or the section's
  `<Section>__AWS__Client` facade. The narrow exception is the
  Lambda-Function-URL two-statement permission fix in `provision_lambdas.py`.
- `:latest` Docker tags — pin everything (we hit moving-tag bugs in this
  session: mitmproxy, caddy).
- Adding `__init__.py` files under `tests/` — they break PyCharm + pytest interop. We removed all 52 of them in commit `0aa9b4a`.

## How to run tests fast

```bash
# Single section
pytest tests/unit/sgraph_ai_service_playwright__cli/vnc/ -q

# Whole unit suite (skip the cryptography-dep file that pre-existing breaks)
pytest tests/unit/ --ignore=tests/unit/agent_mitmproxy/test_Routes__CA.py -q

# Single test class
pytest tests/unit/sgraph_ai_service_playwright__cli/vnc/service/test_Vnc__Service.py::test_create_stack -q
```

The pytest binary is at `/tmp/venv-sp/bin/pytest` in this Claude Code env.
