# 2026-04-26 — `sp el lets cf inventory` (LETS slice 1) — 3 / 3 — How to use it

This is part three of a three-part debrief on the first LETS slice.

| Part | File |
|------|------|
| 1 — Why we built this | `2026-04-26__lets-cf-inventory__01-why.md` |
| 2 — What we built | `2026-04-26__lets-cf-inventory__02-what.md` |
| 3 — **How to use it** *(this doc)* | `2026-04-26__lets-cf-inventory__03-how-to-use.md` |

---

## Prerequisites

```bash
# 1. AWS credentials with EC2 + IAM + SSM + S3-read permissions
aws sts get-caller-identity

# 2. Default region (or pass --region per command)
export AWS_DEFAULT_REGION=eu-west-2

# 3. A strong consistent elastic password — same one used by sp el create
export SG_ELASTIC_PASSWORD="MyStrong_Pass-123"

# 4. The sp CLI on PATH (already installed if you're in the SGraph
#    Playwright repo)
sp el lets cf inventory --help
```

A running Ephemeral Kibana stack is also a prerequisite — `sp el lets cf
inventory` always targets a stack:

```bash
sp el create-from-ami --wait     # ~80s, fastest path on a baked AMI
```

If no AMI exists yet, run `sp el ami create` once (~10-15 min cold bake)
to set one up.

---

## The three flows

### Flow A — First time / one day's data (dry-run, then real)

Always sanity-check with `--dry-run` before the first real load — it lists
the bucket and parses every filename without touching Elastic.

```bash
# Dry-run first to confirm the listing works
sp el lets cf inventory load --prefix cloudfront-realtime/2026/04/25/ --dry-run

# Output ends with something like:
#   pages-listed     1
#   objects-scanned  425
#   bytes-total      633,091
#   wall-time        489 ms
#   (dry-run)
```

If that looks right, drop the flag for the real load:

```bash
sp el lets cf inventory load --prefix cloudfront-realtime/2026/04/25/

# Output:
#   pages-listed     1
#   objects-scanned  425
#   objects-indexed  425
#   objects-updated  0
#   bytes-total      633,091
#   wall-time        2097 ms
#   http-status      200
#   kibana-url       https://3.10.246.233/app/dashboards
#
#   ✓  Open Kibana Discover at https://3.10.246.233/app/discover
```

Open the URL.  Kibana → Dashboards → "CloudFront Logs - Inventory Overview"
shows the auto-imported 5-panel view.

### Flow B — Multi-day load (the "eventually all of it" path)

```bash
# A whole month — Phase 5's daily-rolling indices kick in:
sp el lets cf inventory load --prefix cloudfront-realtime/2026/04/

# Output ends with:
#   sg-cf-inventory-2026-04-23  → 250 docs
#   sg-cf-inventory-2026-04-24  → 380 docs
#   sg-cf-inventory-2026-04-25  → 425 docs
#   sg-cf-inventory-2026-04-26  → ~150 docs (partial — today)
#   ...
```

Each delivery date gets its own index.  The dashboard binds to the
wildcard `sg-cf-inventory-*` and stitches the time-series automatically.

For the full bucket walk:

```bash
sp el lets cf inventory load --all
```

Use `--max-keys 100` first to validate behaviour before committing to a
full scan.

### Flow C — Iterate the load → wipe loop

The matched pair is a first-class developer flow:

```bash
sp el lets cf inventory load --prefix cloudfront-realtime/2026/04/25/
# ... tweak the dashboard / re-index something ...
sp el lets cf inventory wipe -y
sp el lets cf inventory load --prefix cloudfront-realtime/2026/04/25/

# Same data, fresh dashboard, no leftover saved-objects.
```

A second wipe with nothing to clean is harmless — `wipe -y` reports
all-zeros.

---

## Daily commands

### Inspecting

```bash
sp el lets cf inventory list                  # all runs in a Rich table
sp el lets cf inventory list --top 10         # cap at 10 most-recent runs
sp el lets cf inventory health                # 3-check status (mirrors `sp el health`)
```

`list` example output:

```
  Pipeline runs on elastic-witty-lovelace

  Run id                                    Objects   Bytes      Delivery range          Loaded at
  20260426T103042Z-cf-realtime-load-a3f2    425       633,091    2026-04-25              2026-04-26 10:30:48
  20260426T100015Z-cf-realtime-load-7e21    380       540,000    2026-04-24              2026-04-26 10:00:21

  2 run(s)
```

`health` example after a successful load:

```
  ✓  Inventory health for elastic-witty-lovelace

     Check       Detail
  ✓  indices     1 index(es) match sg-cf-inventory-*
  ✓  data-view   sg-cf-inventory-* present
  ✓  dashboard   sg-cf-inventory-overview present
```

After a wipe:

```
  ⚠  Inventory health for elastic-witty-lovelace

     Check       Detail
  ⚠  indices     no indices match sg-cf-inventory-* - run `sp el lets cf inventory load`
  ⚠  data-view   sg-cf-inventory-* not found - load creates it idempotently
  ⚠  dashboard   sg-cf-inventory-overview not found - load imports it idempotently
```

WARN doesn't flip the rollup to FAIL — these states are recoverable by
running `load`.

### Combining with hand-built Lens dashboards

The auto-imported dashboard ("CloudFront Logs - Inventory Overview") is a
baseline.  You can build richer Lens dashboards on top of the same
`sg-cf-inventory-*` data view, export them, and replay them on any future
stack:

```bash
# Build it once in Kibana UI on stack A, then export:
sp el dashboard export <dashboard-id-or-title> -o my-cf-dashboard.json

# Tear stack A down:
sp el delete --all -y

# On a fresh stack (later, possibly different EC2):
sp el create-from-ami --wait
sp el lets cf inventory load --prefix cloudfront-realtime/2026/04/25/
sp el dashboard import my-cf-dashboard.json

# Both dashboards now in Kibana:
sp el dashboard list
#   • CloudFront Logs - Inventory Overview     (auto-imported by `load`)
#   • <your Lens dashboard>                    (re-imported via dashboard import)
#   • Synthetic Logs Overview                  (existed from `sp el seed`)
```

The Lens dashboard's data binding **auto-rebinds by data-view title-match**,
so it just works on the new stack.  Confirmed end-to-end during slice 1
smoke.  No UUID surgery required.

---

## Common failures and what they mean

### `ValueError: Invalid endpoint: https://s3..amazonaws.com`

You're not on a network where boto3 can resolve a region.  Fix:

```bash
export AWS_DEFAULT_REGION=eu-west-2
```

Or pass `--region eu-west-2` to the command directly.

### `Wildcard expressions or all indices are not allowed` from wipe

You're on a pre-fix build.  Pull `git pull` and re-run.  ES rejects
wildcard DELETE; the wipe code now iterates per-index.

### Kibana Dashboards page shows no auto-imported dashboard

The data view ensure step failed silently (e.g. wrong password).  The
loader skips the dashboard import when `ensure_data_view` errors — it has
no view-id to bind panels to.

```bash
sp el lets cf inventory health     # data-view check will WARN/FAIL
# If it warns: just re-run load.
# If it fails with HTTP 401/403: SG_ELASTIC_PASSWORD doesn't match the stack.
```

### Discover shows "No fields exist in this data view"

You're on a pre-fix build (data view title was the literal `sg-cf-inventory`,
no wildcard).  Pull and re-run `wipe -y` then `load`.

### Storage class panel shows red triangle

You're on a pre-fix build (terms agg was on `storage_class` not
`storage_class.keyword`).  Pull and re-load — `load` re-imports the
dashboard idempotently with overwrite=true.

### `sp el lets cf inventory load` hangs / times out

Almost always the IP-rotation issue from the `sp el` lifecycle.  Diagnose:

```bash
sp el health
# → sg-ingress: FAIL with "current IP X.X.X.X not in allowed CIDRs ['Y.Y.Y.Y/32']"
```

Two ways to fix:

```bash
# A. Recreate the stack with your current IP baked in:
sp el delete --all -y && sp el create-from-ami --wait

# B. (Future, when sp el forward ships) tunnel via SSM to bypass the SG:
#    sp el forward --service nginx --local-port 8443
```

---

## Tips and shortcuts

- **`sp el` aliases.**  `sp elastic` and `sp el` are identical.  All
  `sp el lets cf inventory ...` commands also work as `sp elastic lets cf
  inventory ...`.
- **Stack auto-pick.**  Every command takes an optional positional stack
  name.  When only one stack exists, it's auto-picked; with multiple,
  you'll be prompted.  Pass the name to skip.
- **Idempotency.**  `load`, `wipe`, `health` are all safe to re-run.
  `load` uses `overwrite=true` for the dashboard ensure and `_id = etag`
  for docs — re-running over the same prefix updates rather than
  duplicates.  `wipe` reports zeros on the second invocation.
- **Cost.**  No additional cost beyond the existing Ephemeral Kibana stack
  (~$0.19/hour on `m6i.xlarge`).  S3 ListObjectsV2 calls are free at this
  volume; bulk-posts are local to the stack.

## Anti-patterns

- **Don't run `--all` without a `--max-keys` cap on first attempt.**
  ListObjectsV2 is paginated but un-capped on a multi-thousand-object
  bucket can run for minutes.  Use `--max-keys 1000` first.
- **Don't expect `wipe` to clean up your hand-built Lens dashboards.**
  `wipe` only removes the auto-generated dashboard's deterministic IDs
  (`sg-cf-inventory-overview` etc.) and the data view.  Your Lens
  dashboards survive but their data binding will reconnect on the next
  `load` (the data view comes back with the same wildcard title).
- **Don't run `load` against a stack with no AWS credentials configured
  on the laptop.**  S3 listing happens client-side, so the laptop needs
  AWS creds — even though the bulk-post part runs against EC2.

## Recommended starter recipe

```bash
# Once
export AWS_DEFAULT_REGION=eu-west-2
export SG_ELASTIC_PASSWORD="MyStrong_Pass-123"
sp el ami create                                   # ~10-15 min, bake the AMI

# Daily
sp el create-from-ami --wait                       # ~80s
sp el lets cf inventory load                       # default = today UTC's data
# → poke around in Kibana for an hour
sp el delete --all -y                              # reclaim the stack

# Weekly (when the schema/dashboard changes)
sp el ami delete <old-ami-id> -y
sp el ami create                                   # fresh bake including the latest LETS module
```

That's it.