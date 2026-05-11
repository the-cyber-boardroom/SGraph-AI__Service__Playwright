# Bundles and Storage Layout

This document defines the bundle artefact, its manifest schema, the sidecar contents, and the storage registry layout. Implementers should treat these schemas as authoritative — changes require a brief amendment.

---

## What a bundle is

A bundle is a captured slice of filesystem state, packaged for distribution. Concretely, a bundle is **three files** in storage:

```
manifest.json       — structured metadata, file index, hashes, dependencies
payload.tar.zst     — the actual captured file contents (zstd-compressed tar)
sidecar.zip         — documentation, tests, performance data (zip of a folder)
```

Plus a small `publish.json` that records *when, by whom, to which storage* the bundle was published — separate so it can be updated without touching the immutable triplet.

The triplet is immutable: once published at an IFD path, those bytes never change. Updates publish at a new IFD path.

---

## Manifest schema

`Schema__Bundle__Manifest` is the canonical description of a bundle's contents.

```python
class Schema__Bundle__File__Entry(Type_Safe):
    path             : Safe_Str                          # absolute, e.g. /usr/local/bin/ollama
    size_bytes       : int
    sha256           : Safe_Str
    mode             : Safe_Str                          # e.g. '0755'
    owner            : Safe_Str                          # e.g. 'root:root'
    mtime            : Safe_Str                          # ISO timestamp
    is_symlink       : bool                              = False
    symlink_target   : Safe_Str                          = ''
    xattrs           : Dict[Safe_Str, Safe_Str]          = {}

class Schema__Bundle__Manifest(Type_Safe):
    schema_version   : int                               = 1

    # Identity
    spec             : Safe_Str                          # e.g. 'vllm_disk'
    name             : Safe_Str                          # e.g. 'vllm-runtime'
    version          : Safe_Str                          # semver, e.g. '0.1.0'
    arch             : Safe_Str                          = 'x86_64'
    os               : Safe_Str                          = 'al2023'

    # Provenance
    captured_at      : Safe_Str                          # ISO timestamp
    captured_from    : Safe_Str                          # instance-id or hostname
    captured_by      : Safe_Str                          # user/agent identifier
    upstream_source  : Safe_Str                          = ''                 # 'pypi:vllm', 'docker:vllm/vllm-openai', etc.

    # Contents
    files            : List[Schema__Bundle__File__Entry]
    payload_sha256   : Safe_Str                          # sha256 of payload.tar.zst
    payload_size     : int                               # bytes of payload.tar.zst
    extracted_size   : int                               # bytes after extraction

    # Strip metadata (if applicable)
    strip_mode       : Safe_Str                          = 'none'             # 'none|debug|service|minimal'
    strip_removed    : List[Safe_Str]                    = []                 # files removed during strip
    strip_test_run   : Safe_Str                          = ''                 # reference to test run that validated this strip

    # Relationships (P21 — graph-queryable metadata, queries v2+)
    depends_on       : List[Safe_Str]                    = []                 # bundle URIs this requires
    replaces         : List[Safe_Str]                    = []                 # bundles this supersedes
    provides         : List[Safe_Str]                    = []                 # capabilities: 'http-server', 'gpu-inference'
    cve_refs         : List[Safe_Str]                    = []                 # CVE-2024-..., from upstream

    # Modules (P22 — runtime granular loading, runtime support v2+)
    modules          : List[Schema__Bundle__Module]      = []                 # see below
```

`Schema__Bundle__Module` (informational in v1, runtime-honoured in v2+):

```python
class Schema__Bundle__Module(Type_Safe):
    name             : Safe_Str
    files            : List[Safe_Str]
    is_default       : bool                              = False
```

---

## Payload: `payload.tar.zst`

The tarball contains the files declared in the manifest, organised under a synthetic root so the extraction can place them at the correct absolute paths. The conventional layout inside the tar:

```
payload.tar.zst (when uncompressed):
└── rootfs/
    └── <full absolute path of each captured file>
```

Example: if the manifest lists `/usr/local/bin/ollama`, the tar contains `rootfs/usr/local/bin/ollama`. The extractor on the target untars to `/`, dropping the `rootfs/` prefix.

Compression: zstd at level 19. Empirically a good balance for our payloads — fast to decompress, ~30% smaller than gzip. Use `python-zstandard`.

---

## Sidecar: `sidecar.zip`

The sidecar is a zip of a folder with this structure (P18):

```
sidecar/
├── SKILL.md                    Agent-readable: inputs, outputs, capabilities, failure modes
├── USAGE.md                    Human-readable: when to use, common patterns, error decoding
├── SECURITY.md                 Threat model, CVEs at capture time, hardening notes
├── ARCHITECTURE.md             Optional: data flow, component map
├── tests/
│   ├── unit/                   Tests that run on the host, no instance needed
│   ├── integration/            Tests that need a live target
│   └── end_to_end/             Tests that exercise the full workload
├── performance/
│   ├── first_load.json         P17 first_load benchmarks
│   ├── boot.json               P17 boot benchmarks
│   ├── execution.json          P17 execution benchmarks
│   └── experiments/            Other measurements
└── issues/                     Known issues, workarounds, postmortems
    └── ...
```

In v1, stub generators produce minimal SKILL.md/USAGE.md/SECURITY.md if the user hasn't supplied them. Templates:

**SKILL.md stub:**
```markdown
# SKILL: <bundle-name>

## What this bundle provides
TODO

## Inputs
TODO

## Outputs
TODO

## Failure modes
TODO

## Required preconditions
- target instance must have <X> available
- target instance must be reachable via Exec_Provider
```

**USAGE.md stub:**
```markdown
# USAGE: <bundle-name>

## When to use
TODO

## When NOT to use
TODO

## Common patterns that work
TODO

## Common patterns that fail
TODO

## Error messages decoded
TODO
```

**SECURITY.md stub:**
```markdown
# SECURITY: <bundle-name>

## Threat model
TODO

## Known CVEs at capture time
TODO

## Hardening applied
- strip mode: <mode>
```

The sidecar is a first-class artefact. Empty sidecar.zip is allowed but discouraged; CI lints for at least non-stub SKILL.md.

---

## Publish record: `publish.json`

```python
class Schema__Bundle__Publish__Result(Type_Safe):
    bundle_uri       : Safe_Str
    published_at     : Safe_Str
    published_by     : Safe_Str
    published_to     : Safe_Str                          # storage URI
    payload_sha256   : Safe_Str                          # copy from manifest for quick lookup
    sidecar_sha256   : Safe_Str
    manifest_sha256  : Safe_Str
    deregistered     : bool                              = False
    deregistered_at  : Safe_Str                          = ''
    deregistered_reason : Safe_Str                       = ''
```

This is the only file in the IFD path that gets updated (when a bundle is deregistered).

---

## Storage layout: the registry

The full storage tree (P9, P4):

```
<storage-root>/
├── catalog.json                                         ← index of all published artefacts
│
├── bundles/
│   └── <spec>/
│       └── <bundle-name>/
│           └── v0/
│               └── v0.1/
│                   └── v0.1.0/
│                       ├── manifest.json
│                       ├── payload.tar.zst
│                       ├── sidecar.zip
│                       └── publish.json
│
├── recipes/
│   └── <spec>/
│       └── <recipe-name>/
│           └── v0/
│               └── v0.1/
│                   └── v0.1.0/
│                       ├── recipe.json
│                       └── publish.json
│
└── specs/                                               ← Spec definitions (informational)
    └── <spec>/
        └── v0/
            └── ...
                └── spec.json
```

### IFD path rules

1. **Paths are immutable.** Once published, those bytes never change. Updates publish at a new IFD path.
2. **The version is encoded redundantly.** `v0/v0.1/v0.1.0/` — every level is the cumulative version up to that point. This is the IFD pattern from `SGraph-AI__Service__Playwright`. Cache-Control can be very long on any leaf path because content-at-path is by definition unchanging.
3. **Updates bump the version.** A new minor change → `v0.1.0.1` in a new folder. Old folder stays. Anyone referencing the old URI still gets the old bytes.
4. **Deregistration is metadata-only.** `publish.json` gets updated. The bundle files stay so rollback is possible.

### `catalog.json`

```json
{
  "schema_version": 1,
  "generated_at": "2026-05-11T15:20:00Z",
  "bundles": [
    {
      "spec": "vllm_disk",
      "name": "vllm-runtime",
      "version": "0.1.0",
      "uri": "s3://.../bundles/vllm_disk/vllm-runtime/v0/v0.1/v0.1.0/",
      "payload_sha256": "...",
      "published_at": "...",
      "deregistered": false
    }
  ],
  "recipes": [
    {"spec": "vllm_disk", "name": "vllm-llama3-70b", "version": "0.1.0", "uri": "...", ...}
  ]
}
```

Regenerated by `Bundle__Publisher.publish()` and `Recipe__Publisher.publish()` atomically with the publish. For `Storage__S3`, this is a `PUT`. For `Storage__Local_Disk`, an atomic rename of a temp file.

### Browsing

```
sgi storage browse
    bundles/
      vllm_disk/
        vllm-runtime/ (3 versions: 0.1.0, 0.1.1, 0.2.0)
        llama3-70b-weights/ (1 version: 0.1.0)
      ssh_file_server/
        ...

sgi storage browse bundles/vllm_disk/
    vllm-runtime/
      v0.1.0  (4.2 GB,  published 2026-05-11)
      v0.1.1  (4.1 GB,  published 2026-05-15, replaces v0.1.0)
      v0.2.0  (4.0 GB,  published 2026-05-20)
```

---

## Recipe schema

A recipe composes multiple bundles into "what to load on a fresh instance":

```python
class Schema__Recipe__Step(Type_Safe):
    name             : Safe_Str                          # step identifier
    bundle_uri       : Safe_Str                          # IFD path to the bundle
    load_options     : Dict[Safe_Str, Safe_Str]          = {}                 # extraction overrides
    test_after       : bool                              = False              # run sidecar test after this step

class Schema__Recipe(Type_Safe):
    schema_version   : int                               = 1

    spec             : Safe_Str                          # e.g. 'vllm_disk'
    name             : Safe_Str                          # e.g. 'vllm-llama3-70b'
    version          : Safe_Str                          # semver
    description      : Safe_Str                          = ''

    steps            : List[Schema__Recipe__Step]

    instance_values  : Dict[Safe_Str, Safe_Str]          = {}                 # default per-instance overrides
    required_arch    : Safe_Str                          = 'x86_64'
    required_os      : Safe_Str                          = 'al2023'
    required_capabilities : List[Safe_Str]               = []                 # e.g. ['nvidia-gpu']

    kpis             : Schema__Recipe__KPIs                                   # cold-start target, etc.
```

`Schema__Recipe__KPIs` ties to P17:

```python
class Schema__Recipe__KPIs(Type_Safe):
    first_load_p50_ms    : int                           = 60_000             # 60s
    first_load_p95_ms    : int                           = 120_000
    boot_p50_ms          : int                           = 30_000
    boot_p95_ms          : int                           = 60_000
    execution_p50_ms     : int                           = 0                  # workload-defined
    cold_start_target_ms : int                           = 120_000            # composite target
```

---

## Storage paths in code

Code never builds storage paths by string concatenation. Use the helper:

```python
class Ifd__Path__Builder(Type_Safe):
    def bundle(self, spec: str, name: str, version: str) -> Safe_Str:
        parts = version.split('.')                       # ['0', '1', '0']
        path_parts = []
        for i in range(len(parts)):
            path_parts.append('v' + '.'.join(parts[:i+1]))
        # 'v0/v0.1/v0.1.0'
        return Safe_Str(f"bundles/{spec}/{name}/{'/'.join(path_parts)}")

    def recipe(self, spec: str, name: str, version: str) -> Safe_Str:
        # similar
```

Tests verify the path builder produces stable, parseable paths. Anyone tempted to do `f"bundles/{spec}/{name}/v{version}"` should be redirected here.

---

## Sizes to expect

For sizing storage and benchmarking:

| Spec | Payload | Sidecar | Total IFD path |
|---|---|---|---|
| `ssh_file_server` | ~5 MB | ~100 KB | ~5 MB |
| `python_server` | ~80 MB | ~500 KB | ~81 MB |
| `node_server` | ~150 MB | ~500 KB | ~151 MB |
| `graphviz` | ~30 MB | ~200 KB | ~30 MB |
| `docker` | ~250 MB | ~500 KB | ~251 MB |
| `ollama_disk` | ~50 MB (binary) + ~4 GB (model bundle) | ~5 MB | ~4.05 GB across two bundles |
| `ollama_docker` | ~600 MB | ~5 MB | ~600 MB |
| `vllm_disk` | ~3 GB (runtime) + ~15 GB (model bundle) | ~10 MB | ~18 GB across two bundles |
| `vllm_docker` | ~5 GB | ~10 MB | ~5 GB |

Model weights are their own bundle (`ollama-gemma`, `llama3-70b-weights`) separate from the runtime bundle. This lets us update the runtime without re-uploading the model (P21 graph-queryable, P4 IFD versioning).
