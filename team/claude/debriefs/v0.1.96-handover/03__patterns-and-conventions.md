# 03 — Patterns & Conventions Established

## Operator-mandated discipline (mid-session)

> "make those new and refactored files smaller so that changes and context use are more optimised"
>
> "remember to keep the code files smaller and single responsibility"

This drove the second half of the session. **Every new file ≤ ~100 lines. One clear concern per file.** Tests follow the same shape — one focused test file per concern.

For comparison: `Elastic__AWS__Client.py` is ~470 lines, ~20 methods, monolithic. `OpenSearch__AWS__Client` is a ~50-line composition shell that wires 4 small focused helpers, each in its own file.

## Sister-section composition pattern

```
{section}/
  primitives/             ← Safe_Str__{Section}__* (one class per file)
  enums/                  ← Enum__{Section}__* (one class per file)
  schemas/                ← Schema__{Section}__* (one class per file)
  collections/            ← List__Schema__{Section}__* (one class per file)
  service/
    {Section}__AWS__Client.py        ← composition shell + tag constants + {SECTION}_NAMING
    {Section}__SG__Helper.py         ← ensure_security_group + delete
    {Section}__AMI__Helper.py        ← latest_al2023 + latest_healthy
    {Section}__Instance__Helper.py   ← list / find / terminate
    {Section}__Launch__Helper.py     ← run_instance
    {Section}__Tags__Builder.py      ← build tag list
    {Section}__HTTP__Base.py         ← requests wrapper (verify=False, basic auth)
    {Section}__HTTP__Probe.py        ← cluster_health + ui_ready
    {Section}__Stack__Mapper.py      ← raw boto3 dict → Schema__*__Info
    {Section}__Compose__Template.py  ← docker-compose.yml renderer
    {Section}__User_Data__Builder.py ← bash boot script renderer
    {Section}__Service.py            ← Tier-1 orchestrator; setup() wires all helpers
    Caller__IP__Detector.py          ← section-local copy
    Random__Stack__Name__Generator.py ← section-local copy
  fast_api/
    routes/Routes__{Section}__Stack.py ← thin handlers; service.method().json()
  cli/
    Renderers.py                      ← Rich rendering helpers
```

Plus: `scripts/{section}.py` — typer app with 5 commands (create / list / info / delete / health). Mounted on the main `sp` app via `add_typer` with both long form (`sp opensearch`) and short alias (`sp os`).

## Test pattern: real `_Fake_*` subclasses, no mocks

CLAUDE.md is strict: no `unittest.mock`, no `MagicMock`, no `patch`. Tests compose real subclasses that override the AWS / HTTP boundary methods.

```python
class _Fake_Boto_EC2:                                    # Real class
    def __init__(self, ...): self.calls = []; ...
    def describe_instances(self, **kw):
        self.calls.append(kw)
        return {...}

class test_OpenSearch__SG__Helper(TestCase):
    def setUp(self):
        self.fake = _Fake_Boto_EC2()
        self.sg   = OpenSearch__SG__Helper()
        self.sg.ec2_client = lambda region: self.fake    # Override the seam
```

The seam is always a method (`ec2()`, `ec2_client(region)`, `request(...)`, `fetch()`) so tests can override at instance level.

## Service setup() lazy-init

Each service class has `: object = None` slots and a `setup() → self` method that lazy-imports + instantiates all helpers. Avoids circular module-loads when a caller imports the service first.

```python
class OpenSearch__Service(Type_Safe):
    aws_client : object = None
    probe      : object = None
    ...
    def setup(self) -> 'OpenSearch__Service':
        from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__AWS__Client import OpenSearch__AWS__Client
        ...
        self.aws_client = OpenSearch__AWS__Client().setup()
        ...
        return self
```

## Plan / debrief / reality-doc workflow

For every code-change commit:
1. Update `team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md` in the same commit
2. File a debrief at `team/claude/debriefs/{date}__{topic}.md`
3. Add the debrief to `team/claude/debriefs/index.md` (most recent first)
4. Plan-doc sign-off goes inline in the plan doc (not in a separate file)

## Sync discipline

Before each commit: `git fetch origin dev claude/observability-pipeline-architecture-8p9k1` and merge if anything new. The observability branch has been very active during this session — merge clean has worked every time.

## Type_Safe quirks discovered

- `Type_Safe__List[str]` syntax does NOT work — must subclass with `expected_type = str` set on the subclass. See `cli/image/collections/List__Str.py`.
- `Safe_Str__Instance__Id` regex is `^i-[0-9a-f]{17}$` — test fixtures must use real-shaped IDs like `'i-0123456789abcdef0'`, not `'i-aaa'`.
- `Schema.from_json(schema.json())` round-trip is the canonical de/serialisation test — every schema gets one.
