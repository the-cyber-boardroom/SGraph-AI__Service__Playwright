# SG/Compute — Spec Contract

## What every spec must provide

A spec is a directory under `sg_compute_specs/<name>/` containing:

```
sg_compute_specs/<name>/
  schemas/
    Schema__<Name>__Create__Request.py    ← inputs for create
    Schema__<Name>__Create__Response.py   ← what create returns
    Schema__<Name>__Info.py               ← one live node's state
    Schema__<Name>__Delete__Response.py   ← what delete returns
  service/
    <Name>__Service.py                    ← orchestrator (mandatory)
    <Name>__User_Data__Builder.py         ← assembles user-data script
    <Name>__Stack__Mapper.py              ← boto3 dict → Schema__*__Info
  cli/
    __init__.py                           ← Typer app with create/list/info/delete
    Renderers.py                          ← Rich table/panel renderers
  version                                 ← semver string, owned by the spec
```

---

## Schema__*__Create__Request — minimum fields

```python
region        : Safe_Str__AWS__Region
instance_type : Safe_Str__Text          = 't3.large'
from_ami      : Safe_Str__AMI__Id       # empty = use latest AL2023
node_name     : Safe_Str__Node__Name    # empty = auto-generated
caller_ip     : Safe_Str__IP__Address   # empty = auto-detected
max_hours     : int                     = 1
```

Spec-specific fields are added below these. For open-design that includes `api_key` and
`ollama_base_url`; for Ollama that includes `model_name`.

---

## <Name>__Service — mandatory methods

```python
def setup(self) -> '<Name>__Service':
    # wires helpers, returns self

def create_node(self, request: Schema__*__Create__Request, creator: str = '') \
        -> Schema__*__Create__Response:
    # orchestrates: resolve AMI, create SG, render user-data, run instance,
    # emit event, return response

def list_nodes(self, region: str) -> Schema__*__List:
    # DescribeInstances filtered by SpecType tag

def get_node_info(self, region: str, node_name: str) \
        -> Schema__*__Info | None:

def delete_node(self, region: str, node_name: str) \
        -> Schema__*__Delete__Response:
    # terminate instance, delete SG, emit event
```

---

## <Name>__User_Data__Builder — mandatory method

```python
def render(self, node_name: str, region: str, **spec_kwargs) -> str:
    # returns a raw (pre-gzip) bash script
    # composed from Section__* helpers + app-specific sections
```

The SDK gzip+base64 encodes the output before passing to RunInstances.
This keeps the builder testable against plain strings.

---

## CLI commands (Typer)

Each spec CLI must expose at minimum:

| Command             | Description                                        |
|---------------------|----------------------------------------------------|
| `create`            | Launch a new node; `--open` opens browser URL      |
| `list`              | Rich table of live nodes for this spec type        |
| `info <name>`       | Panel with full details for one node               |
| `delete <name>`     | Terminate node and its security group              |
| `health <name>`     | Poll until healthy or timeout                      |

Optional (spec-specific):
| `create-from-ami`   | Like create but defaults `from_ami` to baked AMI   |
| `bake-ami <name>`   | Create AMI from a running node                     |

---

## Event bus topics

Each spec emits exactly two topics via `event_bus`:

```
<spec-type>:node.created   → Schema__Node__Event
<spec-type>:node.deleted   → Schema__Node__Event
```

`Schema__Node__Event` (from `helpers/`) carries:
`type_id`, `node_name`, `region`, `instance_id`.

---

## Containerisation declaration (per spec)

Each spec service declares:

```python
container_engine      : str  = 'docker'   # 'docker' | 'podman' | 'none'
app_runs_in_container : bool = False       # True = app process inside container
```

When `container_engine != 'none'` the builder includes `Section__Docker` in user-data.
When `app_runs_in_container is True` the app section pulls and runs a container image;
otherwise the app section installs and runs the process directly on the host (but Docker/
Podman is still available for auxiliary containers such as nginx, databases, etc.).

### open-design

```python
container_engine      = 'docker'   # docker installed as baseline
app_runs_in_container = False      # Node.js daemon runs on host directly
```

Rationale: open-design has no upstream Dockerfile. The Node.js runtime has minimal
system dependencies. Running bare is simpler and avoids owning a custom Dockerfile.
nginx runs in a Docker container for HTTPS termination.

### ollama

```python
container_engine      = 'none'    # Ollama manages its own process via systemd
app_runs_in_container = False     # GPU driver binding is complex in containers
```

Rationale: Ollama's official install script sets up a systemd service; GPU passthrough
in containers on AL2023 requires additional driver configuration with limited gain.

---

## Testing contract

Every spec must have tests in `sg_compute__tests/specs/<name>/` that:

1. Test `User_Data__Builder.render()` — assert key strings are present in the output
   (no AWS calls, pure string tests)
2. Test `Stack__Mapper.to_info()` — assert schema fields map correctly from a fixture dict
3. Test `Service.create_node()` with fake helpers (no AWS calls)
4. Test `Service.delete_node()` with fake helpers

No mocks, no patches. Fakes are subclasses or simple objects with matching method signatures.
