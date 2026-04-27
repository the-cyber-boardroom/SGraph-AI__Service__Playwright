# 05 — Ephemeral Kibana — Setup, Usage, and Debugging

Everything the planning session needs to understand about the stack that
the LETS commands run against.  Read this before designing any `sg-send`
command that talks to Elasticsearch or Kibana.

Source of truth for details: `team/claude/debriefs/2026-04-25__sp-elastic-kibana__02-what.md`
and `03-how-to-use.md`.

---

## What it is

A **single-command ephemeral stack** on EC2 running:

```
EC2 (m6i.xlarge)
  nginx:alpine           :443  TLS termination (self-signed cert, SAN = public IP)
                                / → Kibana
                                /_elastic/* → Elasticsearch
  kibana:8.13.4          :5601 (loopback only)
  elasticsearch:8.13.4   :9200 (loopback only)
```

Everything lives under `/opt/sg-elastic/` on the host.  The stack
auto-terminates after 1 hour by default (configurable with `--max-hours`).
There is **no SSH** — access is via AWS SSM only (`sp el connect` /
`sp el exec`).

---

## Prerequisites

```bash
# 1. AWS credentials with EC2 + IAM + SSM + S3-read permissions
aws sts get-caller-identity

# 2. Region
export AWS_DEFAULT_REGION=eu-west-2

# 3. Elastic password — same value covers create + lets commands
export SG_ELASTIC_PASSWORD="MyStrong_Pass-123"
```

---

## Three ways to launch a stack

### A — Cold path (~3 min, no AMI needed)

```bash
sp el create --wait --seed
```

Installs Docker, pulls images, starts the compose stack, seeds synthetic
data, imports the dashboard.  Use this when iterating on the cloud-init
user-data or when no AMI exists.

### B — Fast-launch from AMI (~80 s, daily workflow)

```bash
sp el create-from-ami --wait
```

Auto-picks the latest `sg:purpose=elastic` AMI.  Docker and images are
pre-installed; containers restart from their baked state.  This is the
normal daily workflow.

### C — Bake an AMI (once, ~10–15 min)

```bash
sp el ami create        # full chain: create → wait → seed → bake → delete source
```

Do this once, then use flow B daily.  The baked AMI carries the pre-warmed
Elasticsearch data + Kibana saved objects + nginx TLS certs.

---

## Inspecting a running stack

```bash
sp el list                              # all stacks: name, state, uptime, IP, URL
sp el info                              # auto-picked stack — full detail
sp el health                            # 8 checks (see below)
```

---

## The 8 health checks (`sp el health`)

| # | Check | Common failure |
|---|-------|---------------|
| 1 | `ec2-state` | Instance not running |
| 2 | `public-ip` | No public IP assigned |
| 3 | `sg-ingress` | **Your IP rotated** since create — most common cause of ConnectTimeout |
| 4 | `tcp-443` | Port 443 not reachable (SG or nginx not up) |
| 5 | `elastic` | Cluster health probe — yellow is normal on single-node |
| 6 | `kibana` | `/api/status` probe |
| 7 | `ssm-boot-status` | Boot log via SSM |
| 8 | `ssm-docker` | `docker ps` via SSM |

---

## Common failures and fixes

### ConnectTimeout when hitting Kibana URL

Your public IP rotated since the stack was created.  The security group
bakes in `{your-ip}/32` at launch time.

```bash
sp el health
# → sg-ingress: FAIL  current IP X.X.X.X not in allowed CIDRs ['Y.Y.Y.Y/32']
```

Fix: tear down and relaunch.

```bash
sp el delete --all -y
sp el create-from-ami --wait
```

### HTTP 401 when running lets commands

`SG_ELASTIC_PASSWORD` doesn't match the stack's baked password.

Recover the baked password:
```bash
sp el exec -- "grep ELASTIC_PASSWORD /opt/sg-elastic/.env"
export SG_ELASTIC_PASSWORD="<value from above>"
```

### `sp el lets cf inventory load` returns 0 objects indexed

The prefix or default date produced no S3 keys.  Diagnose:

```bash
sp el lets cf inventory load --prefix cloudfront-realtime/2026/04/27/ --dry-run
# → pages-listed / objects-scanned will show the count before any write
```

If `objects-scanned = 0`, the prefix or date is wrong.  Use:
```bash
sp el lets cf sg-send files 04/27    # lists inventory rows for that date
```

### Events dashboard panels show no data after `events load`

The data view may point at the wrong time field or the index is empty.

```bash
sp el lets cf events health           # 4 checks including inventory-link %
sp el lets cf events list             # shows pipeline runs + event counts
```

If `health` passes but Kibana shows nothing: check that the Kibana time
filter (top-right of Discover / Dashboards) covers the event timestamps in
the data.  Events are timestamped at CloudFront delivery time, not load
time.

### Side-nav shows Observability / Security / Fleet

The boot-time harden script didn't run.  Check:

```bash
sp el exec -- "cat /var/log/sg-elastic-harden.log"
```

Apply manually:
```bash
sp el harden
```

---

## Talking to the stack via SSM

```bash
sp el connect                          # interactive shell
sp el exec -- "docker ps"             # one-shot
sp el exec -- "tail -f /var/log/sg-elastic-start.log"
sp el exec -- "docker logs sg-elastic-elasticsearch-1 --tail 30"
sp el exec -- "curl -sk -u elastic:${SG_ELASTIC_PASSWORD} https://localhost:9200/_cat/indices?v"
```

---

## Saved objects (dashboards + data views)

```bash
sp el dashboard list                   # what's in Kibana
sp el dashboard export -o my.ndjson    # snapshot
sp el dashboard import my.ndjson       # apply (with overwrite)
sp el data-view list / export / import
```

---

## LETS-specific Kibana objects

When LETS commands run, they auto-import objects alongside the data.  These
are separate from the `sp el seed` synthetic dataset:

| Command | Index pattern | Data view | Dashboard |
|---------|--------------|-----------|-----------|
| `inventory load` | `sg-cf-inventory-*` | `sg-cf-inventory` | "CloudFront Logs - Inventory Overview" (5 panels) |
| `events load` | `sg-cf-events-*` | `sg-cf-events` | "CloudFront Logs - Events Overview" (6 panels) |

Both sets use **legacy `visualization` saved-object type** (not Lens) —
Lens objects carry migration hooks that cause HTTP 500s on hand-rolled
ndjson.  This is a deliberate hardening decision from the slice 1 debrief.

All LETS objects are removed by their matching `wipe` command.  `sp el wipe`
(synthetic data) and `sp el lets cf inventory wipe` are **independent** —
wiping one does not touch the other.

---

## Stack lifecycle (daily recipe)

```bash
# Morning — spin up
sp el create-from-ami --wait

# Work — run lets commands
sp el lets cf inventory load
sp el lets cf events load --from-inventory

# Evening — tear down (saves ~$4.50/day on m6i.xlarge)
sp el delete --all -y
```

**Cost note:** the 1h auto-terminate is a safety net, not a planning tool.
A forgotten overnight stack costs ~$4.50/day.

---

## AMI lifecycle

```bash
sp el ami list                         # what's baked
sp el ami create                       # bake a new one (~10-15 min)
sp el ami delete ami-0xxx -y           # deregister + delete EBS snapshots
```

Delete old AMIs explicitly — `sp el ami create` always bakes a new one; it
does not replace the old one.  Orphaned snapshots accumulate cost.

---

## Why this matters for the LETS planning session

Every `sp el lets cf ...` command requires a running stack.  The planning
session should:

1. **Assume the stack is already up** — the `SG_Send__Orchestrator` and
   any new `sg-send` commands should follow the existing pattern of
   resolving the stack via `Elastic__Service.get_stack_info()` and bailing
   with a friendly message if no stack is running.

2. **Treat the Kibana URL as the base URL for all HTTP calls** — the nginx
   proxy routes `/_elastic/*` to Elasticsearch, so both Kibana API calls
   and Elasticsearch API calls go to the same base URL on port 443.

3. **Do not design anything that writes to the stack's persistent storage**
   except via the established `Inventory__HTTP__Client` / bulk-post pattern
   — no direct Docker exec, no SSM writes.

4. **Remember that `wipe` is the safety valve** — every new `sg-send`
   command that writes to Elastic must have a clearly documented matched
   `wipe` path (even if it just calls the existing `inventory wipe` +
   `events wipe` in sequence).
