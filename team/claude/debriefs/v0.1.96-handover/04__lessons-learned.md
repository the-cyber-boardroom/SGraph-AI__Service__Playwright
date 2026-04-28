# 04 — Lessons Learned (bugs caught + invariants locked)

## Real bugs the test suite caught

### 1. `os` folder shadowed Python stdlib `os` (Phase B step 5a)

Plan doc 4 originally specified `cli/os/`. Creating `sgraph_ai_service_playwright__cli/os/__init__.py` immediately broke 175 unit tests because every `import os` inside the package resolved to the local empty package — `os.environ.setdefault(...)` in `lambda_handler.py` died.

**Fix:** rename folder to `cli/opensearch/`. Typer aliases stay `sp os` + `sp opensearch` — only the Python folder name changed. Plan doc 4 updated with the rationale.

**Generalisation:** never name a top-level package after a Python stdlib name. Same risk for `io`, `re`, `json`, `time`, `csv`, etc.

### 2. `SG__DESCRIPTION` em-dash rejected by AWS (Phase A step 3d)

The Phase A test `test_sg_and_ami_constants::test__sg_description_is_ascii_only` immediately surfaced a U+2014 em-dash in `SG__DESCRIPTION` when it was moved into `Ec2__AWS__Client`. AWS rejects non-ASCII `GroupDescription` outright on `CreateSecurityGroup`. This bug had been silently sitting in the code (it never fired because the SG already existed when scripts ran).

**Fix:** replace em-dash with hyphen. Test locks ASCII-only via `description.encode('ascii')` round-trip.

**Generalisation:** every AWS-side string field gets an ASCII-only test.

### 3. `Safe_Str__Instance__Id` regex caught test fixture (Phase A step 3f)

`Schema__Ec2__Delete__Response.terminated_instance_ids` is a `List__Instance__Id` whose elements are `Safe_Str__Instance__Id` — regex `^i-[0-9a-f]{17}$`. A test fixture using `'i-aaa'` for brevity threw `TypeError: In Type_Safe__List: Could not convert str to Safe_Str__Instance__Id`.

**Fix:** test fixtures use realistic IDs like `'i-0123456789abcdef0'`.

**Generalisation:** Type_Safe primitives validate at construction; tests can't shortcut realistic data.

### 4. `Type_Safe__List[str]` syntax doesn't work (Phase A step 2)

I tried `image_tags : Type_Safe__List[str]` as a Type_Safe class attribute. Failed at instance construction because `Type_Safe__List.__init__` requires `expected_type` set on the subclass, not via subscript.

**Fix:** create a `List__Str(Type_Safe__List)` subclass with `expected_type = str` set as a class attribute. Use it as the field type.

**Generalisation:** `Type_Safe__List`/`Type_Safe__Dict` are NOT generic-parameterised; always subclass.

### 5. `prometheus_data` was the only volume that actually existed (Phase A step 3 / Phase C)

The v0.1.31 reality doc named `prometheus_data`, `grafana_data`, and `loki_data` named volumes. Searching the actual `provision_ec2.py` revealed only `prometheus_data` ever made it into code. Phase C plan was updated to reflect this — `grafana_data` and `loki_data` are nothing-to-drop.

**Generalisation:** trust the code over the reality doc when they disagree; reality doc gets aspirational entries.

## Invariants locked by tests

### Cross-section parity (sister sections share their shape)

- `Safe_Str__{Section}__Stack__Name.regex.pattern` — same regex across `elastic`, `opensearch`, `prometheus` (parity tests)
- `Enum__{Section}__Stack__State` — same member names + values across all sister sections (parity tests)
- `Stack__Naming(section_prefix='...')` — same class, different prefix per section

### Per-section invariants

- `OpenSearch__Compose__Template`: `bootstrap.memory_lock=true` + `memlock` ulimits (OpenSearch 2.x refuses to start without them)
- `OpenSearch__User_Data__Builder`: `vm.max_map_count=262144` set both runtime + persistent (`/etc/sysctl.d/99-sg-opensearch.conf`)
- `OpenSearch__User_Data__Builder`: `admin_password` does NOT appear — secret only flows through compose YAML (defensive test asserts `'admin_password' not in output`)
- `OpenSearch__Launch__Helper`: `MinCount=MaxCount=1` (single-node stack)
- `OpenSearch__Launch__Helper`: UserData base64-encoded (AWS rejects raw bytes)
- `Ec2__AWS__Client.SG__DESCRIPTION`: ASCII-only

### Plan / lifecycle invariants

- `aws_name_for_stack(stack_name)` never doubles the section prefix — `'opensearch-prod'` stays `'opensearch-prod'`, not `'opensearch-opensearch-prod'`
- `sg_name_for_stack(stack_name)` never starts with `sg-` (AWS reserves that for SG IDs)
- `Schema__OS__Stack__Info` never includes any `password` field (defensive: iterate `__annotations__` and assert `'password' not in field.lower()`)

## Things that surprised me

- **Observability branch active throughout.** The `lets/cf/inventory` and `lets/cf/events` work landed many commits during this session. Merge always clean. Worth syncing before each commit.
- **Type_Safe with `Optional` complications.** `Optional[Schema__OS__Stack__Info]` as return type is fine; `Optional[Type_Safe__List[X]]` is harder — preferred just `: List__Foo` (defaults to empty).
- **`from_json(json())` round-trip** is reliable across all schemas tested — no field-coercion surprises.
- **`Setup()` lazy-init** is genuinely needed — without it, `OpenSearch__Service` triggers a circular import via `OpenSearch__AWS__Client → Stack__Naming` when tests import the service first.
