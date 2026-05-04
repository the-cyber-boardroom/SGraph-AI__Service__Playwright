# S3 Storage Node — Dev Brief (Node Spec Layer)

**version** v0.1.162
**date** 2026-05-04
**from** Developer Agent (Node Specs session)
**to** Dev
**type** Dev brief

---

## Objective

Build `sg_compute_specs/s3_server/` — the Node Spec for launching and managing
S3-server nodes.  This brief covers only the spec layer.  The server
implementation (`sg_s3_server/`) is deferred to a follow-on brief.

Architecture context: `01__architecture.md` (same folder).  Read it first.

---

## Build Order

```
Task 0 (enum patch)  →  Task 1 (enums + primitives)  →  Task 2 (schemas + collections)
                                                       ↓
                                               Task 3 (service helpers)
                                                       ↓
                                               Task 4 (orchestrator)
                                                       ↓
                                               Task 5 (routes)  →  Task 6 (manifest)
                                                       ↓
                                               Task 7 (tests)   →  Task 8 (Docker image stub)
```

Tasks 1 and 3 sub-steps are largely independent and can be parallelised within
a session.

---

## Task 0 — Add OBJECT_STORAGE capability

**Modified file:**
```
sg_compute/primitives/enums/Enum__Spec__Capability.py
```

Add one line:
```python
OBJECT_STORAGE = 'object-storage'
```

**Acceptance:** `Enum__Spec__Capability.OBJECT_STORAGE` is importable.  Extend
the existing capability enum test to assert the new value is present.

---

## Task 1 — Enums + Primitives

**New files:**
```
sg_compute_specs/s3_server/__init__.py
sg_compute_specs/s3_server/enums/__init__.py
sg_compute_specs/s3_server/enums/Enum__S3_Server__Mode.py
sg_compute_specs/s3_server/enums/Enum__S3_Server__Backend.py
sg_compute_specs/s3_server/enums/Enum__S3_Server__Stack__State.py
sg_compute_specs/s3_server/enums/Enum__S3__Handler.py
sg_compute_specs/s3_server/primitives/__init__.py
sg_compute_specs/s3_server/primitives/Safe_Str__S3_Server__Stack__Name.py
sg_compute_specs/s3_server/primitives/Safe_Str__IP__Address.py
```

### Enum__S3_Server__Mode
```python
class Enum__S3_Server__Mode(str, Enum):
    FULL_LOCAL  = 'full-local'
    FULL_PROXY  = 'full-proxy'
    HYBRID      = 'hybrid'
    SELECTIVE   = 'selective'
```

### Enum__S3_Server__Backend
```python
class Enum__S3_Server__Backend(str, Enum):
    MEMORY   = 'memory'
    DISK     = 'disk'
    VAULT    = 'vault'
    REAL_S3  = 'real-s3'
```

### Enum__S3_Server__Stack__State
Same lifecycle as docker: `PENDING / READY / TERMINATING / TERMINATED / FAILED / UNKNOWN`.

### Enum__S3__Handler
```python
class Enum__S3__Handler(str, Enum):
    LOCAL    = 'local'
    PROXY    = 'proxy'
    NOT_IMPL = 'not-impl'
```

### Safe_Str__S3_Server__Stack__Name
Regex `^[a-z][a-z0-9\-]{1,62}$`.  Same pattern as `Safe_Str__Docker__Stack__Name`.

### Safe_Str__IP__Address
Local copy (same as docker and vnc specs — each spec is self-contained).

**Acceptance:** Unit tests for regex validation on both primitives (valid, too
short, invalid chars, too long).  Tests for all enum values present.

---

## Task 2 — Schemas + Collections

**New files:**
```
sg_compute_specs/s3_server/schemas/__init__.py
sg_compute_specs/s3_server/schemas/Schema__S3_Server__Create__Request.py
sg_compute_specs/s3_server/schemas/Schema__S3_Server__Create__Response.py
sg_compute_specs/s3_server/schemas/Schema__S3_Server__Info.py
sg_compute_specs/s3_server/schemas/Schema__S3_Server__List.py
sg_compute_specs/s3_server/schemas/Schema__S3_Server__Delete__Response.py
sg_compute_specs/s3_server/schemas/Schema__S3_Server__Health__Response.py
sg_compute_specs/s3_server/collections/__init__.py
sg_compute_specs/s3_server/collections/List__Schema__S3_Server__Info.py
```

### Schema__S3_Server__Create__Request
```python
class Schema__S3_Server__Create__Request(Type_Safe):
    stack_name    : Safe_Str__S3_Server__Stack__Name
    region        : Safe_Str__AWS__Region
    instance_type : Safe_Str__Text
    from_ami      : Safe_Str__AMI__Id
    caller_ip     : Safe_Str__IP__Address
    max_hours     : int = 4
    mode          : Enum__S3_Server__Mode    = Enum__S3_Server__Mode.FULL_PROXY
    backend       : Enum__S3_Server__Backend = Enum__S3_Server__Backend.MEMORY
    aws_region_target : Safe_Str__AWS__Region   # region to proxy TO (used in FULL_PROXY/HYBRID)
```

### Schema__S3_Server__Info
```python
class Schema__S3_Server__Info(Type_Safe):
    stack_name        : Safe_Str__S3_Server__Stack__Name
    aws_name_tag      : Safe_Str__Text
    instance_id       : Safe_Str__Instance__Id
    region            : Safe_Str__AWS__Region
    ami_id            : Safe_Str__AMI__Id
    instance_type     : Safe_Str__Text
    security_group_id : Safe_Str__Text
    allowed_ip        : Safe_Str__IP__Address
    public_ip         : Safe_Str__Text
    state             : Enum__S3_Server__Stack__State = Enum__S3_Server__Stack__State.UNKNOWN
    mode              : Enum__S3_Server__Mode
    backend           : Enum__S3_Server__Backend
    s3_endpoint_url   : Safe_Str__Text    # "http://{public_ip}:9000"
    call_log_url      : Safe_Str__Text    # "http://{public_ip}:9000/call-log"
    ui_url            : Safe_Str__Text    # "http://{public_ip}:9000/ui/"
    launch_time       : Safe_Str__Text
    uptime_seconds    : int = 0
    spot              : bool = False
```

**Defensive test:** assert `Schema__S3_Server__Create__Request` has no
`aws_secret_access_key` field (no credentials in schemas — ever).

**Acceptance:** Unit tests for all schemas: default construction, field
presence, no-credential assertion.  `List__Schema__S3_Server__Info` appends
and iterates correctly.

---

## Task 3 — Service Helpers

**New files (one class per file):**
```
sg_compute_specs/s3_server/service/__init__.py
sg_compute_specs/s3_server/service/S3_Server__AWS__Client.py
sg_compute_specs/s3_server/service/S3_Server__SG__Helper.py
sg_compute_specs/s3_server/service/S3_Server__AMI__Helper.py
sg_compute_specs/s3_server/service/S3_Server__Instance__Helper.py
sg_compute_specs/s3_server/service/S3_Server__Tags__Builder.py
sg_compute_specs/s3_server/service/S3_Server__Stack__Mapper.py
sg_compute_specs/s3_server/service/S3_Server__User_Data__Builder.py
sg_compute_specs/s3_server/service/S3_Server__Launch__Helper.py
sg_compute_specs/s3_server/service/S3_Server__Health__Checker.py
sg_compute_specs/s3_server/service/Caller__IP__Detector.py
sg_compute_specs/s3_server/service/Random__Stack__Name__Generator.py
```

Mirror the docker spec helpers exactly.  Key differences only:

### S3_Server__AWS__Client
```python
S3_SERVER_NAMING = Stack__Naming(section_prefix='s3srv')
```
Tag constants: `SG__TAG__SECTION = 'sg:section'`, value `'s3-server'`.

### S3_Server__SG__Helper
Opens TCP 9000 inbound (S3 API + UI), TCP 22 inbound (restricted to caller IP
for debugging).  Never uses `sg-*` as GroupName prefix.

### S3_Server__Tags__Builder
Six tags (same as docker): `Name`, `sg:section`, `sg:stack-name`, `sg:creator`,
`sg:allowed-ip`, `sg:mode`.  Tag `sg:mode` carries `Enum__S3_Server__Mode` value.

### S3_Server__User_Data__Builder
AL2023 cloud-init.  Installs Docker CE + Compose, then:
```bash
docker run -d \
  --name sg-s3-server \
  --restart=unless-stopped \
  -p 9000:9000 \
  -e S3_SERVER_MODE="{mode}" \
  -e S3_SERVER_BACKEND="{backend}" \
  -e S3_SERVER_AWS_REGION="{aws_region_target}" \
  sgraph/s3-server:latest
```
No AWS credentials in user-data.  In `FULL_PROXY` mode the container uses the
EC2 instance's IAM role (attach `arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess`
or a tighter policy scoped to the target buckets).

PLACEHOLDERS tuple includes: `mode`, `backend`, `aws_region_target`, `max_hours`.
Test asserts no `aws_secret_access_key` or `aws_access_key` in rendered output.

### S3_Server__Stack__Mapper
boto3 instance dict → `Schema__S3_Server__Info`.  Builds `s3_endpoint_url`,
`call_log_url`, and `ui_url` from `public_ip`.  Reads `sg:mode` tag to
populate the mode field.

### S3_Server__Health__Checker
Polls `GET http://{public_ip}:9000/health` (expects `{"status": "ok"}`).
`READY` when HTTP 200; `FAILED` after timeout.  Default timeout 300 s.

### S3_Server__AMI__Helper
`latest_al2023_ami_id(region)` — identical to docker spec.  No bake-AMI
support in Phase 1.

**Acceptance:** Each helper has its own test file using a real `_Fake_*`
subclass (no mocks, no AWS).  Cover: SG create/reuse, tags never double-prefix,
user-data has no credentials, mapper builds all three URL fields correctly,
health checker returns READY on 200 and FAILED after timeout.

---

## Task 4 — Orchestrator

**New file:**
```
sg_compute_specs/s3_server/service/S3_Server__Service.py
```

```python
class S3_Server__Service(Type_Safe):
    aws_client    : object = None
    mapper        : object = None
    ip_detector   : object = None
    name_gen      : object = None
    user_data_builder : object = None
    health_checker    : object = None

    def setup(self) -> 'S3_Server__Service': ...

    def create_stack (self, request: Schema__S3_Server__Create__Request, creator='')
                                          -> Schema__S3_Server__Create__Response: ...
    def list_stacks  (self, region: str)  -> Schema__S3_Server__List: ...
    def get_stack_info(self, region, name) -> Optional[Schema__S3_Server__Info]: ...
    def delete_stack (self, region, name) -> Schema__S3_Server__Delete__Response: ...
    def health       (self, region, name, timeout_sec=300, poll_sec=10)
                                          -> Schema__S3_Server__Health__Response: ...
```

`create_stack` emits an event via `event_bus` with `type_id=Enum__Stack__Type.S3_SERVER`
(add this value to `Enum__Stack__Type` in the CLI catalog package).

**Acceptance:** Tests using a real `_Fake_S3_Server__Service` subclass that
overrides `setup()` to inject fake helpers.  Cover: create returns response
with non-empty `stack_name`; list returns empty list when no instances; delete
returns `deleted=False` when stack not found; health returns FAILED when
probe returns non-200.

---

## Task 5 — FastAPI Routes

**New files:**
```
sg_compute_specs/s3_server/api/__init__.py
sg_compute_specs/s3_server/api/routes/__init__.py
sg_compute_specs/s3_server/api/routes/Routes__S3_Server__Stack.py
```

Five endpoints, mirroring `Routes__Docker__Stack`:

| Method | Path | Handler |
|--------|------|---------|
| POST | `/api/specs/s3_server/stack` | `create_stack` |
| GET | `/api/specs/s3_server/stacks` | `list_stacks` |
| GET | `/api/specs/s3_server/stack/{name}` | `get_stack` (404 on miss) |
| DELETE | `/api/specs/s3_server/stack/{name}` | `delete_stack` |
| GET | `/api/specs/s3_server/stack/{name}/health` | `health` |

Zero logic in route handlers.  Pure delegation to `S3_Server__Service`.

**Acceptance:** TestClient tests using a real `_Fake_Service(S3_Server__Service)`
subclass (no mocks).  Cover all five routes including 404 on info miss and
health endpoint.

---

## Task 6 — Manifest

**New file:**
```
sg_compute_specs/s3_server/manifest.py
```

```python
MANIFEST = Schema__Spec__Manifest__Entry(
    spec_id               = 's3_server'                                ,
    display_name          = 'S3 Storage Server'                        ,
    icon                  = '🪣'                                        ,
    version               = '0.1.0'                                    ,
    stability             = Enum__Spec__Stability.EXPERIMENTAL         ,
    boot_seconds_typical  = 300                                        ,
    capabilities          = [Enum__Spec__Capability.OBJECT_STORAGE     ,
                              Enum__Spec__Capability.IFRAME_EMBED      ],
    nav_group             = Enum__Spec__Nav_Group.STORAGE               ,
    extends               = []                                         ,
    soon                  = False                                      ,
    create_endpoint_path  = '/api/specs/s3_server/stack'               ,
)
```

**Acceptance:** `Spec__Loader.load_all()` returns a catalogue that includes
the `s3_server` manifest.  Test that `spec_id == 's3_server'` and
`OBJECT_STORAGE in manifest.capabilities`.

---

## Task 7 — Tests

**New files:**
```
sg_compute__tests/s3_server/__init__.py
sg_compute__tests/s3_server/test_manifest.py
sg_compute__tests/s3_server/test_enums.py
sg_compute__tests/s3_server/test_primitives.py
sg_compute__tests/s3_server/test_schemas.py
sg_compute__tests/s3_server/service/test_S3_Server__Tags__Builder.py
sg_compute__tests/s3_server/service/test_S3_Server__Stack__Mapper.py
sg_compute__tests/s3_server/service/test_S3_Server__User_Data__Builder.py
sg_compute__tests/s3_server/service/test_S3_Server__Service.py
sg_compute__tests/s3_server/api/test_Routes__S3_Server__Stack.py
```

**Minimum test count:** 30 tests (same order of magnitude as docker spec).
All must pass without AWS credentials or network.

Key invariants to assert:
- `Safe_Str__S3_Server__Stack__Name` rejects `s3srv-` prefix (no double-prefix
  — the `aws_name_tag` carries the prefix, not the stack name itself).
- `Schema__S3_Server__Create__Request` has no credential fields.
- `S3_Server__User_Data__Builder` rendered output contains no credential strings.
- `S3_Server__Tags__Builder` `Name` tag never starts with `s3srv-s3srv-`.
- `Spec__Loader.load_all()` includes `s3_server`.

---

## Task 8 — Docker Image Stub

**New files:**
```
docker/s3-server/Dockerfile
docker/s3-server/requirements.txt
```

Phase 1 Dockerfile installs `sg_s3_server` from source (not yet on PyPI) and
runs uvicorn.  This is a stub — the `sg_s3_server/` package does not exist yet
when this brief ships.  The Dockerfile comments `# TODO: replace with PyPI
install once sg_s3_server is published`.

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 9000
CMD ["uvicorn", "sg_s3_server.app.Fast_API__S3_Server:app", "--host", "0.0.0.0", "--port", "9000"]
```

`requirements.txt`: `fastapi`, `uvicorn[standard]`, `osbot-utils`, `boto3`
(for proxy mode).

No CI job for this image until `sg_s3_server` exists.

---

## Constraints

Standard project rules apply (see `/.claude/CLAUDE.md`).  Key ones:

- All classes extend `Type_Safe`.  No plain classes, no Pydantic, no Literals.
- One class per file.  File name matches class name exactly.
- `__init__.py` files stay empty.
- No AWS credentials in any schema, user-data template, or committed file.
- `═══` 80-char section header in every file.
- Inline comments only; no docstrings.
- `s3srv-` is the section prefix; GroupName never starts with `sg-`.

---

## Acceptance Checklist (complete before pushing)

- [ ] `Enum__Spec__Capability.OBJECT_STORAGE` importable
- [ ] `Safe_Str__S3_Server__Stack__Name` validates correctly
- [ ] `Schema__S3_Server__Create__Request` has no credential fields
- [ ] `Schema__S3_Server__Info.s3_endpoint_url` is non-empty after mapper runs
- [ ] `S3_Server__User_Data__Builder.render()` output contains no AWS credentials
- [ ] `S3_Server__Tags__Builder` Name tag never double-prefixes
- [ ] `Routes__S3_Server__Stack` returns 404 on unknown stack name (GET + DELETE)
- [ ] `Spec__Loader.load_all()` returns manifest with `spec_id='s3_server'`
- [ ] All 30+ spec unit tests pass without AWS credentials or network
- [ ] Reality doc updated: `team/roles/librarian/reality/sg-compute/index.md`
  gains `s3_server` in the EXISTS section
