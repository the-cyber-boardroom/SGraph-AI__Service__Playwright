# Appendix A — Layout Templates

Concrete templates implementers can lift directly. These are the canonical shapes for the file/folder structures described elsewhere in the pack.

---

## A.1 — Workspace folder template

A fresh workspace after `sgi init`:

```
my-workspace/
├── README.md                           ← user-edited; optional
├── state.json                          ← the only required file
├── bundles/                            ← created empty
├── recipes/                            ← created empty
├── captures/                           ← created empty
├── events/                             ← created empty
├── benchmarks/                         ← created empty
├── logs/                               ← created empty
└── strip/                              ← created empty
    ├── plans/
    └── executions/
```

### `state.json` initial content

```json
{
  "schema_version": 1,
  "workspace_name": "my-workspace",
  "created_at": "2026-05-11T14:32:00Z",
  "created_by": "user-or-agent-identifier",
  "current": null,
  "tracked": [],
  "defaults": {
    "region": "eu-west-2",
    "storage": "s3://sg-compute-sgi-artifacts-dev/",
    "exec_provider": "ssh"
  }
}
```

### `state.json` after some usage

```json
{
  "schema_version": 1,
  "workspace_name": "vllm-disk-iteration",
  "created_at": "2026-05-11T14:32:00Z",
  "created_by": "dinis",
  "current": "build-vllm-1",
  "tracked": [
    {
      "name": "build-vllm-1",
      "spec": "vllm_disk",
      "instance_id": "i-0abc123def456",
      "region": "eu-west-2",
      "added": "2026-05-11T14:35:00Z",
      "added_by_command": "sgi instance launch --spec vllm_disk",
      "connection": {
        "ssh_host": "1.2.3.4",
        "ssh_user": "ec2-user",
        "ssh_key_file": "/tmp/sgi-build-vllm-1.pem"
      }
    }
  ],
  "defaults": {
    "region": "eu-west-2",
    "storage": "s3://sg-compute-sgi-artifacts-dev/",
    "exec_provider": "ssh"
  },
  "last_operation": {
    "operation_id": "op_2026-05-11T15-22-00_capture",
    "kind": "capture",
    "started_at": "2026-05-11T15:22:00Z",
    "completed_at": "2026-05-11T15:24:32Z",
    "outcome": "success"
  }
}
```

---

## A.2 — Bundle folder layouts

### Local (in workspace)

```
workspace/bundles/
└── vllm-runtime__v0.1.0/
    ├── manifest.json
    ├── payload.tar.zst
    └── sidecar.zip
```

The local representation omits `publish.json` (only created when published).

### In Storage (IFD path)

```
<storage-root>/
└── bundles/
    └── vllm_disk/
        └── vllm-runtime/
            └── v0/
                └── v0.1/
                    └── v0.1.0/
                        ├── manifest.json
                        ├── payload.tar.zst
                        ├── sidecar.zip
                        └── publish.json
```

---

## A.3 — Sidecar zip contents

```
sidecar.zip (when extracted):
└── sidecar/
    ├── SKILL.md
    ├── USAGE.md
    ├── SECURITY.md
    ├── ARCHITECTURE.md
    ├── tests/
    │   ├── unit/
    │   │   └── test_*.py
    │   ├── integration/
    │   │   └── test_*.py
    │   └── end_to_end/
    │       └── test_*.py
    ├── performance/
    │   ├── first_load.json
    │   ├── boot.json
    │   ├── execution.json
    │   └── experiments/
    └── issues/
        └── *.md
```

---

## A.4 — Capture folder layout

```
workspace/captures/
└── 2026-05-11__143202__local-claude__build-vllm-1/
    ├── diff.json                       ← structured file-level diff
    ├── files.txt                       ← flat list of paths (grep-able)
    ├── meta.json                       ← source instance, build host, duration
    └── snapshots/                      ← optional, for incremental captures
        ├── before.txt
        └── after.txt
```

### `meta.json` shape

```json
{
  "capture_id": "2026-05-11__143202__local-claude__build-vllm-1",
  "started_at": "2026-05-11T14:32:02Z",
  "completed_at": "2026-05-11T14:38:17Z",
  "source": {
    "type": "remote",
    "instance_id": "i-0abc123",
    "instance_type": "g5.xlarge",
    "region": "eu-west-2",
    "base_ami": "ami-..."
  },
  "exec_provider": "ssh",
  "scan_root": "/",
  "exclude_patterns": ["/proc", "/sys", "/dev", "/tmp", "/var/cache"],
  "file_count": 12453,
  "total_size_bytes": 18234567890,
  "duration_seconds": 375
}
```

---

## A.5 — Events JSONL

One event per line, newline-delimited JSON:

```jsonl
{"event_id": "evt_001", "kind": "capture.started", "operation_id": "op_2026-05-11T14-32-02", "timestamp": "2026-05-11T14:32:02.123Z", "attributes": {"source": "i-0abc123"}}
{"event_id": "evt_002", "kind": "capture.scanning.before", "operation_id": "op_2026-05-11T14-32-02", "timestamp": "2026-05-11T14:32:03.456Z", "attributes": {"file_count": 8123}}
{"event_id": "evt_003", "kind": "exec.command.started", "operation_id": "op_2026-05-11T14-32-02", "timestamp": "2026-05-11T14:32:04.001Z", "attributes": {"command": "find / -type f", "target": "i-0abc123"}}
{"event_id": "evt_004", "kind": "exec.command.completed", "operation_id": "op_2026-05-11T14-32-02", "timestamp": "2026-05-11T14:32:08.234Z", "attributes": {"command": "find / -type f", "exit_code": 0, "elapsed_ms": 4233}}
```

---

## A.6 — Benchmark JSON

```json
{
  "schema_version": 1,
  "run_id": "bench_2026-05-11T15-30-00_vllm-disk",
  "spec": "vllm_disk",
  "bundle_uri": null,
  "workload": null,
  "target_type": "g5.xlarge",
  "purchase": "spot",
  "region": "eu-west-2",
  "az": "eu-west-2a",
  "started_at": "2026-05-11T15:30:00Z",
  "completed_at": "2026-05-11T15:31:32Z",
  "measurements": {
    "first_load_ms": 28400,
    "boot_ms": 24100,
    "execution_ms": 1890,
    "cold_start_ms": 88420,
    "sub_timings": {
      "ec2_run_instances": 540,
      "ec2_to_ssh_ready": 16800,
      "bundle_download_runtime": 3200,
      "bundle_download_model": 22100,
      "bundle_extract": 4800,
      "service_start": 3200,
      "first_inference": 1900
    }
  }
}
```

---

## A.7 — Recipe JSON

```json
{
  "schema_version": 1,
  "spec": "vllm_disk",
  "name": "vllm-qwen3-coder",
  "version": "0.1.0",
  "description": "vLLM disk-based serving Qwen3-Coder for local-claude",
  "steps": [
    {
      "name": "nvidia-driver",
      "bundle_uri": "s3://sg-compute-sgi-artifacts/bundles/vllm_disk/nvidia-driver/v0/v0.1/v0.1.0/",
      "load_options": {},
      "test_after": false
    },
    {
      "name": "cuda-runtime",
      "bundle_uri": "s3://sg-compute-sgi-artifacts/bundles/vllm_disk/cuda-runtime/v0/v0.1/v0.1.0/",
      "load_options": {},
      "test_after": false
    },
    {
      "name": "vllm-runtime",
      "bundle_uri": "s3://sg-compute-sgi-artifacts/bundles/vllm_disk/vllm-runtime/v0/v0.1/v0.1.0/",
      "load_options": {},
      "test_after": false
    },
    {
      "name": "qwen3-coder-weights",
      "bundle_uri": "s3://sg-compute-sgi-artifacts/bundles/vllm_disk/qwen3-coder-weights/v0/v0.1/v0.1.0/",
      "load_options": {},
      "test_after": true
    }
  ],
  "instance_values": {
    "model_name": "qwen3-coder",
    "served_port": "8000"
  },
  "required_arch": "x86_64",
  "required_os": "al2023",
  "required_capabilities": ["nvidia-gpu", "nvme-storage"],
  "kpis": {
    "first_load_p50_ms": 30000,
    "first_load_p95_ms": 45000,
    "boot_p50_ms": 30000,
    "boot_p95_ms": 60000,
    "execution_p50_ms": 2000,
    "cold_start_target_ms": 90000
  }
}
```

---

## A.8 — Manifest JSON

```json
{
  "schema_version": 1,
  "spec": "vllm_disk",
  "name": "vllm-runtime",
  "version": "0.1.0",
  "arch": "x86_64",
  "os": "al2023",
  "captured_at": "2026-05-11T14:38:17Z",
  "captured_from": "i-0abc123def456",
  "captured_by": "dinis@build-host",
  "upstream_source": "pypi:vllm==0.5.4",
  "payload_sha256": "abcd1234...",
  "payload_size": 3221225472,
  "extracted_size": 4294967296,
  "strip_mode": "none",
  "strip_removed": [],
  "strip_test_run": "",
  "depends_on": [
    "s3://.../bundles/vllm_disk/cuda-runtime/v0/v0.1/v0.1.0/",
    "s3://.../bundles/vllm_disk/nvidia-driver/v0/v0.1/v0.1.0/"
  ],
  "replaces": [],
  "provides": ["openai-api-compatible-server", "gpu-inference"],
  "cve_refs": [],
  "modules": [
    {"name": "core", "files": ["/opt/vllm/vllm/*"], "is_default": true},
    {"name": "tools", "files": ["/opt/vllm/tools/*"], "is_default": false}
  ],
  "files": [
    {
      "path": "/opt/vllm/bin/vllm",
      "size_bytes": 1024,
      "sha256": "...",
      "mode": "0755",
      "owner": "root:root",
      "mtime": "2026-05-11T14:30:00Z",
      "is_symlink": false,
      "symlink_target": "",
      "xattrs": {}
    }
  ]
}
```

---

## A.9 — Glossary of paths

| Path | What lives there | Owned by |
|---|---|---|
| `<storage-root>/catalog.json` | Index of all published bundles + recipes | `Bundle__Publisher`, `Recipe__Publisher` |
| `<storage-root>/bundles/<spec>/<name>/<ifd>/manifest.json` | Bundle manifest | `Bundle__Publisher` |
| `<storage-root>/bundles/<spec>/<name>/<ifd>/payload.tar.zst` | Bundle contents | `Bundle__Publisher` |
| `<storage-root>/bundles/<spec>/<name>/<ifd>/sidecar.zip` | Bundle metadata zip | `Bundle__Publisher` |
| `<storage-root>/bundles/<spec>/<name>/<ifd>/publish.json` | Publish record | `Bundle__Publisher` (updates supported for deregister) |
| `<storage-root>/recipes/<spec>/<name>/<ifd>/recipe.json` | Recipe definition | `Recipe__Publisher` |
| `<workspace>/state.json` | Workspace state | `Workspace__State__Manager` |
| `<workspace>/bundles/<name>__<ver>/` | Local bundle artefacts | `Bundle__Packer` |
| `<workspace>/captures/<id>/` | Capture results | `Capture__Filesystem` |
| `<workspace>/events/<id>.jsonl` | Event log per operation | `Events__Sink__JSONL` |
| `<workspace>/benchmarks/<id>.json` | Benchmark results | `Benchmark__*` |
| `<workspace>/strip/plans/<plan-id>.json` | Strip plans | `Strip__Plan__Builder` |
| `<workspace>/strip/executions/<id>/` | Strip execution records | `Strip__Executor` |

---

## A.10 — Environment variables

| Var | Used by | Purpose |
|---|---|---|
| `SGI_WORKSPACE` | All commands | Override cwd as workspace root |
| `SGI_STORAGE` | All commands | Override `defaults.storage` from state.json |
| `SGI_EXEC_PROVIDER` | All commands | Override `defaults.exec_provider` |
| `SGI_REGION` | AWS-touching commands | Override `defaults.region` |
| `SGI_QUIET` | All commands | Equivalent to `--quiet` |
| `SGI_VERBOSE` | All commands | Equivalent to `--verbose` |
| `SGI_E2E_ENABLED` | Test suite | Run E2E tests |
| `SGI_S3_TESTS_ENABLED` | Test suite | Run S3 round-trip tests |
| `SGI_GPU_TESTS_ENABLED` | Test suite | Run GPU spec tests |
| `SGI_LONG_TESTS_ENABLED` | Test suite | Run tests > 5 min |
| `SGI_ELASTIC_URL` | Events__Sink__Elasticsearch | ES endpoint |
| `SGI_ELASTIC_API_KEY` | Events__Sink__Elasticsearch | ES auth |
| `AWS_REGION` | osbot-aws | AWS region (standard) |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | osbot-aws | AWS creds (standard) |
