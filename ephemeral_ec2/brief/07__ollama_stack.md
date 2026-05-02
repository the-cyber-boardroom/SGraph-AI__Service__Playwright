# Ephemeral EC2 — Ollama Stack Specification

## What it runs

**Ollama** (`ollama.com`) — a local LLM runtime that exposes an OpenAI-compatible REST API
on port 11434. Supports any model in the Ollama registry (Llama 3.3, Qwen 2.5 Coder,
DeepSeek R2, Mistral, Phi-4, Gemma 3, etc.).

Ollama manages its own process via a systemd service. GPU passthrough complexity in containers
on AL2023 means we run it bare on the host; Docker is not installed unless another tool on the
same instance needs it (the default `container_engine = 'none'`).

---

## GPU instance selection guide

| AWS instance  | GPU                  | VRAM   | Suitable models                        |
|---------------|----------------------|--------|----------------------------------------|
| g4dn.xlarge   | NVIDIA T4            | 16 GB  | 7B–13B (q4), 70B (q2 barely)          |
| g4dn.12xlarge | 4× T4                | 64 GB  | 70B (q4), MoE models                  |
| g5.xlarge     | NVIDIA A10G          | 24 GB  | 13B–34B (q4), 70B (q2)               |
| g5.12xlarge   | 4× A10G              | 96 GB  | 70B (q4), 2×70B                       |
| p3.2xlarge    | NVIDIA V100          | 16 GB  | 7B–13B (q4)                           |
| p3.8xlarge    | 4× V100              | 64 GB  | 70B (q4)                              |
| g6.xlarge     | NVIDIA L4            | 24 GB  | 13B–34B (q4), fast inference          |

Default instance type for Ollama stack: `g4dn.xlarge` (best cost/capability ratio for 13B
models; sufficient for code-generation use cases with Qwen2.5-Coder or DeepSeek-Coder).

CPU-only is also supported (no GPU, c7i.4xlarge or similar) for smaller models (≤7B) where
GPU cost is not justified.

---

## Instance profile

| Parameter        | Default          | Notes                                       |
|------------------|------------------|---------------------------------------------|
| instance_type    | g4dn.xlarge      | GPU instance; set to c7i.4xlarge for CPU    |
| min_storage_gb   | 100              | Model weights: 7B≈4GB, 70B≈40GB q4         |
| container_engine | none             | No Docker by default                        |
| app_in_container | False            | Ollama systemd service on host              |
| api_port         | 11434            | OpenAI-compatible; never exposed publicly   |
| health_path      | /api/tags        | Returns JSON list of local models           |
| boot_seconds     | 120 (baked AMI)  | Model pre-pulled in AMI                     |
| boot_seconds_ami | 60               | Driver init dominates                       |

---

## Create request fields (beyond base)

```
model_name       : Safe_Str__Text = 'qwen2.5-coder:7b'
    Ollama model reference. Pulled during user-data if not in AMI.
    Examples: 'llama3.3', 'deepseek-r2:70b', 'phi4', 'qwen2.5-coder:32b'

allowed_cidr     : Safe_Str__Text = ''
    CIDR that may reach port 11434. Defaults to caller /32.
    For open-design integration, set to open-design EC2 private IP /32.

pull_on_boot     : bool = True
    When False, assumes model is baked into the AMI (faster boot).
    When True, `ollama pull <model_name>` runs in user-data (adds minutes).

gpu_required     : bool = True
    When True, validates instance_type has a GPU before launching.
    Set to False for CPU-only deployments.
```

---

## User-data script sections (in order)

1. `Section__Base` — hostname, dnf update
2. **NVIDIA driver section** (Ollama-specific, GPU only):
   ```bash
   # Install NVIDIA drivers for AL2023
   dnf install -y kernel-devel kernel-headers
   dnf config-manager --add-repo \
     https://developer.download.nvidia.com/compute/cuda/repos/amzn2023/x86_64/cuda-amzn2023.repo
   dnf install -y cuda-toolkit-12-4 nvidia-driver
   modprobe nvidia
   ```
3. **Ollama install section**:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   systemctl enable --now ollama

   # Wait for Ollama to be ready
   until curl -sf http://localhost:11434/api/tags; do sleep 2; done

   # Pull model (skipped when pull_on_boot=False)
   ollama pull {model_name}
   ```
4. `Section__Shutdown` — auto-terminate timer

**No nginx.** Port 11434 is never exposed publicly; the SG restricts it to `allowed_cidr`.

---

## Security group rules

```
inbound_ports  = []                      ← no public ports
extra_cidrs    = {11434: allowed_cidr}   ← internal access only
```

SSH is off by default. To debug, add `--ssh` flag to the create command.

---

## Stack mapper — Schema__Ollama__Info fields

```
instance_id      : Safe_Str__Instance__Id
stack_name       : Safe_Str__Stack__Name
region           : Safe_Str__AWS__Region
state            : Enum__Stack__State
private_ip       : str              ← primary address for consumers
public_ip        : str              ← present but never used by default
instance_type    : str
ami_id           : str
model_name       : str              ← from StackModel tag
api_base_url     : str              ← f'http://{private_ip}:11434/v1'
uptime_seconds   : int
gpu_count        : int              ← from DescribeInstances GPU info
```

---

## CLI commands

```
ec2 ollama create
    --region        eu-west-2
    --instance-type g4dn.xlarge
    --model         qwen2.5-coder:7b
    --allowed-cidr  ''              (defaults to caller /32)
    --max-hours     4
    --no-pull       (skip ollama pull, assume baked AMI)
    --wait          (poll until model is ready)

ec2 ollama list    [--region]
ec2 ollama info    <name>  [--region]
ec2 ollama delete  <name>  [--region]
ec2 ollama health  <name>  [--region]
ec2 ollama models  <name>  [--region]   (calls /api/tags, lists local models)
ec2 ollama pull    <name> <model>       (pull additional model onto running instance)
```

---

## AMI bake strategy for Ollama

GPU driver installation takes 5–10 minutes. Model pull for a 70B q4 model adds another
5–15 minutes. An AMI baked with drivers + model cuts cold-start to ~60 seconds (driver
init only). Recommended for any model larger than 7B or any latency-sensitive workflow.

The `bake-ami` command:
1. Launches a fresh instance with `pull_on_boot=True`
2. Waits for health (model ready)
3. Stops the instance (does not terminate)
4. Creates an AMI
5. Terminates the stopped instance

Subsequent creates with `--from-ami <ami-id>` skip the driver install and model pull.
