# 02 — Folder Layout and Schemas

---

## `sp linux` — folder tree

```
sgraph_ai_service_playwright__cli/linux/
├── __init__.py
├── cli/
│   ├── __init__.py
│   └── Renderers.py              # render_create, render_list, render_info, render_health
├── enums/
│   ├── __init__.py
│   └── Enum__Linux__Stack__State.py
├── primitives/
│   ├── __init__.py
│   └── Safe_Str__Linux__Stack__Name.py
├── schemas/
│   ├── __init__.py
│   ├── Schema__Linux__Create__Request.py
│   ├── Schema__Linux__Create__Response.py
│   ├── Schema__Linux__Delete__Response.py
│   ├── Schema__Linux__Health__Check.py
│   ├── Schema__Linux__Health__Response.py
│   ├── Schema__Linux__Info.py
│   └── Schema__Linux__List.py
└── service/
    ├── __init__.py
    ├── Linux__AWS__Client.py     # AWS boundary (osbot-aws only, no direct boto3)
    ├── Linux__Health__Checker.py # 4-check health logic
    ├── Linux__Instance__Helper.py# launch, terminate, SSM exec
    ├── Linux__Service.py         # pure logic — no Console, no typer
    ├── Linux__SG__Helper.py      # SG create/delete/describe
    ├── Linux__Stack__Mapper.py   # EC2 details dict → Schema__Linux__Info
    ├── Linux__Tags__Builder.py   # tag dict builder
    └── Linux__User_Data__Builder.py  # cloud-init template renderer

scripts/linux.py                  # Typer CLI surface for sp linux
```

---

## `sp docker` — folder tree

```
sgraph_ai_service_playwright__cli/docker/
├── __init__.py
├── cli/
│   ├── __init__.py
│   └── Renderers.py
├── enums/
│   ├── __init__.py
│   └── Enum__Docker__Stack__State.py
├── primitives/
│   ├── __init__.py
│   └── Safe_Str__Docker__Stack__Name.py
├── schemas/
│   ├── __init__.py
│   ├── Schema__Docker__Create__Request.py
│   ├── Schema__Docker__Create__Response.py
│   ├── Schema__Docker__Delete__Response.py
│   ├── Schema__Docker__Health__Check.py
│   ├── Schema__Docker__Health__Response.py
│   ├── Schema__Docker__Info.py
│   └── Schema__Docker__List.py
└── service/
    ├── __init__.py
    ├── Docker__AWS__Client.py
    ├── Docker__Compose__Template.py  # renders a minimal docker-compose.yml
    ├── Docker__Health__Checker.py    # 6-check health logic
    ├── Docker__Instance__Helper.py
    ├── Docker__Service.py
    ├── Docker__SG__Helper.py
    ├── Docker__Stack__Mapper.py
    ├── Docker__Tags__Builder.py
    └── Docker__User_Data__Builder.py

scripts/docker.py                 # Typer CLI surface for sp docker
```

---

## Schema field definitions

### `Schema__Linux__Create__Request`

```python
class Schema__Linux__Create__Request(Type_Safe):
    stack_name    : Safe_Str__Linux__Stack__Name   # Empty → auto-generate 'linux-{adj}-{sci}'
    region        : Safe_Str__AWS__Region           # Empty → AWS_Config session region
    instance_type : str = 't3.medium'              # Default: 2 vCPU / 4 GB (lighter than elastic's m6i.xlarge)
    caller_ip     : str = ''                        # Empty → auto-detect; set to '0.0.0.0/0' to skip SG lock
    max_hours     : int = 4                         # Auto-terminate after N hours; 0 = no auto-terminate
    extra_ports   : list = []                       # Optional TCP ports to open from caller /32 (e.g. [8080, 3000])
    ami_id        : str = ''                        # Empty → latest AL2023
```

### `Schema__Linux__Create__Response`

```python
class Schema__Linux__Create__Response(Type_Safe):
    stack_name  : Safe_Str__Linux__Stack__Name
    instance_id : str = ''
    aws_name_tag: str = ''                          # e.g. 'linux-quiet-fermi'
    region      : Safe_Str__AWS__Region
    ami_id      : str = ''
    instance_type: str = ''
    sg_id       : str = ''
    caller_ip   : str = ''
    public_ip   : str = ''                          # Empty until instance is running
    state       : Enum__Linux__Stack__State = Enum__Linux__Stack__State.PENDING
```

### `Schema__Linux__Info`

```python
class Schema__Linux__Info(Type_Safe):
    stack_name    : Safe_Str__Linux__Stack__Name
    aws_name_tag  : str = ''
    instance_id   : str = ''
    region        : Safe_Str__AWS__Region
    ami_id        : str = ''
    instance_type : str = ''
    sg_id         : str = ''
    allowed_ip    : str = ''
    public_ip     : str = ''
    state         : Enum__Linux__Stack__State = Enum__Linux__Stack__State.UNKNOWN
    launch_time   : str = ''                        # ISO-8601
    uptime_seconds: int = 0
```

### `Schema__Linux__List`

```python
class Schema__Linux__List(Type_Safe):
    region : Safe_Str__AWS__Region
    stacks : List__Schema__Linux__Info
```

### `Schema__Linux__Delete__Response`

```python
class Schema__Linux__Delete__Response(Type_Safe):
    stack_name              : Safe_Str__Linux__Stack__Name
    target                  : str = ''              # instance_id
    terminated_instance_ids : list = []
    security_group_deleted  : bool = False
```

### `Schema__Linux__Health__Check`

```python
class Schema__Linux__Health__Check(Type_Safe):
    name   : str = ''
    status : Enum__Health__Status = Enum__Health__Status.SKIP
    detail : str = ''
```

### `Schema__Linux__Health__Response`

```python
class Schema__Linux__Health__Response(Type_Safe):
    stack_name : Safe_Str__Linux__Stack__Name
    all_ok     : bool = False
    checks     : List__Schema__Linux__Health__Check
```

---

### Docker schemas — differences from Linux

`Schema__Docker__Create__Request` adds:

```python
    image         : str = ''     # Optional Docker image to pull+run (e.g. 'nginx:alpine')
    compose_spec  : str = ''     # Optional inline docker-compose YAML string
    container_port: int = 0      # Port to expose from the container (→ added to SG ingress + compose ports:)
```

`Schema__Docker__Info` adds:

```python
    image            : str = ''
    containers_running: int = 0  # from `docker ps --format json | wc -l` via SSM
```

All other schemas are structurally identical to the Linux equivalents — just
rename `Linux` → `Docker` and swap the enum type.

---

## Enum fields

### `Enum__Linux__Stack__State`

```python
class Enum__Linux__Stack__State(Enum):
    PENDING     = 'pending'
    RUNNING     = 'running'
    STOPPING    = 'stopping'
    STOPPED     = 'stopped'
    TERMINATING = 'terminating'
    TERMINATED  = 'terminated'
    UNKNOWN     = 'unknown'
```

Note: No `READY` state (unlike Elastic which waits for Kibana HTTP).  A Linux
stack is operationally useful as soon as SSM reports the instance as
"running" — no HTTP probe needed.

### `Enum__Docker__Stack__State`

Same values as Linux plus:

```python
    DOCKER_STARTING = 'docker-starting'   # Instance running but docker daemon not yet up
```

---

## Primitive fields

### `Safe_Str__Linux__Stack__Name`

Same regex as `Safe_Str__Elastic__Stack__Name` — no change needed.

```python
regex            = r'^[a-z][a-z0-9\-]{1,62}$'
allow_empty      = True
to_lower_case    = True
trim_whitespace  = True
```

`Safe_Str__Docker__Stack__Name` — identical regex, different class file (rule 21).

---

## FastAPI routes (ship alongside CLI — not a follow-up)

```
fast_api/routes/Routes__Linux__Stack.py
fast_api/routes/Routes__Docker__Stack.py
```

Each route file follows the 3-line pattern:

```python
class Route__Linux__Stack__Create(Type_Safe):
    def handle(self, body: Schema__Linux__Create__Request) -> Response:
        result = Linux__Service().setup().create(body)
        return result.json()
```

Routes to implement for v1:
- `POST /linux/stack/create`
- `GET  /linux/stack/list`
- `GET  /linux/stack/info/{stack_name}`
- `DELETE /linux/stack/delete/{stack_name}`
- `GET  /linux/stack/health/{stack_name}`

Same set for `docker/`.
