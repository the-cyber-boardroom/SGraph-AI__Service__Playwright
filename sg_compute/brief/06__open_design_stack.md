# SG/Compute — Open Design Spec Specification

## What it runs

**Open Design** (`github.com/nexu-io/open-design`) — an open-source, AI-assisted design
platform. Single Node.js process (daemon + static Next.js export) on port 7456.
SQLite at `.od/app.sqlite` for session state. No external databases required.

Upstream ships no Dockerfile. We run the daemon bare on the host and put nginx in a
container in front for HTTPS.

---

## Instance profile

| Parameter        | Default          | Notes                                   |
|------------------|------------------|-----------------------------------------|
| instance_type    | t3.large         | 2 vCPU / 8 GB RAM; pnpm build needs RAM |
| min_storage_gb   | 20               | pnpm node_modules + build artefacts     |
| container_engine | docker           | nginx container only                    |
| app_in_container | False            | Node.js daemon runs on host             |
| viewer_port      | 443              | HTTPS, nginx → 7456                     |
| health_path      | /api/agents      | Returns JSON list; 200 = healthy        |
| boot_seconds     | 480 (cold)       | Fresh pnpm install + build              |
| boot_seconds_ami | 45               | Baked AMI with artefacts present        |

---

## Create request fields (beyond base)

```
api_key          : Safe_Str__Text = ''
    Anthropic API key injected as ANTHROPIC_API_KEY in /run/open-design/env.
    When empty, the claude CLI must already be authenticated on the AMI.

ollama_base_url  : Safe_Str__Text = ''
    e.g. 'http://10.0.1.5:11434/v1'
    Injected as OLLAMA_BASE_URL; used by open-design's BYOK proxy endpoint.
    When set, the claude CLI is not required.

open_design_ref  : Safe_Str__Text = 'main'
    Git ref (branch / tag / commit) to check out.

fast_boot        : bool = False
    When True, skips pnpm install + build (assumes baked AMI has artefacts).
```

---

## User-data script sections (in order)

1. `Section__Base` — hostname = stack_name, dnf update, git/curl/jq/unzip
2. `Section__Docker` — docker CE install, socket enable
3. `Section__Node` — Node 24 via NodeSource, pnpm global install
4. `Section__Env__File` — writes `/run/open-design/env` with:
   ```
   ANTHROPIC_API_KEY=<api_key>          # omitted if empty
   OLLAMA_BASE_URL=<ollama_base_url>     # omitted if empty
   OD_PORT=7456
   ```
5. **App section** (open-design specific):
   ```bash
   # Clone and build (skipped when fast_boot=True)
   git clone https://github.com/nexu-io/open-design /opt/open-design
   cd /opt/open-design
   pnpm install
   pnpm --filter @open-design/web build

   # Systemd unit
   cat > /etc/systemd/system/open-design.service <<EOF
   [Unit]
   Description=Open Design daemon
   After=network.target

   [Service]
   EnvironmentFile=/run/open-design/env
   WorkingDirectory=/opt/open-design
   ExecStart=/usr/bin/node apps/daemon/dist/index.js --port 7456
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   EOF
   systemctl enable --now open-design
   ```
6. `Section__Nginx` — docker run nginx container, proxies 443 → 7456, SSE-safe config
7. `Section__Shutdown` — auto-terminate timer

---

## Nginx configuration (SSE-safe)

Open Design uses Server-Sent Events for real-time streaming of chat and agent runs.
Standard nginx buffering breaks SSE. The nginx config must include:

```nginx
proxy_buffering          off;
proxy_cache              off;
proxy_read_timeout       3600s;
proxy_send_timeout       3600s;
chunked_transfer_encoding on;
gzip                     off;
```

---

## Agent auto-detection (open-design behaviour)

Open Design auto-detects coding-agent CLIs on `$PATH`. On the EC2:

- **With `api_key` provided**: install `claude` CLI in user-data, authenticate with the key.
  Open Design detects it and uses it for design generation.
- **With `ollama_base_url` provided**: no CLI needed. Open Design's BYOK proxy at
  `/api/proxy/stream` routes to Ollama. Set as the default model endpoint in the UI.
- **Both provided**: both are available; user selects agent in the UI.

---

## Stack mapper — Schema__Open_Design__Info fields

```
instance_id      : Safe_Str__Instance__Id
stack_name       : Safe_Str__Stack__Name
region           : Safe_Str__AWS__Region
state            : Enum__Stack__State
public_ip        : str
private_ip       : str
instance_type    : str
ami_id           : str
viewer_url       : str          ← f'https://{public_ip}/'
uptime_seconds   : int
has_ollama       : bool         ← True if OLLAMA_BASE_URL tag present
```

---

## CLI commands

```
sg-compute node create --spec open-design
    --region       eu-west-2
    --instance-type t3.large
    --from-ami     ''           (latest AL2023 if blank)
    --name         ''           (auto-generated if blank)
    --api-key      ''           (or $ANTHROPIC_API_KEY)
    --ollama-ip    ''           (private IP of Ollama EC2)
    --ref          main
    --max-hours    1
    --fast-boot
    --open                      (open browser after create)
    --wait                      (poll until healthy)

sg-compute node list --spec open-design            [--region]
sg-compute node info  <name>    [--region]
sg-compute node delete <name>   [--region]
sg-compute node health <name>   [--region] [--timeout 300]
sg-compute node bake-ami <name> [--region]  (future)
```

---

## Two-node workflow (open-design + Ollama)

```bash
# 1. Launch Ollama on GPU
sg-compute node create --spec ollama --model llama3.3 --region eu-west-2 --max-hours 4
# → prints private IP: 10.0.1.42

# 2. Launch open-design pointing at Ollama
sg-compute node create --spec open-design --ollama-ip 10.0.1.42 --max-hours 4 --open
# → opens https://<public-ip>/ in browser
```

Both instances auto-terminate after 4 hours. Zero cleanup required.
