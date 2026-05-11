# Appendix B — Code Conventions and Idioms

These are the conventions every implementer follows. They mirror `SGraph-AI__Service__Playwright` and `SG_Send__Deploy` so anyone familiar with either codebase finds sgi immediately readable.

---

## B.1 — One class per file

Each file contains exactly one top-level class. The filename matches the class name, using double-underscores between words.

```
Word__Word__Word.py    →   class Word__Word__Word
```

Examples:
- `Bundle__Publisher.py` → `class Bundle__Publisher`
- `Storage__Local_Disk.py` → `class Storage__Local_Disk`
- `Schema__Bundle__Manifest.py` → `class Schema__Bundle__Manifest`

Helper functions, constants, and inner schemas can live in the same file IF they're only used by the top-level class. If they're used elsewhere, extract them to their own file.

## B.2 — Type_Safe everywhere

All data classes inherit from `Type_Safe` (from `osbot_utils.type_safe.Type_Safe`):

```python
from osbot_utils.type_safe.Type_Safe import Type_Safe
from osbot_utils.utils.Safe_Str       import Safe_Str

class Schema__Bundle__Manifest(Type_Safe):
    spec             : Safe_Str
    name             : Safe_Str
    version          : Safe_Str
    payload_sha256   : Safe_Str
    payload_size     : int
    files            : list                                  # typed where possible: List[Schema__Bundle__File__Entry]
```

**Never use Pydantic.** Type_Safe is the standard. It gives us:
- Strict typing with `Safe_*` primitives that validate at assignment
- Free `.json()` and `.from_json()` round-tripping
- Class-level defaults that work without `__init__` boilerplate

## B.3 — Service classes follow setup-and-use pattern

Service classes (anything with logic, not just data) follow this shape:

```python
class Bundle__Publisher(Type_Safe):
    storage           : Optional[Storage]                    = None
    events_emitter    : Optional[Events__Emitter]            = None

    def setup(self, storage: Storage,
                    events_emitter: Optional[Events__Emitter] = None) -> 'Bundle__Publisher':
        self.storage = storage
        self.events_emitter = events_emitter or Events__Emitter()
        return self

    def publish(self, request: Schema__Bundle__Publish__Request
            ) -> Schema__Bundle__Publish__Result:
        # ...
        return result
```

Convention: `setup()` returns `self` so chaining works:

```python
publisher = Bundle__Publisher().setup(storage=Storage__In_Memory().setup())
result = publisher.publish(request)
```

## B.4 — Side effects through providers only

The boundaries laid out in [02__architecture/architecture.md](../02__architecture/architecture.md) §"Side-effect boundaries" are not suggestions. If a service class wants to:

- Read a file from disk → goes through `Storage__Local_Disk`
- Read a file from S3 → goes through `Storage__S3`
- Run a command on a remote → goes through `Exec_Provider__*`
- Read live filesystem during capture → goes through `Capture__Filesystem`
- Write events → goes through `Events__Emitter`

`import boto3`, `import paramiko`, `import subprocess` outside `providers/` is a PR-blocker.

## B.5 — No mocks, no patches in tests

Tests use real in-memory provider implementations:

```python
# GOOD
def test__publish__writes_manifest(self):
    storage = Storage__In_Memory().setup()
    publisher = Bundle__Publisher().setup(storage=storage)
    result = publisher.publish(test_request())
    assert storage.exists(result.bundle_uri + 'manifest.json')

# BAD
@patch('sg_image_builder.bundle.Bundle__Publisher.storage')
def test__publish__writes_manifest(self, mock_storage):
    ...
```

`unittest.mock.patch` is not used. `pytest-mock` is not installed. If a test feels like it needs a mock, the design is wrong — the provider boundary in the wrong place.

The Twin providers (`Exec_Provider__Twin`, `Storage__In_Memory`) are real implementations that *record* what they're asked to do. Tests assert on the recording.

## B.6 — Type_Safe schemas for requests and results

Every service method takes a `Schema__*__Request` and returns a `Schema__*__Result`:

```python
class Schema__Bundle__Publish__Request(Type_Safe):
    bundle_path      : Safe_Str
    storage_uri      : Safe_Str                              = ''                 # uses workspace default if empty
    overwrite        : bool                                  = False              # immutable IFD paths normally

class Schema__Bundle__Publish__Result(Type_Safe):
    bundle_uri       : Safe_Str
    published_at     : Safe_Str
    payload_sha256   : Safe_Str
    sidecar_sha256   : Safe_Str
    manifest_sha256  : Safe_Str
    operation_id     : Safe_Str
    elapsed_ms       : float
```

Service methods never take loose `**kwargs`. Either the parameter is on the schema or it's not configurable. This is enforced — `def publish(self, **kwargs)` would fail review.

## B.7 — Naming conventions

| Prefix | What it is | Example |
|---|---|---|
| `Schema__` | Type_Safe data class, no logic | `Schema__Bundle__Manifest` |
| `Schema__Twin__Config__` | Static twin config (from boto3 / capture) | `Schema__Twin__Config__Bundle` |
| `Schema__Twin__State__` | Runtime twin state (evolves via execute) | `Schema__Twin__State__Bundle` |
| `Type__Twin__` | Alive twin with `execute()` | `Type__Twin__Bundle` |
| `<Component>__` | Service / logic class | `Bundle__Publisher`, `Capture__Filesystem` |
| `<Provider-family>__` | Provider implementation | `Storage__S3`, `Exec_Provider__SSH` |
| `Cli__` | CLI sub-app | `Cli__Bundle`, `Cli__Recipe` |
| `Renderer__` | Output renderer | `Renderer__Table`, `Renderer__JSON` |
| `Events__` | Event-related | `Events__Emitter`, `Events__Sink__JSONL` |
| `Ifd__` | IFD-path-related | `Ifd__Path__Builder` |

Method names are `snake_case`. Constants are `UPPER_SNAKE_CASE`. Type variables are `Word_Word` (PascalCase). Filenames match class names exactly.

## B.8 — Context managers for transactional operations

Operations that acquire resources (SSH connections, key pairs, security group ingress) use context managers:

```python
with EC2__Ephemeral__Launcher(spec='vllm_disk', region='eu-west-2') as launcher:
    instance_info = launcher.launch()
    exec = launcher.exec_provider()        # SSH already set up
    # do work
# leaving the with-block automatically: terminate instance, delete key pair, revoke ingress
```

Pattern lifted from `CBR__Athena__Deploy__EC2.py`. The `__enter__` does setup, `__exit__` does teardown. Failures during the body still trigger cleanup.

## B.9 — Exceptions over magic return values

Service methods raise specific exception types on failure:

```python
class SgiError(Exception):
    """Base for all sgi errors."""

class WorkspaceError(SgiError):
    """Workspace-related: not initialised, corrupted state.json, etc."""

class BundleError(SgiError):
    """Bundle integrity or validity."""

class StorageError(SgiError):
    """Storage access failed."""

class ExecError(SgiError):
    """Remote execution failed."""

class IntegrityError(SgiError):
    """sha256 mismatch, malformed manifest, etc. → exit code 4."""
```

**Never** return `('', -1)` to indicate failure. **Never** return `None` to indicate "not found" when you mean "failed to find". The local-claude bug catalogue is full of these patterns; they're banned here.

If "not found" is a normal outcome, return an optional. If it's an exceptional outcome, raise.

## B.10 — Time and IDs

```python
from osbot_utils.helpers.Time__Now import Time__Now

# Timestamps — always UTC, always ISO 8601
now_iso = Time__Now.now_iso()

# Operation IDs — time-ordered for natural sorting in logs
operation_id = f"op_{Time__Now.now_filename()}_{kind}"
# e.g. "op_2026-05-11T14-32-02_capture"
```

The `Id__Generator` class wraps these so consumers don't import `Time__Now` directly:

```python
class Id__Generator(Type_Safe):
    def operation_id(self, kind: str) -> Safe_Str:
        return Safe_Str(f"op_{Time__Now.now_filename()}_{kind}")

    def event_id(self) -> Safe_Str:
        return Safe_Str(f"evt_{Time__Now.now_filename()}_{secrets.token_hex(4)}")
```

## B.11 — Logging vs events

Two separate channels:

- **Events** — structured, machine-readable, every operation emits them, go to JSONL/Elasticsearch. The primary observability channel.
- **Logging** (Python `logging`) — text, for debug only, never relied upon for state.

Don't log instead of emitting an event. If something is worth logging, it's worth emitting as a structured event.

```python
# GOOD
self.events_emitter.emit(Schema__Event(
    kind='bundle.uploaded',
    attributes={'bundle_uri': str(uri), 'size_bytes': size},
))

# BAD
logging.info(f"Uploaded bundle to {uri}, size {size}")
```

## B.12 — Documentation in code

Docstrings on every public method. Docstrings explain *why* and *what the contract is*, not *how*:

```python
def publish(self, request: Schema__Bundle__Publish__Request
        ) -> Schema__Bundle__Publish__Result:
    """Upload a packaged bundle to Storage at its IFD path.

    The IFD path is derived from (spec, name, version) and is immutable
    once written. Attempting to publish a different bundle at the same
    path raises IntegrityError. See P4, P8.

    Updates catalog.json atomically.

    Raises:
        BundleError: bundle manifest invalid or payload sha256 mismatch
        StorageError: storage backend unavailable
        IntegrityError: a different bundle already exists at the IFD path
    """
```

No `# Args:` / `# Returns:` blocks — the type annotations carry that information.

## B.13 — File headers

Every Python file starts with imports only. No copyright headers, no docstring at the top of the file (unless it's `__init__.py` with a package-level explanation). Class-level docstrings carry the meaning.

```python
# Top of Bundle__Publisher.py:
from typing                                            import Optional
from osbot_utils.type_safe.Type_Safe                   import Type_Safe
from osbot_utils.utils.Safe_Str                        import Safe_Str

from sg_image_builder.providers.storage.Storage        import Storage
from sg_image_builder.core.events.Events__Emitter      import Events__Emitter
from sg_image_builder.schemas.bundle.Schema__Bundle__Publish__Request import Schema__Bundle__Publish__Request
from sg_image_builder.schemas.bundle.Schema__Bundle__Publish__Result  import Schema__Bundle__Publish__Result


class Bundle__Publisher(Type_Safe):
    """..."""
    ...
```

Imports are grouped: stdlib → third-party → sgi internal. Within each group, alphabetical.

## B.14 — Forbidden patterns

A non-exhaustive list of things that fail code review:

| Pattern | Why forbidden |
|---|---|
| `import boto3` outside `providers/` | P21 cloud-agnostic; goes through osbot-aws |
| `import paramiko` outside `providers/exec/` | P10 exec via providers |
| `subprocess.run(...)` outside `providers/exec/Exec_Provider__Sg_Compute.py` | Same |
| `unittest.mock.patch` | B.5 no mocks |
| `try: ... except: pass` | Errors must propagate or be explicitly logged + re-raised |
| `from pydantic import` | B.2 Type_Safe everywhere |
| `def method(self, **kwargs)` | B.6 use schemas |
| `print(...)` for output | Use the renderer system |
| Hidden filenames in workspace (`.foo`) | P13 visible files |
| Hard-coded `s3://...` URLs | Use storage factory + workspace defaults |

If you find yourself wanting to do one of these, escalate to the architect role.
