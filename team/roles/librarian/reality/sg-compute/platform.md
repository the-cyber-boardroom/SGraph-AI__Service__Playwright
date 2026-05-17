# Platform Interface and EC2 Platform

**Domain:** `sg-compute/` | **Subarea:** `sg_compute/platforms/` | **Last updated:** 2026-05-17

The `Platform` abstract base and its concrete `EC2__Platform` implementation. Includes all EC2 helpers, user-data composables, health pollers, networking primitives, and EC2-specific enums/collections.

---

## EXISTS

### sg_compute/platforms/

| Class / File | Path | Description |
|--------------|------|-------------|
| `Platform` | `platforms/Platform.py` | Abstract base; defines `create_node`, `list_nodes`, `get_node`, `delete_node` |
| `EC2__Platform` | `platforms/ec2/EC2__Platform.py` | Wraps EC2 helpers; implements `list_nodes`, `get_node`, `delete_node`; `create_node` delegates to spec services |
| `EC2__Launch__Helper` | `platforms/ec2/helpers/EC2__Launch__Helper.py` | (moved from `sg_compute/helpers/aws/`) |
| `EC2__SG__Helper` | `platforms/ec2/helpers/EC2__SG__Helper.py` | |
| `EC2__Tags__Builder` | `platforms/ec2/helpers/EC2__Tags__Builder.py` | |
| `EC2__AMI__Helper` | `platforms/ec2/helpers/EC2__AMI__Helper.py` | |
| `EC2__Instance__Helper` | `platforms/ec2/helpers/EC2__Instance__Helper.py` | |
| `EC2__Stack__Mapper` | `platforms/ec2/helpers/EC2__Stack__Mapper.py` | |
| `Stack__Naming` | `platforms/ec2/helpers/Stack__Naming.py` | |
| `Section__Base` | `platforms/ec2/user_data/Section__Base.py` | (moved from `sg_compute/helpers/user_data/`) |
| `Section__Docker` | `platforms/ec2/user_data/Section__Docker.py` | |
| `Section__Node` | `platforms/ec2/user_data/Section__Node.py` | |
| `Section__Nginx` | `platforms/ec2/user_data/Section__Nginx.py` | |
| `Section__Env__File` | `platforms/ec2/user_data/Section__Env__File.py` | |
| `Section__Shutdown` | `platforms/ec2/user_data/Section__Shutdown.py` | |
| `Section__Sidecar` | `platforms/ec2/user_data/Section__Sidecar.py` | Renders ECR-login + `docker run` block for the host-control sidecar; returns `''` when `registry=''` |
| `Health__Poller` | `platforms/ec2/health/Health__Poller.py` | |
| `Health__HTTP__Probe` | `platforms/ec2/health/Health__HTTP__Probe.py` | |
| `Caller__IP__Detector` | `platforms/ec2/networking/Caller__IP__Detector.py` | |
| `Stack__Name__Generator` | `platforms/ec2/networking/Stack__Name__Generator.py` | |

### sg_compute/platforms/ec2/user_data/ — NEW SECTIONS (v0.2.7)

| Class | Path | Description |
|-------|------|-------------|
| `Section__GPU_Verify` | `user_data/Section__GPU_Verify.py` | `nvidia-smi` check; exits 47 on failure. Empty when `gpu_required=False`. |
| `Section__Ollama` | `user_data/Section__Ollama.py` | Installs Ollama, optional `--expose-api` systemd drop-in, pulls model. |
| `Section__Claude_Launch` | `user_data/Section__Claude_Launch.py` | Boots Claude under tmux; empty when `with_claude=False`. |
| `Section__Agent_Tools` | `user_data/Section__Agent_Tools.py` | Python venv with `requests/httpx/rich`; `/etc/logrotate.d/sg-compute` drop-in. |

### sg_compute/platforms/ec2/enums/ — BV2.7

| Class | Path | Values |
|-------|------|--------|
| `Enum__Instance__State` | `platforms/ec2/enums/Enum__Instance__State.py` | pending/running/shutting-down/terminated/stopping/stopped/unknown |

### sg_compute/platforms/ec2/primitives/ — BV2.7

| Class | Path | Pattern |
|-------|------|---------|
| `Safe_Str__AMI__Id` | `platforms/ec2/primitives/Safe_Str__AMI__Id.py` | `^ami-[0-9a-f]{17}$` |
| `Safe_Str__Instance__Id` | `platforms/ec2/primitives/Safe_Str__Instance__Id.py` | `^i-[0-9a-f]{17}$` |

### sg_compute/platforms/ec2/collections/ — BV2.7

| Class | Path |
|-------|------|
| `List__Instance__Id` | `platforms/ec2/collections/List__Instance__Id.py` |

### Exceptions

| Class | Path | Notes |
|-------|------|-------|
| `Exception__AWS__No_Credentials` | `platforms/exceptions/Exception__AWS__No_Credentials.py` | Raised when AWS credentials absent; caught by registered 503 handler in `Fast_API__Compute` |

---

## See also

- [`index.md`](index.md) — SG/Compute cover sheet
- [`primitives.md`](primitives.md) — core primitives consumed by EC2 helpers
- [`specs.md`](specs.md) — pilot specs and per-spec services that `EC2__Platform.create_node` delegates to
- [`pods.md`](pods.md) — pod management (Pod__Manager bridges via `EC2__Instance__Helper` public IP)
