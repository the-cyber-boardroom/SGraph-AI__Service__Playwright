# Providers

Providers are the abstraction layer between sgi's service code and the outside world. Every infrastructure touch goes through a provider. Tests use twin providers; production uses real ones.

There are two provider families in v1:

- **`Storage`** — durable blob storage. Implementations: `S3`, `Local_Disk`, `In_Memory`.
- **`Exec_Provider`** — remote command execution and file transfer. Implementations: `SSH`, `Sg_Compute`, `Twin`.

A third family exists as a v2 placeholder:

- **`Events__Sink`** — where structured events go. Implementations: `JSONL` (default), `Elasticsearch`.

---

## Why this matters (the principles being enforced)

- **P1** (Storage abstracted): no `s3.*` calls in service code
- **P10** (Exec_Provider abstracted; SSH default): no `paramiko`/`subprocess` calls in service code
- **P19** (Offline-first): every operation works against `Local_Disk` + `SSH` to localhost
- **P21** (Cloud-agnostic): no AWS-specific code in core

If you find yourself writing `import boto3` or `import paramiko` outside a provider implementation, stop. The work belongs inside an existing provider, or behind a new one.

---

## Storage

### Interface

```python
# sg_image_builder/providers/storage/Storage.py

class Storage(Type_Safe):
    uri_root : Safe_Str

    def setup(self) -> 'Storage':
        raise NotImplementedError()

    def get(self, key: Safe_Str) -> bytes:
        """Get an object's bytes. Raises if not found."""
        raise NotImplementedError()

    def put(self, key: Safe_Str, data: bytes,
                   content_type: Safe_Str = 'application/octet-stream'
            ) -> Schema__Storage__Object__Info:
        """Put an object. Returns info including sha256 and size."""
        raise NotImplementedError()

    def list(self, prefix: Safe_Str = ''
            ) -> List[Schema__Storage__Object__Info]:
        """List objects with the given prefix."""
        raise NotImplementedError()

    def exists(self, key: Safe_Str) -> bool:
        raise NotImplementedError()

    def stat(self, key: Safe_Str) -> Schema__Storage__Object__Info:
        """Object metadata without fetching bytes."""
        raise NotImplementedError()

    def delete(self, key: Safe_Str) -> bool:
        raise NotImplementedError()

    def get_stream(self, key: Safe_Str) -> Iterator[bytes]:
        """Streaming download for large objects."""
        raise NotImplementedError()

    def put_stream(self, key: Safe_Str, stream: Iterator[bytes]
            ) -> Schema__Storage__Object__Info:
        """Streaming upload for large objects."""
        raise NotImplementedError()
```

### `Storage__S3` (production)

Uses `osbot_aws` for boto3 access. No direct boto3 imports in sgi code.

Key implementation notes:
- Multipart upload for files > 100 MiB
- Multipart GET with concurrency for files > 50 MiB (NIC-saturating; see the package-manager arch brief)
- SSE-S3 by default; SSE-KMS if `--kms-key` configured
- Region from workspace `state.json` defaults

### `Storage__Local_Disk`

A filesystem path that mirrors the S3 tree exactly. Same object keys = same relative paths under the root.

```
file:///mnt/sgi-registry/   →   /mnt/sgi-registry/bundles/<spec>/<name>/v0/v0.1/v0.1.0/...
```

Used for:
- Air-gap deployments (USB stick or mounted volume)
- Dev iteration (no S3 network round-trips)
- Most tests

### `Storage__In_Memory`

Dict-backed. Wipes on process exit. Used for unit tests.

### `Storage__Factory`

URI scheme → Storage instance:

```python
class Storage__Factory(Type_Safe):
    def from_uri(self, uri: Safe_Str) -> Storage:
        if uri.startswith('s3://'):     return Storage__S3       (uri_root=uri).setup()
        if uri.startswith('file://'):   return Storage__Local_Disk(uri_root=uri).setup()
        if uri.startswith('mem://'):    return Storage__In_Memory (uri_root=uri).setup()
        raise ValueError(f'Unknown storage scheme: {uri}')
```

Service code never instantiates `Storage__S3` directly. Always goes through the factory.

### `sgi storage migrate <from> <to>`

Backend-agnostic copy: any source URI to any target URI. Used to:
- Snapshot S3 to local for air-gap
- Replay from local to S3 to seed a new region
- Make a backup before a major catalog change

```python
def migrate(self, source: Storage, target: Storage):
    for info in source.list():
        target.put_stream(info.key, source.get_stream(info.key))
```

---

## Exec_Provider

### Interface

```python
# sg_image_builder/providers/exec/Exec_Provider.py

class Exec_Provider(Type_Safe):

    def setup(self) -> 'Exec_Provider':
        raise NotImplementedError()

    def wait_ready(self, timeout_seconds: int = 60) -> bool:
        """Wait until the target is reachable. SSH = port 22 open + auth works."""
        raise NotImplementedError()

    def exec_command(self, req: Schema__Exec__Request) -> Schema__Exec__Result:
        """Execute a command on the target. SYNCHRONOUS — return when done."""
        raise NotImplementedError()

    def copy_to(self, transfer: Schema__Exec__File__Transfer
            ) -> Schema__Exec__Result:
        """Copy a local file to the target."""
        raise NotImplementedError()

    def copy_from(self, transfer: Schema__Exec__File__Transfer
            ) -> Schema__Exec__Result:
        """Copy a file from the target to local."""
        raise NotImplementedError()

    def teardown(self) -> None:
        """Close connections, clean up ephemeral resources."""
        raise NotImplementedError()
```

The synchronous `exec_command` is the headline feature. It returns `Schema__Exec__Result` with `stdout`, `stderr`, `exit_code`, `elapsed_ms`, `command`. No polling, no async machinery, no `InvalidInstanceId` retries. Errors propagate as normal Python exceptions.

### `Exec_Provider__SSH` (default)

Wraps `osbot_utils.helpers.ssh.SSH`. Pattern lifted from `CBR__Athena__Deploy__SSH`:

```python
class Exec_Provider__SSH(Exec_Provider):
    ssh_host         : Safe_Str
    ssh_port         : int       = 22
    ssh_user         : Safe_Str  = 'ec2-user'
    ssh_key_file     : Safe_Str
    ssh              : Optional[SSH] = None

    def setup(self) -> 'Exec_Provider__SSH':
        self.ssh = SSH(ssh_host=str(self.ssh_host), ssh_port=self.ssh_port,
                       ssh_key_file=str(self.ssh_key_file), ssh_key_user=str(self.ssh_user))
        self.ssh.setup()
        return self

    def exec_command(self, req):
        t0 = time.perf_counter()
        with self.ssh.ssh_execute() as e:
            result = e.execute_command(str(req.command))
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        return Schema__Exec__Result(
            command   = req.command,
            stdout    = result.get('stdout', ''),
            stderr    = result.get('stderr', ''),
            exit_code = result.get('exit_code', -1),
            elapsed_ms= elapsed_ms,
        )

    def copy_to(self, transfer):
        with self.ssh.scp() as scp:
            scp.copy_file_to_host(str(transfer.local_path), str(transfer.remote_path))
        return Schema__Exec__Result(...)
```

For per-instance lifecycle (provisioning the EC2 box, scoping the SG, creating the key pair), `Exec_Provider__SSH` composes with helpers in `sg_image_builder/providers/aws/`:

- `EC2__Ephemeral__Launcher` — call `osbot-aws` `EC2_Instance.create_kwargs`, run, wait
- `EC2__Key_Pair__Lifecycle` — create per-run key, delete on teardown
- `EC2__Security_Group__Ingress` — authorize-ingress for runner IP only, revoke on teardown

Pattern lifted from `SG_Send__Deploy`'s `Operation__EC2__Ephemeral__LLM`:

```
_create_key_pair(run_id=run_id)
_authorize_ingress(runner_ip=runner_ip)
# do the build
_revoke_ingress()
_delete_key_pair()
```

### `Exec_Provider__Sg_Compute`

Shells out to `sg lc exec <name> "<command>"`. Used when sgi operates on an instance that sg-compute already manages.

```python
class Exec_Provider__Sg_Compute(Exec_Provider):
    instance_name : Safe_Str
    region        : Safe_Str

    def exec_command(self, req):
        t0 = time.perf_counter()
        result = subprocess.run(
            ['sg', 'lc', 'exec', str(self.instance_name),
             '--region', str(self.region),
             '--', str(req.command)],
            capture_output=True, text=True, timeout=req.timeout_seconds
        )
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        return Schema__Exec__Result(
            command   = req.command,
            stdout    = result.stdout,
            stderr    = result.stderr,
            exit_code = result.returncode,
            elapsed_ms= elapsed_ms,
        )
```

**This is where the sg-compute feedback list comes in.** Today `sg lc exec` outputs human-formatted text. sgi needs structured output. We try in order:

1. `sg lc exec <name> "<cmd>" --json` if the flag exists
2. Best-effort text parsing of the existing output
3. Fail with a clear error if the output is unparseable

Every fallback to (2) is a candidate item for the sg-compute team to add `--json` to. Maintain a running list at `humans/dinis_cruz/feedback-to-sg-compute.md` in the repo.

### `Exec_Provider__Twin`

In-memory. Records every call. Returns canned responses.

Pattern lifted from `SG_Send__Deploy`'s `SSH__Execute__Twin`:

```python
class Exec_Provider__Twin(Exec_Provider):
    command_log       : list      = []
    canned_responses  : dict       = {}

    def exec_command(self, req):
        self.command_log.append(req)
        cmd = str(req.command)
        if cmd in self.canned_responses:
            return self.canned_responses[cmd]
        # Best-effort default response
        return Schema__Exec__Result(command=req.command, stdout='', stderr='',
                                    exit_code=0, elapsed_ms=10)

    def set_response(self, command: str, result: Schema__Exec__Result):
        self.canned_responses[command] = result
```

Tests do:

```python
twin = Exec_Provider__Twin().setup()
twin.set_response('uname -a', Schema__Exec__Result(stdout='Linux ...', exit_code=0, ...))
service = Bundle__Publisher(exec_provider=twin, storage=Storage__In_Memory())
service.publish(...)
assert any(call.command == 'expected-command' for call in twin.command_log)
```

### Choosing a provider

```python
class Exec_Provider__Factory(Type_Safe):
    def from_workspace(self, ws: Schema__Workspace__State,
                             target: str = None) -> Exec_Provider:
        provider_name = ws.defaults.exec_provider  # 'ssh' | 'sg_compute' | 'twin'

        if provider_name == 'ssh':
            tracked = ws.find_tracked(target or ws.current)
            return Exec_Provider__SSH(
                ssh_host=tracked.connection.ssh_host,
                ssh_key_file=tracked.connection.ssh_key_file,
                ssh_user=tracked.connection.ssh_user,
            ).setup()

        if provider_name == 'sg_compute':
            return Exec_Provider__Sg_Compute(
                instance_name=target or ws.current,
                region=ws.defaults.region,
            ).setup()

        if provider_name == 'twin':
            return Exec_Provider__Twin().setup()

        raise ValueError(f'Unknown exec provider: {provider_name}')
```

CLI flags `--exec-provider` and `--region` override workspace defaults.

---

## Schemas used by providers

### `Schema__Exec__Request`

```python
class Schema__Exec__Request(Type_Safe):
    command          : Safe_Str
    cwd              : Optional[Safe_Str]   = None
    env              : Dict[Safe_Str, Safe_Str] = {}
    timeout_seconds  : int                  = 300
    user             : Optional[Safe_Str]   = None       # sudo to this user
```

### `Schema__Exec__Result`

```python
class Schema__Exec__Result(Type_Safe):
    command          : Safe_Str
    stdout           : str
    stderr           : str
    exit_code        : int
    elapsed_ms       : float
    started_at       : Safe_Str                          # ISO timestamp
```

### `Schema__Exec__File__Transfer`

```python
class Schema__Exec__File__Transfer(Type_Safe):
    local_path       : Safe_Str
    remote_path      : Safe_Str
    mode             : Optional[Safe_Str]   = None       # 'a+x' etc.
    owner            : Optional[Safe_Str]   = None       # 'ec2-user:ec2-user'
```

### `Schema__Storage__Object__Info`

```python
class Schema__Storage__Object__Info(Type_Safe):
    key              : Safe_Str
    size_bytes       : int
    sha256           : Safe_Str
    content_type     : Safe_Str
    last_modified    : Safe_Str
    storage_class    : Safe_Str             = 'STANDARD'
```

---

## Common pitfalls

**Don't construct providers in service classes.** Pass them in via `setup()` or constructor injection. Services that hard-code `Storage__S3()` are not testable.

```python
# BAD
class Bundle__Publisher(Type_Safe):
    def publish(self, ...):
        s3 = Storage__S3(uri_root='s3://...').setup()      # hard-coded
        s3.put(...)

# GOOD
class Bundle__Publisher(Type_Safe):
    storage : Optional[Storage] = None

    def setup(self, storage: Storage):
        self.storage = storage
        return self

    def publish(self, ...):
        self.storage.put(...)
```

**Don't catch and swallow provider errors.** Let them propagate. The Twin records calls and returns structured results; real providers throw structured exceptions. Either way, the caller gets information. The bug catalogue from the local-claude debriefs is full of `try/except: return ('', -1)` patterns — those are anti-patterns here.

**Don't bypass the factory.** If you have a URI, go through the factory. If you have a workspace + target, go through the factory. The factory is where the policy lives (which provider, which region, what credentials).

**Don't put provider-specific code in `core/` or service classes.** AWS-specific code lives in `providers/aws/`. If a service class needs to ask "is this an AWS provider", you've abstracted wrong.
