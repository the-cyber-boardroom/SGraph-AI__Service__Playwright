# Architecture

This document describes how sgi is laid out as code and how the pieces fit together. It does **not** describe principles (see [01__principles/principles.md](../01__principles/principles.md)) or the CLI surface (see [03__cli/cli-surface.md](../03__cli/cli-surface.md)).

## Top-level repo layout

```
SG-Compute__Image-Builder/
├── LICENSE
├── README.md
├── pyproject.toml
├── requirements.txt
├── requirements-test.txt
├── humans/                              ← human briefs, mirrors SG_Send__Deploy
│   └── dinis_cruz/
│       └── briefs/
├── team/                                ← agentic team setup, mirrors SG_Send__Deploy
│   └── roles/
│       ├── conductor/
│       ├── architect/
│       ├── developer/
│       ├── devops/
│       ├── appsec/
│       └── librarian/
├── sg_image_builder/                    ← the package
│   ├── schemas/
│   ├── providers/
│   ├── core/
│   ├── capture/
│   ├── bundle/
│   ├── load/
│   ├── strip/
│   ├── test/
│   ├── benchmark/
│   ├── recipe/
│   ├── workspace/
│   ├── cli/
│   ├── consts/
│   └── version
├── sg_image_builder__tests/             ← parallel test tree
│   ├── unit/
│   ├── integration/
│   ├── end_to_end/
│   └── fixtures/
├── sg_image_builder_specs/              ← per-spec definitions
│   ├── ssh_file_server/
│   ├── python_server/
│   ├── node_server/
│   ├── graphviz/
│   ├── docker/
│   ├── ollama_disk/
│   ├── ollama_docker/
│   ├── vllm_disk/
│   └── vllm_docker/
├── scripts/                             ← maintenance scripts (build zipapp, etc.)
└── docs/                                ← user documentation
```

## Package layout (`sg_image_builder/`)

```
sg_image_builder/
├── __init__.py
├── version                              ← plain text file, e.g. "v0.1.0"
│
├── schemas/                             ← Type_Safe schemas, no logic
│   ├── twins/
│   │   ├── Schema__Twin.py              ← copied from SG_Send__Deploy
│   │   ├── Schema__Twin__Config__Bundle.py
│   │   └── Schema__Twin__State__Bundle.py
│   ├── bundle/
│   │   ├── Schema__Bundle__Manifest.py
│   │   ├── Schema__Bundle__File__Entry.py
│   │   ├── Schema__Bundle__Publish__Result.py
│   │   └── Schema__Bundle__Sidecar.py
│   ├── recipe/
│   │   ├── Schema__Recipe.py
│   │   └── Schema__Recipe__Step.py
│   ├── capture/
│   │   ├── Schema__Capture__Diff.py
│   │   └── Schema__Capture__Meta.py
│   ├── strip/
│   │   ├── Schema__Strip__Plan.py
│   │   └── Schema__Strip__Mode.py
│   ├── exec/
│   │   ├── Schema__Exec__Request.py
│   │   ├── Schema__Exec__Result.py
│   │   └── Schema__Exec__File__Transfer.py
│   ├── storage/
│   │   ├── Schema__Storage__Uri.py
│   │   └── Schema__Storage__Object__Info.py
│   ├── workspace/
│   │   ├── Schema__Workspace__State.py
│   │   └── Schema__Workspace__Tracked__Instance.py
│   └── events/
│       ├── Schema__Event.py
│       └── Schema__Event__Kind.py
│
├── types/                               ← alive twins (have execute())
│   ├── Type__Twin.py
│   └── Type__Twin__Bundle.py
│
├── providers/                           ← all infrastructure abstractions
│   ├── storage/
│   │   ├── Storage.py                   ← abstract interface
│   │   ├── Storage__S3.py               ← uses osbot-aws
│   │   ├── Storage__Local_Disk.py
│   │   ├── Storage__In_Memory.py
│   │   └── Storage__Factory.py          ← URI → Storage instance
│   ├── exec/
│   │   ├── Exec_Provider.py             ← abstract interface
│   │   ├── Exec_Provider__SSH.py        ← osbot-utils SSH helpers
│   │   ├── Exec_Provider__Sg_Compute.py ← shells out to `sg lc exec`
│   │   ├── Exec_Provider__Twin.py
│   │   └── Exec_Provider__Factory.py
│   └── aws/                             ← AWS-specific helpers (P21)
│       ├── EC2__Ephemeral__Launcher.py
│       ├── EC2__Key_Pair__Lifecycle.py
│       └── EC2__Security_Group__Ingress.py
│
├── core/                                ← cross-cutting concerns
│   ├── events/
│   │   ├── Events__Emitter.py
│   │   ├── Events__Sink.py              ← abstract
│   │   ├── Events__Sink__JSONL.py
│   │   └── Events__Sink__Elasticsearch.py
│   ├── id/
│   │   └── Id__Generator.py             ← time-ordered ids
│   └── timing/
│       └── Timing__Tracker.py           ← context manager: records elapsed_ms
│
├── workspace/                           ← state.json management
│   ├── Workspace.py
│   ├── Workspace__Init.py
│   ├── Workspace__State__Manager.py
│   └── Workspace__Resolver.py           ← cwd → workspace; current instance resolution
│
├── capture/                             ← P5 capture phase
│   ├── Capture__Filesystem.py           ← the one class allowed to read live FS during capture
│   ├── Capture__Diff.py
│   └── Capture__Manifest__Builder.py
│
├── bundle/                              ← bundle artefact lifecycle
│   ├── Bundle__Packer.py                ← tar.zst + manifest
│   ├── Bundle__Sidecar__Builder.py
│   ├── Bundle__Verifier.py
│   ├── Bundle__Publisher.py             ← → Storage
│   ├── Bundle__Resolver.py              ← ← Storage, URI → bytes
│   └── Bundle__Diff.py
│
├── load/                                ← replay onto target
│   ├── Load__Downloader.py              ← the one class allowed to read Storage during load
│   ├── Load__Extractor.py
│   └── Load__Transparent.py             ← P2 enforcement: perms, owner, xattrs
│
├── strip/                               ← P6 — substantial own package
│   ├── Strip__Analyser.py
│   ├── Strip__Plan__Builder.py
│   ├── Strip__Executor.py
│   ├── Strip__Verifier.py
│   └── modes/
│       ├── Strip__Mode.py
│       ├── Strip__Mode__None.py
│       ├── Strip__Mode__Debug.py
│       ├── Strip__Mode__Service.py
│       └── Strip__Mode__Minimal.py
│
├── test/                                ← end-to-end test runner
│   ├── Test__Suite__Runner.py
│   └── Test__Result__Reporter.py
│
├── benchmark/                           ← P17 three canonical moments
│   ├── Benchmark__First_Load.py
│   ├── Benchmark__Boot.py
│   ├── Benchmark__Execution.py
│   ├── Benchmark__Cold_Start.py         ← composite of the three
│   └── Benchmark__Reporter.py
│
├── recipe/                              ← multi-bundle composition
│   ├── Recipe__Builder.py
│   ├── Recipe__Validator.py
│   ├── Recipe__Publisher.py
│   └── Recipe__Executor.py              ← orchestrates loads + tests
│
├── cli/                                 ← typer-based CLI
│   ├── app.py                           ← top-level typer app
│   ├── Cli__Bundle.py
│   ├── Cli__Capture.py
│   ├── Cli__Recipe.py
│   ├── Cli__Instance.py
│   ├── Cli__Storage.py
│   ├── Cli__Strip.py
│   ├── Cli__Test.py
│   ├── Cli__Benchmark.py
│   ├── Cli__Spec.py
│   ├── Cli__Events.py
│   ├── Cli__Shell.py
│   ├── Cli__Connect.py
│   ├── Cli__Init.py
│   └── renderers/
│       ├── Renderer__Table.py
│       ├── Renderer__JSON.py
│       └── Renderer__Events.py
│
└── consts/
    ├── env_vars.py
    ├── paths.py
    └── ifd.py                           ← version path conventions
```

## Provider layer in detail

See [04__providers/providers.md](../04__providers/providers.md) for the full Provider API. Quick summary:

```python
# Storage interface
class Storage(Type_Safe):
    def get   (self, key: Safe_Str)              -> bytes:      ...
    def put   (self, key: Safe_Str, data: bytes) -> Schema__Storage__Object__Info: ...
    def list  (self, prefix: Safe_Str)           -> list[Schema__Storage__Object__Info]: ...
    def exists(self, key: Safe_Str)              -> bool:       ...
    def delete(self, key: Safe_Str)              -> bool:       ...

# Exec_Provider interface
class Exec_Provider(Type_Safe):
    def setup       (self)                                          -> 'Exec_Provider': ...
    def exec_command(self, req: Schema__Exec__Request)              -> Schema__Exec__Result: ...
    def copy_to     (self, transfer: Schema__Exec__File__Transfer)  -> Schema__Exec__Result: ...
    def copy_from   (self, transfer: Schema__Exec__File__Transfer)  -> Schema__Exec__Result: ...
    def wait_ready  (self, timeout_seconds: int = 60)                -> bool: ...
    def teardown    (self)                                          -> None: ...
```

## Side-effect boundaries

These boundaries are enforced by code review. Crossing them in any other class is a violation.

| Class | Is the only one that may... |
|---|---|
| `Capture__Filesystem` | Read the live filesystem during a capture |
| `Bundle__Publisher` | Write to Storage |
| `Bundle__Resolver` | Read from Storage |
| `Load__Extractor` | Write to the target instance's filesystem during load |
| `Load__Downloader` | Read Storage during a load operation (separate from publish reads) |
| `Strip__Executor` | Delete files on the target |
| `Exec_Provider__*` | Issue commands to remote instances |
| `Events__Emitter` | Write events |
| `Workspace__State__Manager` | Read/write `state.json` |

Everything else operates on `Type_Safe` schemas in memory.

## Class hierarchy: Twin pattern

Lifted from `SG_Send__Deploy`:

```
Type_Safe
│
├── Schema__Twin                                 ← base for all twin data
│   ├── Schema__Twin__Config                     ← static, immutable
│   │   └── Schema__Twin__Config__Bundle
│   └── Schema__Twin__State                      ← evolves through execute()
│       └── Schema__Twin__State__Bundle
│
└── Type__Twin                                   ← alive: has execute()
    └── Type__Twin__Bundle
        ↳ execute(action: str, **kwargs) routes to action__publish, action__verify, etc.
        ↳ never sets state.* directly outside execute() (P11)
```

A `Type__Twin__Bundle` holds the config (set once at capture time) and the state (upload status, load count, last verified at). All state transitions go through `execute()` so every change is auditable.

## Class hierarchy: CLI app composition

```
sgi (typer app)
│
├── init                ← Cli__Init.py
├── bundle              ← Cli__Bundle.py        (capture, capture-from, package, publish, list, info, load, verify, diff, deregister)
├── recipe              ← Cli__Recipe.py        (init, validate, publish, list, info, execute, diff)
├── spec                ← Cli__Spec.py          (list, info, test-suite, scaffold)
├── instance            ← Cli__Instance.py      (list, use, current, track, forget, launch, status)
├── strip               ← Cli__Strip.py         (analyse, plan, execute, verify, bake)
├── test                ← Cli__Test.py          (list, run, compare)
├── benchmark           ← Cli__Benchmark.py     (first-load, boot, execution, cold-start, report)
├── storage             ← Cli__Storage.py       (info, browse, stat, gc, migrate)
├── events              ← Cli__Events.py        (tail, query, export, kibana)
├── shell               ← Cli__Shell.py
├── connect             ← Cli__Connect.py
├── version
└── doctor
```

Each `Cli__*` is a typer sub-app. The top-level `app.py` registers them. Every command:

1. Parses args
2. Resolves the workspace (`Workspace__Resolver`)
3. Constructs services with appropriate providers injected from `state.json`
4. Calls the service method with a `Schema__*__Request`
5. Renders the `Schema__*__Result` via `Renderer__Table` or `Renderer__JSON` based on `--format`

The CLI is thin. All logic lives in service classes that are unit-testable without ever touching typer.

## Data flow: capture-package-publish-load

```
┌───────────────────────────────────────────────────────────────────┐
│ CAPTURE PHASE — runs on build host                                │
│                                                                   │
│  user runs `sgi bundle capture-from <instance>`                  │
│    ↓                                                              │
│  Cli__Bundle → Capture__Filesystem.execute(req)                  │
│    ↓                                                              │
│  Exec_Provider__SSH copies a sentinel + before-snapshot,         │
│  user runs the install, then sgi captures the diff               │
│    ↓                                                              │
│  produces Schema__Capture__Diff in workspace/captures/            │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────────┐
│ PACKAGE PHASE — local                                             │
│                                                                   │
│  user runs `sgi bundle package <capture-id>`                     │
│    ↓                                                              │
│  Bundle__Packer reads the diff + actual files (via the same      │
│  Exec_Provider that captured them), produces:                    │
│    - payload.tar.zst                                              │
│    - manifest.json (with content hashes)                          │
│    - sidecar.zip (with SKILL.md/USAGE.md stubs if not provided)  │
│  Stored in workspace/bundles/<name>__v0.1.0/                      │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────────┐
│ PUBLISH PHASE — Storage                                           │
│                                                                   │
│  user runs `sgi bundle publish <local-bundle>`                   │
│    ↓                                                              │
│  Bundle__Publisher writes to:                                     │
│    bundles/<spec>/<bundle>/v0/v0.1/v0.1.0/                       │
│      ├── manifest.json                                            │
│      ├── payload.tar.zst                                          │
│      ├── sidecar.zip                                              │
│      └── publish.json                                             │
│  Updates catalog.json                                             │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────────┐
│ LOAD PHASE — fresh target instance                                │
│                                                                   │
│  recipe executor or user runs `sgi bundle load <uri> <target>`   │
│    ↓                                                              │
│  Load__Downloader pulls payload.tar.zst from Storage             │
│  Exec_Provider copies it to the target                            │
│  Load__Extractor extracts on the target (with transparency       │
│  enforcement: perms, owner, xattrs from manifest)                 │
│  Verifies sha256s against manifest                                │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

## Workspace state model

```
state.json (visible, plain JSON):
{
  "schema_version": 1,
  "current": "compute-1",
  "tracked": [
    {"name": "compute-1",       "spec": "local_claude", "added": "..."},
    {"name": "build-vllm-disk", "spec": "vllm_disk",    "added": "..."}
  ],
  "defaults": {
    "region": "eu-west-2",
    "storage": "s3://sg-compute-artifacts-dev/",
    "exec_provider": "ssh"
  }
}
```

`Workspace__Resolver` provides:

```python
class Workspace__Resolver(Type_Safe):
    def find_workspace_root(self, cwd: Path) -> Path | None: ...
    def load_state(self)                      -> Schema__Workspace__State: ...
    def resolve_target(self, arg: str | None) -> str:
        # Rules (see Quick Reference for full text):
        # 1. arg provided → use it
        # 2. current set + live → use it
        # 3. exactly one tracked + live → use it (with announcement)
        # 4. multiple tracked + live → interactive prompt
        # 5. nothing → "no current instance; sgi instance launch first"
        ...
```

## Test architecture

Three layers, mirroring `SGraph-AI__Service__Playwright`:

| Layer | What it tests | How |
|---|---|---|
| **Unit** | A service class in isolation | In-memory providers, no IO, no AWS, no SSH. Fast: hundreds per second. |
| **Integration** | Multiple services together | `Storage__Local_Disk` + `Exec_Provider__Twin`. Real filesystem, simulated remote. |
| **End-to-end** | Full workflow on real AWS | `Storage__S3` + `Exec_Provider__SSH` against a real EC2 instance. Slow, requires creds. Gated by env var. |

Tests for `sgi spec <name>` live in `sg_image_builder_specs/<name>/tests/`, not in the main `sg_image_builder__tests/` tree. This mirrors how each spec owns its test suite (P16).

Coverage target: 90%+ on the core `sg_image_builder/` package; spec test coverage is whatever makes the spec's end-to-end suite pass.

## Dependencies

```toml
# pyproject.toml (relevant excerpts)
[project]
name = "sg-image-builder"
requires-python = ">=3.11"
dependencies = [
    "osbot-utils >= ...",      # Type_Safe, SSH helpers, Memory_FS
    "osbot-aws >= ...",         # the boto3 boundary (P21 exception list)
    "typer >= ...",             # CLI
    "rich >= ...",              # CLI rendering
    "zstandard >= ...",         # tar.zst
]

[project.optional-dependencies]
test = ["pytest", "pytest-cov", "pytest-xdist"]
dev  = ["ruff", "mypy"]

[project.scripts]
sgi = "sg_image_builder.cli.app:app"
sg-image-builder = "sg_image_builder.cli.app:app"
```

No pydantic, no boto3 direct, no requests (osbot-utils has http helpers), no flask/fastapi (sgi has no server).

## What's NOT in this architecture

Things that might seem like they should be here but aren't:

- **No FastAPI app.** sgi is CLI-only in v1. The service layer is designed so adding routes later is trivial, but routes are not in v1.
- **No database.** All state is files. `state.json` for workspace, JSONL for events, JSON for bundle manifests.
- **No background daemon.** Everything is a one-shot CLI command. Long-running workflows print progress and exit.
- **No plugin system.** Specs are registered Python packages discovered via entry points; that's the only extension mechanism.
- **No telemetry.** sgi never phones home. The event bus is local. The optional Elasticsearch sink goes to *the user's* ES instance.
