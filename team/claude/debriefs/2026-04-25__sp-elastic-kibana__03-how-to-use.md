# 2026-04-25 — `sp el` (Ephemeral Kibana) — 3 / 3 — How to use it

This is part three of a three-part debrief on the `sp elastic` slice.

| Part | File |
|------|------|
| 1 — Why we built this | `2026-04-25__sp-elastic-kibana__01-why.md` |
| 2 — What we built | `2026-04-25__sp-elastic-kibana__02-what.md` |
| 3 — **How to use it** *(this doc)* | `2026-04-25__sp-elastic-kibana__03-how-to-use.md` |

---

## Prerequisites

```bash
# 1. AWS credentials with EC2 + IAM + SSM permissions in your active session
aws sts get-caller-identity                            # confirm the right account/role

# 2. Default region (the elastic CLI also accepts --region)
export AWS_DEFAULT_REGION=eu-west-2

# 3. A strong consistent elastic password — one variable covers create + seed + health
export SG_ELASTIC_PASSWORD="MyStrong_Pass-123"

# 4. The sp CLI on PATH (already installed if you're in the SGraph Playwright repo)
sp el --help
```

Everything in this doc assumes the four exports above are in place.

## The three flows

### Flow A — First time / iterating on user-data (cold path, ~3 min)

```bash
sp el create --wait --seed
```

Single command from nothing to a working Kibana with synthetic data and a dashboard. Output:

```
  Stack launched  (state: pending)
  ┌──────────────┬─────────────────────────────────────────────┐
  │ stack-name   │ elastic-fierce-faraday                      │
  │ instance-id  │ i-0...                                       │
  │ kibana-url   │ https://18.130.x.y/                          │
  │ elastic-pass │ MyStrong_Pass-123  (from $SG_ELASTIC_PASSWORD) │
  │ auto-term    │ 1h from boot                                 │
  └──────────────┴─────────────────────────────────────────────┘

  Waiting for Kibana  (polling every 10s, up to 900s)
  ⠙ [115s #12]  state=running  es=yellow  kibana=ready
  ✓  Kibana is ready at https://18.130.x.y/

  Seeding  (10000 docs, default index sg-synthetic, default dashboard)
  ✓  posted 10000 docs to sg-synthetic  (4229 ms, 2364 docs/sec)
  ✓  data view created  id=...
  ✓  dashboard imported  "Synthetic Logs Overview" (5 objects)

  Bootstrap timeline
  ─ aws launch returned       5s
  ─ elastic ready (y/g)     129s
  ─ kibana ready (200)      150s
  ─ wait phase finished     150s
  ─ seed finished           158s
  ─ total wall time         158s

  Open Kibana:
    https://18.130.x.y/app/dashboards
```

Open the URL → you're in Discover/Dashboards with `Synthetic Logs Overview` already populated.

### Flow B — Bake an AMI once, fast-launch repeatedly

**Step 1: bake an "Ephemeral Kibana" AMI from nothing** (~10-15 min, once):

```bash
sp el ami create
```

Default behaviour: creates a fresh stack, seeds it, bakes the AMI, deletes the source. The full chain in five phases. Single command.

Output ends with:
```
  ✓  AMI ami-0xxx is available

  Bake-from-scratch complete  total 612s
    ami-id:   ami-0xxx
    password: MyStrong_Pass-123  (baked into the AMI; same on every launch from it)

  Launch a fresh stack from this AMI:
    sp el create-from-ami ami-0xxx --wait        # ~30-60s vs ~3 min
```

**Step 2: tear down whatever's running** (saves money while the AMI bakes / between launches):

```bash
sp el delete --all -y
```

**Step 3: fast-launch from the AMI** (~80s, daily):

```bash
sp el create-from-ami --wait
```

No AMI id required — auto-picks the latest available. Drops you straight into a working Kibana with the same data + dashboard the AMI was baked with.

```
  No AMI specified — using latest available: ami-0xxx  (Ephemeral Kibana - elastic-...)

  Fast-launched from AMI  (state: pending)
  ┌──────────────┬─────────────────────────┐
  │ stack-name   │ elastic-sharp-darwin    │
  │ from-ami     │ ami-0xxx                │
  │ elastic-pass │ baked into AMI          │
  └──────────────┴─────────────────────────┘

  Waiting for Kibana  (polling every 5s, up to 300s)
  ✓  Kibana is ready at https://3.10.x.y/

  Bootstrap timeline
  ─ aws launch returned    4s
  ─ elastic ready (y/g)   80s
  ─ kibana ready (200)    80s
  ─ total wall time       80s
```

### Flow C — Bake a customised stack as-is (advanced)

If you've manually customised a running stack (built a dashboard in the UI, added users, tuned ES settings) and want to snapshot that exact state:

```bash
sp el ami create elastic-fierce-faraday --wait
```

Pass the existing stack name explicitly. The `--from-scratch` chain is skipped; only the AMI bake runs.

## Daily commands

### Inspecting a stack

```bash
sp el list                                     # everyone, with uptime
sp el info                                     # auto-picked stack, full detail
sp el info elastic-fierce-faraday              # explicit
sp el health                                   # 8 checks + targeted "likely fix" hint
```

### Talking to a stack

```bash
sp el connect                                  # SSM Session Manager interactive shell
sp el exec -- "docker ps"                      # one-shot command
sp el exec -- "tail -f /var/log/sg-elastic-start.log"
sp el exec -- "grep ELASTIC_PASSWORD /opt/sg-elastic/.env"   # if you've forgotten the AMI's password
```

### Re-seeding / re-baking

```bash
sp el wipe -y                                  # drop synthetic data + data view + dashboard objects
sp el seed                                     # re-seed (also re-creates data view + dashboard)
sp el harden                                   # re-apply side-nav cleanup (idempotent)
```

### Dashboard / data view round-trip

```bash
sp el dashboard list                           # what's there
sp el dashboard export -o my-dash.ndjson       # snapshot one
sp el dashboard import my-dash.ndjson          # apply elsewhere

sp el data-view list / export / import         # same three actions for data views
```

### AMI lifecycle

```bash
sp el ami list                                 # what we've baked
sp el ami wait ami-0xxx                        # block until pending → available
sp el ami delete ami-0xxx -y                   # deregister + delete EBS snapshots
```

### Tearing everything down

```bash
sp el delete --all -y                          # every stack in the region
sp el ami delete <oldest-ami> -y               # one AMI at a time (no --all yet)
```

## Common failures and what they mean

### "ConnectTimeout: HTTPSConnectionPool ... Connection to X.X.X.X timed out"

Your public IP rotated since `sp el create` baked it into the SG.

```bash
sp el health
# → sg-ingress will be FAIL with "current IP X.X.X.X not in allowed CIDRs ['Y.Y.Y.Y/32']"
```

Fix: `sp el delete --all -y && sp el create-from-ami --wait` (the new SG bakes in your current IP).

### "HTTP 401: ... unable to authenticate user [elastic] for REST request [/_bulk]"

`SG_ELASTIC_PASSWORD` doesn't match the live stack's password.

- Mismatch usually because you re-exported a password from a previous stack
- For a stack from AMI: `sp el exec -- "grep ELASTIC_PASSWORD /opt/sg-elastic/.env"` and re-export

### "Cannot read properties of undefined (reading 'layers')" in Kibana logs

Stale half-imported Lens objects from an earlier dashboard attempt. Already auto-cleaned by `ensure_default_dashboard`'s pre-clean step, but if you see it manually:

```bash
sp el wipe -y                                  # cleans all dashboard saved objects
sp el seed                                     # re-imports cleanly
```

### Side-nav still shows Observability / Security on a fresh stack

The boot-time harden script may not have run. Diagnose:

```bash
sp el exec -- "cat /var/log/sg-elastic-harden.log"
```

Manual fix:

```bash
sp el harden
```

Refresh Kibana in the browser; the slim nav should appear.

## Tips and shortcuts

- **`sp el` is the alias** — `sp elastic` and `sp el` are identical.
- **Auto-pick** — every command that takes a stack name will auto-pick when only one stack exists. Multi-stack prompts a numeric chooser. To skip: pass the name explicitly.
- **`--debug`** — appears before any sub-command, shows the full Python traceback on errors. Default is the friendly one-line summary.
- **Idempotency** — `seed`, `wipe`, `harden` are all safe to re-run. `seed` even self-heals stale dashboard objects.
- **Cost ceiling** — every stack auto-terminates after `--max-hours` (default 1). Pass `--max-hours 0` to disable, but don't forget you did.
- **No SSH** — only SSM is exposed. Use `sp el connect` for interactive, `sp el exec` for one-shots.

## Anti-patterns

- **Don't put real production data in here.** It's an ephemeral demo box. Single-node, no replicas, auto-terminates, baked password.
- **Don't share AMIs with third parties.** The bake-time password ships with the AMI. Fine for internal use, not for distribution.
- **Don't re-use `sp el ami create` to update an existing AMI.** It always bakes a new one. Delete the old AMI explicitly with `sp el ami delete` to avoid accumulating snapshot costs.
- **Don't skip `sp el delete --all` between iteration cycles.** A forgotten stack costs ~$0.19/h × 24h = ~$4.50/day on `m6i.xlarge`. The 1h auto-terminate is a safety net, not a planning tool.
- **Don't try to bake from a stack mid-seed.** Wait for `sp el seed` to complete (or trust the `--from-scratch` chain to do it for you).

## Recommended starter recipe

```bash
# Once
export AWS_DEFAULT_REGION=eu-west-2
export SG_ELASTIC_PASSWORD="MyStrong_Pass-123"
sp el ami create                                       # ~10-15 min, bake the AMI

# Daily
sp el create-from-ami --wait                           # ~80s, fresh stack
# → poke around in Kibana for an hour
sp el delete --all -y                                  # reclaim the stack

# Weekly (or whenever the schema/dashboard changes)
sp el ami delete <old-ami-id> -y                       # delete old snapshot
sp el ami create                                       # fresh bake
```

That's it.
