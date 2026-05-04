# 01 — Reuse and Foundations

---

## Reuse matrix

| Component | Source | linux | docker | Notes |
|-----------|--------|-------|--------|-------|
| `Stack__Naming` | `aws/Stack__Naming.py` | ✅ verbatim | ✅ verbatim | Just set `section_prefix='linux'` / `'docker'` |
| `Safe_Str__AWS__Region` | `observability/primitives/` | ✅ import as-is | ✅ import as-is | Shared across all sections |
| `Caller__IP__Detector` | `elastic/service/` | ✅ import as-is | ✅ import as-is | Detects caller /32 for SG ingress |
| `AWS__Error__Translator` | `elastic/service/` | ✅ import as-is | ✅ import as-is | Friendly IAM/SG error messages |
| AL2023 AMI resolution | `Elastic__AWS__Client.resolve_latest_al2023_ami()` | ✅ copy method | ✅ copy method | Same SSM parameter path |
| IAM instance profile | `Elastic__AWS__Client.ensure_instance_profile()` | ✅ copy, rename | ✅ copy + add ECR read | linux = SSM only; docker = SSM + ECR |
| SG create pattern | `Elastic__AWS__Client.ensure_security_group()` | ✅ copy, rename | ✅ copy, rename | Port list changes — see below |
| EC2 launch | `Elastic__AWS__Client.launch_instance()` | ✅ copy | ✅ copy | Tags differ |
| SSM exec | `Elastic__AWS__Client.ssm_send_command()` | ✅ copy | ✅ copy | Identical pattern |
| Wait loop | `Elastic__Service.wait_until_ready()` | ✅ copy, adapt | ✅ copy, adapt | Different probe checks |
| `random_stack_name()` | `Elastic__Service` adjectives+scientists | ✅ copy | ✅ copy | Change prefix: `linux-` / `docker-` |
| Schema patterns | `elastic/schemas/` | ✅ copy + rename | ✅ copy + rename | ~7 schemas each |
| CLI surface pattern | `scripts/elastic.py` + `opensearch/cli/` | ✅ follow OpenSearch pattern | ✅ follow OpenSearch pattern | Thin commands, separate Renderers.py |
| Health check framework | `Elastic__Service.health()` | ✅ adapt | ✅ adapt | Different checks (no Kibana) |
| `aws_error_handler` decorator | `scripts/elastic.py` | ✅ import as-is | ✅ import as-is | Shared from elastic CLI module |
| `resolve_stack_name()` | `scripts/elastic.py` | ✅ import as-is | ✅ import as-is | Auto-pick / prompt pattern |

---

## What must be written fresh

### `sp linux` — fresh content

| File | Why fresh |
|------|-----------|
| `Linux__User_Data__Builder.py` | Minimal cloud-init: only auto-terminate + boot-status write; no Docker, no nginx |
| `Enum__Linux__Stack__State.py` | Rename + drop READY state (linux is "ready" as soon as SSM responds) |
| `Safe_Str__Linux__Stack__Name.py` | Same regex as elastic; fresh file per CLAUDE.md rule 21 |
| `Linux__Tags__Builder.py` | `sg:purpose = 'linux'`; same shape as OpenSearch |
| `Linux__Health__Checker.py` | 4 checks: ec2-state, public-ip, ssm-boot-status, ssm-ping (no TCP :443) |
| `scripts/linux.py` (CLI) | Thin Typer surface; follows `scripts/elastic.py` pattern but NO seed/wipe/ami subcommands for v1 |

### `sp docker` — fresh content

| File | Why fresh |
|------|-----------|
| `Docker__User_Data__Builder.py` | Installs Docker + compose plugin; optionally pulls image + writes compose file + runs `docker compose up -d` |
| `Docker__Compose__Template.py` | Renders a minimal docker-compose.yml from `--image` + optional `--port` |
| `Docker__Health__Checker.py` | Same 4 as linux + 2 more: docker-daemon (`docker info`), container-running (`docker ps`) |
| `Enum__Docker__Stack__State.py` | Like linux enum; add DOCKER_STARTING state for post-boot container startup window |
| `scripts/docker.py` (CLI) | Same as linux + `compose-ps`, `compose-logs` commands |

---

## Naming conventions

```python
# linux section
LINUX_NAMING = Stack__Naming(section_prefix='linux')
# → AWS Name tag: 'linux-{stack_name}'  (e.g. 'linux-quiet-fermi')
# → SG GroupName: '{stack_name}-sg'     (e.g. 'quiet-fermi-sg')  ← never "sg-*"
TAG_PURPOSE_VALUE = 'linux'
INSTANCE_PROFILE_NAME = 'sg-linux-ec2'

# docker section
DOCKER_NAMING = Stack__Naming(section_prefix='docker')
TAG_PURPOSE_VALUE = 'docker'
INSTANCE_PROFILE_NAME = 'sg-docker-ec2'
```

---

## IAM policy differences

| Section | Policies |
|---------|----------|
| `sp linux` | `AmazonSSMManagedInstanceCore` only |
| `sp docker` | `AmazonSSMManagedInstanceCore` + `AmazonEC2ContainerRegistryReadOnly` |

Both sections get a fresh IAM role (`sg-linux-ec2`, `sg-docker-ec2`) following the elastic
`ensure_instance_profile()` pattern.  The profiles are idempotent — re-running
create when the profile exists is a no-op.

---

## Security group ports

| Section | Default open ports |
|---------|--------------------|
| `sp linux` | None (SSM only, no public ingress required) |
| `sp docker` | `--port N` maps to ingress :N/tcp from caller /32 |

Both sections lock any ingress to the caller's current public IP (`caller_ip/32`).
The `sp linux health` check mirrors the elastic `sg-ingress` check — flags if
the caller's IP has changed since launch.

---

## OpenSearch as the implementation template

Follow the OpenSearch folder structure (not Elastic) for both new sections:

- Separate `{Section}__SG__Helper.py`, `{Section}__Instance__Helper.py`,
  `{Section}__Tags__Builder.py` instead of one monolithic AWS client.
- `{Section}__Service.py` with a `setup()` lazy-init pattern.
- `cli/Renderers.py` for all Rich output (not inline in the CLI script).
- `fast_api/routes/Routes__{Section}__Stack.py` — **ship alongside the CLI**,
  not as a follow-up (v0.1.96 locked decision: API-first for new sections).

This is the one area where the Elastic section shows its age.  New sections
get the API route on day one.
