# Quick Reference

One-page distillation of sgi's concepts and vocabulary. Keep this open while reading the rest of the pack.

## Core vocabulary

| Term | Definition |
|---|---|
| **Bundle** | A captured slice of filesystem state, stored as `payload.tar.zst` + `manifest.json` + sidecar. The unit of distribution. |
| **Sidecar** | Per-bundle metadata: `SKILL.md`, `USAGE.md`, `SECURITY.md`, `tests/`, `performance/`. Stored alongside the bundle in Storage. |
| **Recipe** | Ordered list of bundle references + per-instance values. The unit of "what to load on an instance". |
| **Spec** | Named use case (e.g. `ssh_file_server`, `vllm_disk`). Owns a recipe template, a test suite, and KPIs. |
| **Workspace** | A folder on the user's disk that holds the state for one logical sgi context. Contains `state.json`, `bundles/`, `recipes/`, `captures/`, `events/`, `benchmarks/`, `logs/`. |
| **Provider** | Abstract interface with multiple concrete implementations. Examples: `Storage` (S3/local-disk/in-memory), `Exec_Provider` (SSH/sg-compute/twin). |
| **IFD path** | Iterative Flow Development versioning: `<root>/<spec>/<bundle>/v0/v0.1/v0.1.0/`. Each path is immutable once published. |

## Vocabulary that is NOT sgi's

| Term | Where it lives |
|---|---|
| `sgit` / vault | The user's tool for versioning workspace folders. sgi never invokes it. |
| AMI / EBS snapshot | AWS concepts. sgi works *because* it avoids them. |
| Docker image | Different concept. A bundle may contain a `docker save`d image as one of its files, but a bundle is not a Docker image. |
| Package / package manager | The layer above sgi. sgi is the image-building primitive that a package manager would use. |

## The seven core verbs

```
capture   → record filesystem changes during an install on a build host
package   → turn a capture into a bundle (tar.zst + manifest + sidecar)
publish   → upload a bundle to Storage at its IFD-versioned path
load      → pull a bundle from Storage onto a target instance; replay
strip     → remove files not exercised by the spec's test suite
test      → run the spec's end-to-end test suite against a target
benchmark → measure first-load, boot, execution (three canonical moments)
```

## The three canonical performance moments

| Moment | Measures | Why |
|---|---|---|
| **First load** | Time from "bundle not present" to "bundle on disk" | Cold-start cost: download + extract |
| **Boot time** | Time from "bundle on disk" to "service ready" | Warm-start cost: process init |
| **Execution** | Time per operation once running | Steady-state cost: actual work |

## The four strip modes

| Mode | What's removed | Use case |
|---|---|---|
| `none` | Nothing | Baseline measurement |
| `debug` | Docs, man pages, build caches | Easy 200–300 MB win |
| `service` | Everything not needed for boot + service + diagnose/ssh | Practical production default |
| `minimal` | Everything not exercised by end-to-end tests, including ssh server if absent from tests | Maximum hardening |

## The seven v1 principles that matter most

(Full list of 21 in [01__principles/principles.md](../01__principles/principles.md))

1. **Storage abstracted** — never `s3.*` in service code
2. **Capture, don't construct** — observe a real install, don't write installer scripts
3. **Tests are the contract** — strip removes anything tests don't require
4. **IFD versioning** — paths are immutable; updates publish new paths
5. **Workspace folder is the unit of context** — no global state, no hidden files
6. **Cloud-agnostic** — no AWS-specific code in core; AWS lives behind providers
7. **Offline-first** — every operation works without internet given a local Storage backend

## The nine v1 specs

In implementation order (CPU first, GPU last):

| # | Spec | Tests "works" by |
|---|---|---|
| 1 | `ssh_file_server` | SSH in, create/read/delete a file |
| 2 | `python_server` | HTTP server returns hello-world |
| 3 | `node_server` | Same, Node.js |
| 4 | `graphviz` | Single-action: dot file in, PNG out |
| 5 | `docker` | `docker run hello-world` works |
| 6 | `ollama_disk` | Ollama binary on disk, model on disk, `/api/generate` responds |
| 7 | `ollama_docker` | Same in a container |
| 8 | `vllm_disk` | GPU only — vLLM serving with the working flag set |
| 9 | `vllm_docker` | Current local-claude path, just fast |

Each level proves new primitives. Numbers 1–7 are CPU; 8–9 are GPU.

## The two execution providers

| Provider | Mechanism | When to use |
|---|---|---|
| `Exec_Provider__SSH` | osbot-utils SSH helpers; sync commands | **Default.** Fresh-build workflows where sgi launches the build instance itself |
| `Exec_Provider__Sg_Compute` | Shells out to `sg lc exec` | Dog-food workflows where sgi operates on an sg-compute-managed instance |
| `Exec_Provider__Twin` | In-memory; records calls; returns canned responses | All tests |

**SSH is the default** because:
- Synchronous (no SSM polling, no `InvalidInstanceId` retries)
- Cloud-agnostic (works on any host with port 22 open)
- ~50× faster per-command than SSM (sub-100ms vs 1.5–3s)
- Works offline / air-gap

## Workspace folder layout

```
my-workspace/
├── state.json                          ← current instance, tracked list, defaults
├── bundles/
│   └── <bundle>__v0.1.0/
│       ├── manifest.json
│       └── payload.tar.zst
├── recipes/
│   └── <recipe>__v0.1.0.json
├── captures/
│   └── 2026-05-11__143202__local-claude/
│       ├── diff.json
│       ├── files.txt
│       └── meta.json
├── events/
│   └── 2026-05-11__143202__capture.jsonl
├── benchmarks/
│   └── 2026-05-11__cold-start__vllm-disk.json
├── logs/
│   └── 2026-05-11__143202__capture.log
└── README.md                           ← optional, user-edited
```

All files are visible (no leading dots). The user can `sgit init` this folder if they want vault versioning; sgi doesn't care.

## Storage layout (S3 / local-disk / any backend)

```
<storage-root>/
├── bundles/
│   └── <spec>/
│       └── <bundle-name>/
│           └── v0/v0.1/v0.1.0/
│               ├── manifest.json
│               ├── payload.tar.zst
│               ├── sidecar.zip          ← contains SKILL.md, USAGE.md, etc.
│               └── publish.json
├── recipes/
│   └── <spec>/
│       └── <recipe-name>/
│           └── v0/v0.1/v0.1.0/
│               ├── recipe.json
│               └── publish.json
└── catalog.json                         ← index of all published artefacts
```

Zip the root, get everything. That's the "ships as one zip" property.
