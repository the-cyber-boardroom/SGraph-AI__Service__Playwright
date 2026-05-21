---
title: "B1 — TUI API contract + registry + CLI + first provider"
file: 01__B1-contract-and-registry.md
author: Architect (Claude)
date: 2026-05-21 (UTC hour 15)
repo: SGraph-AI__Service__Playwright @ claude/review-tui-cli-commits-S3xCM (v0.2.36 line)
status: PLAN — the keystone slice. Pure (3.11), no Textual. Ships as the `sg <area> tui api` CLI.
parent: 00__plans-index.md
---

# B1 — contract + registry + CLI + first provider

**Goal.** Stand up the TUI API contract as Type_Safe classes, a registry, the
`sg <area> tui api` CLI surface, JSON-Schema-from-Type_Safe, and **one real read-only
provider** (`sg aws s3`). All pure, fully unit-tested on 3.11, no Textual, no mutations.
After B1 a human/agent can do `sg aws s3 tui api list/describe/skills/invoke` end-to-end.

**Non-goals (later slices).** SG/Role enforcement (B2), the execution center / dry-run /
sequencing (B3), VFS (B4), the chat tool loop (C). B1's `invoke` calls the provider directly
(read-only only) — the execution center wraps it in B3.

---

## Files to create

All under the shared lib `sgraph_ai_service_playwright__cli/tui/tool_api/` (one class per file):

```
tui/tool_api/
  enums/
    Enum__Tui_Api__Tier.py            READ_ONLY · WRITE · CRUD · DESTRUCTIVE
  schemas/
    Schema__Tui_Api__Scope.py         api · capability · resource='*'   (string form {api}:{cap}[:{res}])
    Schema__Tui_Api__Action.py        name·description·input_schema·output_schema·tier·scope·idempotent·emits
    Schema__Tui_Api__Event.py         name·description·payload_schema
    Schema__Tui_Api__Skills.py        human·api·driver  (markdown refs/text)
    Schema__Tui_Api__Manifest.py      slug·tool·name·version·description·tiers·actions·events·skills·children
    Schema__Tui_Api__Result.py        ok·data·error                     (dry_run/preview/cost added in B3)
    List__Tui_Api__Action.py · List__Tui_Api__Event.py · List__Tui_Api__Scope.py
  service/
    Tui_Api__Schema__Builder.py       wraps Type_Safe__Schema_For__LLMs; params-class -> input_schema dict
    Tui_Api__Provider.py              the seam (base class; subclass per host)
    Tui_Api__Registry.py             register(provider) / get(slug) / list_slugs() / manifest_all()
  cli/
    Cli__Tui_Api.py                   make_tui_api_app(registry) -> typer.Typer  (list/describe/skills/state/invoke)
  tests/
    test_Tui_Api__Schema__Builder.py
    test_Tui_Api__Registry.py
    test_Cli__Tui_Api.py
```

Plus the first provider, co-located with the host it exposes:

```
aws/s3/tui_api/
  schemas/
    Schema__S3__Params__List_Objects.py   bucket: Safe_Str__S3__Bucket · prefix: Safe_Str__S3__Prefix = '' · recursive: bool = False
    Schema__S3__Params__Head_Object.py     bucket · key: Safe_Str__S3__Key
  S3__Tui_Api__Provider.py                 manifest() + dispatch() over S3__AWS__Client
  skills/ SKILL-human.md · SKILL-api.md · SKILL-driver.md
  tests/ test_S3__Tui_Api__Provider.py     (uses S3__AWS__Client__In_Memory — no mocks)
```

---

## Key shapes

```python
# Enum__Tui_Api__Tier
class Enum__Tui_Api__Tier(Enum):
    READ_ONLY = 'read_only'; WRITE = 'write'; CRUD = 'crud'; DESTRUCTIVE = 'destructive'

# Schema__Tui_Api__Scope                    (pure data)
class Schema__Tui_Api__Scope(Type_Safe):
    api        : Safe_Str__Tui_Api__Slug      # 'sg-aws.s3'   (new Safe_Str; dotted slug)
    capability : Safe_Str__Tui_Api__Capability # 'read' | 'write' | 'list_objects' | '*'
    resource   : str = '*'
    # token string = f'{api}:{capability}:{resource}'  — used by SG/Role in B2

# Schema__Tui_Api__Action
class Schema__Tui_Api__Action(Type_Safe):
    name         : Safe_Str__Tui_Api__Action_Name
    description  : str
    input_schema : dict                       # from Tui_Api__Schema__Builder (real JSON Schema)
    output_schema: dict
    tier         : Enum__Tui_Api__Tier
    scope        : Schema__Tui_Api__Scope
    idempotent   : bool = True
    emits        : List__Tui_Api__Event_Name
    # preconditions / privileges / supports_dry_run / est_cost_usd are ADDED in B2/B3

# Tui_Api__Schema__Builder                  (the decision-#9 wiring)
class Tui_Api__Schema__Builder(Type_Safe):
    def input_schema(self, params_cls) -> dict:
        from osbot_utils.helpers.llms.actions.Type_Safe__Schema_For__LLMs import Type_Safe__Schema_For__LLMs
        return Type_Safe__Schema_For__LLMs().export(params_cls)

# Tui_Api__Provider                         (the seam; B1 subset — extended in B3/brief surfaces)
class Tui_Api__Provider(Type_Safe):
    def manifest(self)               -> Schema__Tui_Api__Manifest : raise NotImplementedError
    def skills(self)                 -> dict                      : return {}     # {human,api,driver}
    def state(self)                  -> dict                      : return {}     # outbound 'state' (brief 1)
    def dispatch(self, action: str, params: dict) -> Schema__Tui_Api__Result: raise NotImplementedError

# Tui_Api__Registry
class Tui_Api__Registry(Type_Safe):
    providers : Dict[str, Tui_Api__Provider]      # slug -> provider
    def register(self, provider): self.providers[str(provider.manifest().slug)] = provider
    def get(self, slug)        : return self.providers.get(slug)
    def list_slugs(self)       : return sorted(self.providers)
```

`Safe_Str__Tui_Api__Slug` / `…Capability` / `…Action_Name` / `…Event_Name` are new
primitives under `tui/tool_api/primitives/` (lowercase + dot/underscore; deny spaces) — keeps
rule 2 (zero raw primitives).

---

## The S3 provider (the proof it's real)

```python
class S3__Tui_Api__Provider(Tui_Api__Provider):
    client  : S3__AWS__Client                 # inject S3__AWS__Client__In_Memory in tests
    builder : Tui_Api__Schema__Builder

    def manifest(self):
        return Schema__Tui_Api__Manifest(
            slug='sg-aws.s3', tool='sg-aws', name='S3 (read-only)', version='0.1.0',
            tiers=[Enum__Tui_Api__Tier.READ_ONLY],
            actions=[
              Schema__Tui_Api__Action(name='list_buckets', tier=READ_ONLY,
                  scope=Schema__Tui_Api__Scope(api='sg-aws.s3', capability='read'),
                  input_schema={}),
              Schema__Tui_Api__Action(name='list_objects', tier=READ_ONLY,
                  scope=Schema__Tui_Api__Scope(api='sg-aws.s3', capability='read'),
                  input_schema=self.builder.input_schema(Schema__S3__Params__List_Objects)),
              Schema__Tui_Api__Action(name='head_object', tier=READ_ONLY,
                  scope=Schema__Tui_Api__Scope(api='sg-aws.s3', capability='read'),
                  input_schema=self.builder.input_schema(Schema__S3__Params__Head_Object)),
            ])

    def dispatch(self, action, params):
        if action == 'list_buckets': data = [b.json() for b in self.client.list_buckets()]
        elif action == 'list_objects': data = self.client.list_objects(**params).json()
        elif action == 'head_object' : data = self.client.head_object(**params).json()
        else: return Schema__Tui_Api__Result(ok=False, error=f'unknown action {action}')
        return Schema__Tui_Api__Result(ok=True, data={'result': data})
```

Params are validated by constructing the Type_Safe params class from `params` before the
call (Type_Safe rejects bad input) — deterministic, no hand-rolled validation.

---

## CLI — `sg <area> tui api` (the `tui`-becomes-a-group change)

`tui` is a leaf command today. Convert `register_tui` so `tui` is a sub-group that still
launches on bare `sg … tui`, and hosts `api`:

```python
# generic, in tui/tool_api/cli/Cli__Tui_Api.py
def make_tui_api_app(registry: Tui_Api__Registry) -> typer.Typer:
    app = typer.Typer(name='api', help='TUI API: discover + invoke this area\'s actions.', no_args_is_help=True)
    @app.command('list')
    def list_(): ...                 # registry.list_slugs() + action names
    @app.command('describe')
    def describe(slug: str = typer.Argument(None), json_: bool = typer.Option(False,'--json')): ...
    @app.command('skills')
    def skills(slug: str, audience: str = typer.Argument('api')): ...
    @app.command('state')
    def state(slug: str): ...
    @app.command('invoke')
    def invoke(slug: str, action: str, params: str = typer.Option('{}','--params')):
        result = registry.get(slug).dispatch(action, json.loads(params))   # B3 routes via execution center
        typer.echo(json.dumps(result.json(), indent=2))
    return app

# per host (rewrite of register_tui in Cli__Bedrock__Chat__Tui.py, and a new one for s3):
def register_tui(parent_app: typer.Typer) -> None:
    tui_app = typer.Typer(name='tui', invoke_without_command=True, no_args_is_help=False)
    @tui_app.callback()
    def _launch(ctx: typer.Context, model: str = typer.Option('default','-m','--model'), ...):
        if ctx.invoked_subcommand is None:
            run_tui(model=model, ...)            # bare `sg … tui` still launches
    tui_app.command('diagnose')(lambda: run_diagnose())
    tui_app.add_typer(make_tui_api_app(_build_registry()), name='api')
    parent_app.add_typer(tui_app, name='tui')
```

For B1 the first wiring target is **`sg aws s3 tui api …`**. Note: s3's Textual UI is the
**`browse`** command — there is **no `tui` group on s3 today** — so adding `tui api` introduces
a fresh `tui` group containing only `api`, with **no existing `tui` launch to preserve** (s3's
`browse` can be re-homed under `tui` later, as a separate cleanup). The bedrock `tui`→group
conversion — which *does* have a launch to preserve (`@app.command('tui')`) — is deferred to
C-P0 (when the chat gains its provider). Result B1 delivers:

```
sg aws s3 tui api list
sg aws s3 tui api describe sg-aws.s3 --json
sg aws s3 tui api skills sg-aws.s3 api
sg aws s3 tui api invoke sg-aws.s3 list_objects --params '{"bucket":"my-bucket","prefix":"logs/"}'
```

---

## Tests (no mocks, 3.11)

- `test_Tui_Api__Schema__Builder` — `input_schema(Schema__S3__Params__List_Objects)` returns
  a JSON Schema with `properties.bucket.type=='string'`, `prefix` present, `recursive` boolean,
  `required==['bucket']`. (Asserts the osbot emitter is wired, not its internals.)
- `test_Tui_Api__Registry` — register the S3 provider; `get('sg-aws.s3')` returns it;
  `list_slugs()` contains it; `manifest_all()` validates.
- `test_S3__Tui_Api__Provider` — build with `S3__AWS__Client__In_Memory().add_bucket('b').add_object('b','k',b'…')`;
  `dispatch('list_objects', {'bucket':'b'})` returns `ok==True` and the object key in `data`;
  unknown action → `ok==False`; bad params (missing bucket) → Type_Safe raises, asserted.
- `test_Cli__Tui_Api` — Typer `CliRunner`: `invoke list` lists `sg-aws.s3`; `invoke describe`
  emits valid JSON; `invoke … list_objects --params` returns the in-memory object. Registry
  built with the in-memory client via a test factory seam (mirror `_engine_factory`).

---

## Acceptance (B1 done-when)

1. `sg aws s3 tui api list/describe/skills/invoke` work end-to-end against real S3 creds **and** the in-memory client in tests.
2. Every action's `input_schema` is **derived** (no hand-written JSON); `describe --json` shows real JSON Schema with `required`.
3. The registry is the single source of truth — the CLI reads exactly what a provider declares.
4. SKILL-{human,api,driver}.md exist for the S3 provider and name every action.
5. Pure: the whole slice imports no Textual and runs on 3.11; full unit coverage; no mocks.
6. `tui` is a Typer group (bare launch preserved where a TUI exists; `api` attached).

## Effort / risk

- **Effort:** ~1–1.5 days. The schema emitter + S3 client + in-memory double already exist, so most work is the contract classes + CLI wiring + tests.
- **Risk — `tui` group conversion** could change the bare-`tui` launch UX. Mitigate: `invoke_without_command=True` + callback; pilot the bedrock launch still works (defer the bedrock conversion to C-P0; do s3 first where there's no launch to break).
- **Risk — osbot emitter output shape** differs slightly from Bedrock's `inputSchema` expectations. Mitigate: B1 only needs valid JSON Schema for `describe`; the Bedrock-specific massaging is C-TL2.

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
