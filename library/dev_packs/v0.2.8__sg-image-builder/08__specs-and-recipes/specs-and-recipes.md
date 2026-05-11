# Specs and Recipes

A **spec** is a named use case. A **recipe** is a concrete instantiation of a spec (a particular set of bundles, a particular configuration). This doc lists the 9 v1 specs in implementation order, with what each proves and what its test suite looks like.

The ladder is deliberately CPU-first. Levels 1–7 are CPU instances and prove the entire workflow without GPU complexity. Levels 8–9 are the GPU targets — local-claude's actual use case — and reuse everything from 1–7.

---

## The ladder

| # | Spec | Instance | Tests "works" by | Key primitive proved |
|---|---|---|---|---|
| 1 | `ssh_file_server` | t3.micro | SSH in, create/read/delete a file | The whole workflow on the simplest target |
| 2 | `python_server` | t3.micro | HTTP server returns hello-world | Bundle includes a service |
| 3 | `node_server` | t3.micro | Same with Node.js | Different runtime, same workflow |
| 4 | `graphviz` | t3.micro | Single-action: dot file → PNG | Stateless action, no long-running service |
| 5 | `docker` | t3.small | `docker run hello-world` works | Docker daemon transparency |
| 6 | `ollama_disk` | c5.xlarge | Ollama binary + model on disk, `/api/generate` responds | Model as separate bundle |
| 7 | `ollama_docker` | c5.xlarge | Same in a container | Container + bundle interaction |
| 8 | `vllm_disk` | g5.xlarge | vLLM serving Qwen with the working flag set | GPU instance + model bundle |
| 9 | `vllm_docker` | g5.xlarge | The current local-claude path, but fast | The "real" target |

Each spec is a Python package under `sg_image_builder_specs/<spec-id>/` with this structure:

```
sg_image_builder_specs/ssh_file_server/
├── pyproject.toml                  ← spec is a separately-installable package
├── README.md
├── manifest.py                     ← Schema__Spec definition
├── schemas/
│   └── ...                         ← spec-specific schemas (rare)
├── service/
│   └── ...                         ← spec-specific service classes (rare)
├── recipes/
│   ├── default.json                ← the canonical recipe
│   └── minimal.json                ← stripped variant
├── tests/
│   ├── unit/                       ← runs on host
│   ├── integration/                ← runs against twin target
│   └── end_to_end/                 ← runs against real EC2
└── version
```

---

## Spec 1: `ssh_file_server`

**The hello-world of sgi.** Proves the entire workflow: capture, package, publish, load, test. Trivial bundle contents.

### What it produces

An EC2 instance you can SSH into. That's it. No additional service, no extra software — just a working SSH setup with a known user, a known home directory layout, a known set of basic tools.

### Recipe

```json
{
  "spec": "ssh_file_server",
  "name": "default",
  "version": "0.1.0",
  "steps": [],
  "required_arch": "x86_64",
  "required_os": "al2023"
}
```

Yes — empty steps. AL2023 already ships with SSH and the basic tools. This spec's only job is to **be the simplest possible target** for testing sgi infrastructure.

### Test suite

```python
# tests/end_to_end/test_ssh_file_server.py
def test__ssh_login_works(target):
    result = target.exec_command(Schema__Exec__Request(command='whoami'))
    assert result.exit_code == 0
    assert result.stdout.strip() == 'ec2-user'

def test__file_create_read_delete(target):
    target.exec_command(Schema__Exec__Request(command='echo "hello" > /tmp/sgi-test.txt'))
    result = target.exec_command(Schema__Exec__Request(command='cat /tmp/sgi-test.txt'))
    assert 'hello' in result.stdout
    target.exec_command(Schema__Exec__Request(command='rm /tmp/sgi-test.txt'))

def test__basic_tools_present(target):
    for tool in ['ls', 'cat', 'rm', 'echo', 'grep', 'find']:
        result = target.exec_command(Schema__Exec__Request(command=f'which {tool}'))
        assert result.exit_code == 0
```

### KPIs

```
first_load_p50_ms : 5_000     (5s — basically nothing to load)
boot_p50_ms        : 25_000   (25s — just EC2 boot + SSH ready)
execution_p50_ms   : 100      (100ms — SSH commands are fast)
cold_start_target_ms : 45_000 (45s)
```

### Why this is spec #1

If sgi can't ship `ssh_file_server`, it can't ship anything. This is the smoke test for every part of the workflow. Once this works end-to-end on real AWS, the rest of the specs are variations.

---

## Spec 2: `python_server`

A FastAPI hello-world server.

### What it produces

EC2 + Python 3.12 + FastAPI + uvicorn + a "hello world" service on port 8000. Managed by systemd, starts at boot.

### Bundles

1. **`python-runtime` v0.1.0** — Python 3.12 with pip, venv, FastAPI, uvicorn, sgi-related Python tools.
2. **`hello-server` v0.1.0** — The application code + systemd unit + venv contents.

### Recipe

```json
{
  "spec": "python_server",
  "steps": [
    {"name": "python", "bundle_uri": "s3://.../bundles/python_server/python-runtime/v0/v0.1/v0.1.0/"},
    {"name": "app",    "bundle_uri": "s3://.../bundles/python_server/hello-server/v0/v0.1/v0.1.0/"}
  ]
}
```

### Test suite

```python
def test__http_get_returns_hello(target):
    result = target.exec_command(Schema__Exec__Request(command='curl -s http://localhost:8000/'))
    assert '"message":"hello"' in result.stdout

def test__service_starts_on_boot(target):
    result = target.exec_command(Schema__Exec__Request(command='systemctl is-active hello-server'))
    assert result.stdout.strip() == 'active'
```

### Primitive proved

Bundles can include a systemd service that's wired to start at boot. The capture phase must observe the systemd unit registration.

---

## Spec 3: `node_server`

Same as `python_server` but with Node.js + Express.

### Bundles

1. `node-runtime` — Node 20 + npm + global packages
2. `node-hello-server` — application code + node_modules + systemd unit

### Why this exists separately from `python_server`

To verify that the capture/load workflow is genuinely language-agnostic. Different package managers (`npm` vs `pip`), different file layouts (`node_modules/` vs `venv/`), different startup commands — all proved transparent by P2.

---

## Spec 4: `graphviz`

A stateless single-action target. Take a `.dot` file as input, produce a PNG as output.

### What it produces

EC2 + graphviz installed + a wrapper script at `/usr/local/bin/dot-to-png` that takes stdin → stdout.

### Bundles

1. `graphviz-runtime` — the `graphviz` package and its libraries, captured from `apt-get install graphviz`.

### Recipe

```json
{
  "spec": "graphviz",
  "steps": [
    {"name": "graphviz", "bundle_uri": "s3://.../bundles/graphviz/graphviz-runtime/v0/v0.1/v0.1.0/"}
  ]
}
```

### Test suite

```python
def test__dot_to_png(target):
    target.copy_to(transfer=Schema__Exec__File__Transfer(local_path='./fixtures/sample.dot', remote_path='/tmp/in.dot'))
    result = target.exec_command(Schema__Exec__Request(command='dot -Tpng /tmp/in.dot > /tmp/out.png'))
    assert result.exit_code == 0
    result = target.exec_command(Schema__Exec__Request(command='file /tmp/out.png'))
    assert 'PNG' in result.stdout
```

### Primitive proved

A spec doesn't need a long-running service. Stateless single-shot actions work just as well. Also the first spec where `strip --mode minimal` is genuinely aggressive — graphviz's runtime needs are a tiny subset of what `apt-get install graphviz` puts on disk.

---

## Spec 5: `docker`

Docker daemon working on AL2023.

### Bundles

1. `docker-daemon` — Docker CE + containerd + cli, captured from `dnf install docker`.

### Test suite

```python
def test__docker_runs_hello_world(target):
    result = target.exec_command(Schema__Exec__Request(command='sudo docker run --rm hello-world'))
    assert 'Hello from Docker' in result.stdout
```

### Primitive proved

The bundle includes a daemon (more complex than a simple service). The capture must preserve `/etc/docker/` config, `/var/lib/docker/` initial state, and the systemd unit. Loading must restart the daemon correctly.

This is the foundation for all subsequent container-based specs (7, 9).

---

## Spec 6: `ollama_disk`

Ollama binary running natively on disk (no container). Model weights on disk too.

### Bundles

1. `ollama-runtime` — Ollama binary, captured from `curl -fsSL https://ollama.com/install.sh | sh`.
2. `ollama-gemma-2b` — The gemma2:2b model weights.

Note: bundle 2 is large (~1.6 GB). This is the first spec where the model-as-separate-bundle pattern really pays off — we update the runtime without re-uploading the model.

### Recipe

```json
{
  "spec": "ollama_disk",
  "steps": [
    {"name": "ollama",   "bundle_uri": "s3://.../bundles/ollama_disk/ollama-runtime/v0/v0.1/v0.1.0/"},
    {"name": "model",    "bundle_uri": "s3://.../bundles/ollama_disk/ollama-gemma-2b/v0/v0.1/v0.1.0/"}
  ]
}
```

### Test suite

```python
def test__ollama_serves(target):
    # systemd should already have started ollama
    result = target.exec_command(Schema__Exec__Request(command='curl -s http://localhost:11434/api/tags'))
    assert 'gemma2:2b' in result.stdout

def test__inference_works(target):
    result = target.exec_command(Schema__Exec__Request(
        command="""curl -s http://localhost:11434/api/generate -d '{"model": "gemma2:2b", "prompt": "hello", "stream": false}'"""
    ))
    assert result.exit_code == 0
    assert '"response":' in result.stdout
```

### Primitive proved

Multi-bundle recipes work. Large bundles work. The "model as separate IFD artefact" pattern works.

---

## Spec 7: `ollama_docker`

Ollama in a Docker container.

### Bundles

1. `docker-daemon` (reuse from spec 5)
2. `ollama-docker-image` — `docker save ollama/ollama:latest -o image.tar`, ~1 GB
3. `ollama-gemma-2b` (reuse from spec 6)

### Test suite

Same shape as spec 6 — `curl` to `localhost:11434` — but the test should verify that the service is running *inside Docker*, not natively.

### Primitive proved

Bundles can contain Docker images. The capture captures the image's overlay2 directory; the load restores it; Docker picks it up natively. Container start-up time is part of the boot KPI.

---

## Spec 8: `vllm_disk`

vLLM running natively. **First GPU spec.**

### Bundles

1. `nvidia-driver-os-bundle` — captured from the DLAMI base layer (this might be empty if we start from DLAMI; see §architectural-decision below)
2. `cuda-runtime` — CUDA libraries
3. `vllm-runtime` — vLLM Python package and its deps
4. `qwen3-coder` — the model weights, ~15 GB

### Architectural decision

We start from the DLAMI AL2023 OSS variant as our base AMI for GPU specs. This means:

- `nvidia-driver` and `cuda-runtime` may be empty bundles (already in DLAMI) — or they may capture customisations on top. Determine empirically.
- The boot floor is ~37s instead of ~17s (per the EBS findings doc).
- Trade-off: drivers always work; the cost is 20s of boot time we pay every launch.

Alternative path (deferred to v0.2): use AL2023 base and ship `nvidia-driver-bundle` as a real bundle, loaded at boot. Saves 20s per launch but adds a kernel/driver version-pinning burden.

### Test suite

Adapted from the working local-claude smoke tests:

```python
def test__nvidia_smi_works(target):
    result = target.exec_command(Schema__Exec__Request(command='nvidia-smi --query-gpu=name --format=csv,noheader'))
    assert result.exit_code == 0
    assert 'A10G' in result.stdout

def test__vllm_serves(target):
    result = target.exec_command(Schema__Exec__Request(command='curl -s http://localhost:8000/v1/models'))
    assert result.exit_code == 0
    assert '"qwen' in result.stdout.lower()

def test__inference_works(target):
    result = target.exec_command(Schema__Exec__Request(
        command="""curl -s http://localhost:8000/v1/completions -H 'Content-Type: application/json' -d '{"model": "qwen3-coder", "prompt": "def add(a, b):", "max_tokens": 50}'"""
    ))
    assert result.exit_code == 0
    assert '"choices"' in result.stdout
```

### Primitive proved

GPU instance. The same capture/load workflow used for CPU specs works for GPU. The model bundle is the largest sgi has ever handled (~15 GB).

---

## Spec 9: `vllm_docker`

The current local-claude path: vLLM in a container.

### Bundles

1. `docker-daemon` (reuse)
2. `nvidia-container-toolkit-runtime` — for Docker GPU access
3. `vllm-docker-image` — `docker save vllm/vllm-openai:latest`
4. `qwen3-coder` (reuse from spec 8)

### Test suite

Identical contract to spec 8 — `vLLM /v1/models` returns 200, inference works. The container-vs-disk implementation is transparent to the test (P2).

### What this proves

The entire local-claude system, but produced via sgi's workflow. The KPI target here is the headline number:

```
cold_start_target_ms: 90_000    (90s — down from ~600s today)
```

This is the spec that vindicates sgi's existence.

---

## Recipe composition rules

A recipe is an ordered list of bundle loads + per-instance values:

```python
class Schema__Recipe(Type_Safe):
    spec             : Safe_Str
    name             : Safe_Str
    version          : Safe_Str
    steps            : List[Schema__Recipe__Step]
    instance_values  : Dict[Safe_Str, Safe_Str]                              # hostname, model_name, etc.
    required_arch    : Safe_Str                          = 'x86_64'
    required_os      : Safe_Str                          = 'al2023'
    required_capabilities : List[Safe_Str]               = []                # ['nvidia-gpu']
    kpis             : Schema__Recipe__KPIs
```

Steps execute in order. A step may declare:

- `test_after: true` — run the bundle's own sidecar tests after this step (fail-fast on broken intermediate states)
- `parallel_group: <name>` — execute in parallel with other steps in the same group (v2)

The default v1 behaviour is sequential, no parallelism. Optimisations come later once we have measurements.

---

## How a spec evolves over time

The spec is registered in code. Recipes are versioned in storage (IFD). Bundles are versioned in storage (IFD).

```
sg_image_builder_specs/vllm_disk/  ← code, evolves with the codebase

s3://.../recipes/vllm_disk/default/v0/v0.1/v0.1.0/   ← the recipe at recipe-version 0.1.0
                              /v0.1.1/                ← updated to reference newer bundles
                              /v0.2.0/                ← major change to the recipe shape

s3://.../bundles/vllm_disk/vllm-runtime/v0/v0.1/v0.1.0/   ← bundle versions independent
                                       /v0.1.1/            ← stripped --mode debug
                                       /v0.2.0/            ← stripped --mode minimal
```

A recipe at v0.1.0 might reference vllm-runtime v0.1.0 (the unstripped fat bundle). Recipe at v0.1.1 references vllm-runtime v0.1.1 (stripped --mode service). Both recipes are valid and pinnable.

This is the workflow that makes "update the model without touching the runtime" a 30-second operation.
