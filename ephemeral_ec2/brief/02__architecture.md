# Ephemeral EC2 — Architecture

## Layer diagram

```
┌─────────────────────────────────────────────────────┐
│  CLI  (ec2 open-design create / list / delete …)    │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│  Stack  (ephemeral_ec2/stacks/open_design/)         │
│  • Schema__*__Create__Request / Response            │
│  • Stack__Service (orchestrates helpers)            │
│  • User_Data__Builder (app-specific cloud-init)     │
└──────┬────────────┬───────────────┬─────────────────┘
       │            │               │
┌──────▼──┐  ┌──────▼──┐  ┌────────▼────────┐
│ helpers/ │  │ helpers/ │  │    helpers/     │
│  aws/   │  │ health/  │  │  user_data/     │
│ EC2     │  │ Poller   │  │  Base sections  │
│ SG      │  │ Checker  │  │  (docker, ssh,  │
│ Tags    │  └──────────┘  │   shutdown …)   │
│ AMI     │                └─────────────────┘
└─────────┘
       │
┌──────▼───────────────────────────────────────────────┐
│  AWS  (boto3 via osbot-aws)                          │
│  EC2 RunInstances / DescribeInstances / Terminate    │
│  EC2 CreateSecurityGroup / AuthorizeIngress          │
│  SSM GetParameter (AMI lookup)                       │
│  EC2 CreateLaunchTemplate (ASG path)                 │
└──────────────────────────────────────────────────────┘
```

## Two-instance topology (open-design + Ollama example)

```
Caller
  │  sp ec2 open-design create --ollama-ip <ip>
  │
  ├── EC2 #1: open-design  (t3.large)
  │     port 443 ← nginx → 7456 (daemon + static web)
  │     Node 24, pnpm, open-design built + running
  │     claude CLI installed (agent auto-detected)
  │     env: OLLAMA_BASE_URL=http://<private-ip>:11434/v1
  │
  └── EC2 #2: Ollama        (g4dn.xlarge, GPU)
        port 11434 open only to EC2 #1 private IP
        Ollama service + model pre-pulled in AMI
        NO public port exposure
```

## Single-instance topology (open-design with Anthropic API)

```
Caller
  │  sp ec2 open-design create --api-key $ANTHROPIC_API_KEY
  │
  └── EC2 #1: open-design  (t3.large)
        port 443 ← nginx → 7456
        claude CLI installed
        env: ANTHROPIC_API_KEY=…
        auto-terminates after max_hours (default 1)
```

## User-data assembly model

User-data is a gzip+base64 bash script built from sections. Each section is a string template.
Sections are composed by the Stack's `User_Data__Builder`; common sections live in
`helpers/user_data/`.

```
BASE_SECTION          — hostname, locale, common packages
DOCKER_SECTION        — docker or podman install + socket enable
APP_SECTION           — stack-specific install + build + systemd unit
ENV_SECTION           — write secrets to /run/<stack>/env (tmpfs)
NGINX_SECTION         — nginx install + reverse-proxy config
SHUTDOWN_SECTION      — systemd-run auto-terminate timer
```

Stacks that need Docker include `DOCKER_SECTION`. Stacks running bare Node.js skip it (but
Docker is available on the host anyway as baseline).

## Security group model

Each stack instance gets its own security group named `<stack-name>-sg`. Rules:

| Stack         | Inbound                                      | Outbound |
|---------------|----------------------------------------------|----------|
| open-design   | TCP 443 from caller /32                      | all      |
| ollama        | TCP 11434 from open-design EC2 private IP /32 | all      |
| (any stack)   | TCP 22 from caller /32 (optional, --ssh)     | all      |

SSH is opt-in and off by default, consistent with the existing stack pattern.

## Auto-terminate mechanism

Every instance created through the SDK carries:

1. `InstanceInitiatedShutdownBehavior=terminate` on the RunInstances call when `max_hours > 0`
2. In user-data: `systemd-run --on-active={max_hours}h /sbin/shutdown -h now`

When the timer fires the instance shuts itself down, which triggers termination. No Lambda,
no EventBridge, no external watchdog required.

## AMI strategy

| Stage          | What is baked                          | Boot time target |
|----------------|----------------------------------------|-----------------|
| Base AMI       | AL2023 + Docker + Node 24 + pnpm       | (not deployed directly) |
| Stack AMI      | Base + app source + build artefacts    | < 60 s to health-ready |
| Fresh (no AMI) | Full install from scratch via user-data | 3–10 min        |

Stack AMIs are optional. The SDK supports both paths; stack definitions declare
`supports_baked_ami: bool`.
