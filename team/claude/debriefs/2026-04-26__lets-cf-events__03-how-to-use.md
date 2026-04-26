# 2026-04-26 — `sp el lets cf events` (LETS slice 2) — 3 / 3 — How to use it

This is part three of the three-part debrief.

| Part | File |
|------|------|
| 1 — Why we built this | `2026-04-26__lets-cf-events__01-why.md` |
| 2 — What we built | `2026-04-26__lets-cf-events__02-what.md` |
| 3 — **How to use it** *(this doc)* | `2026-04-26__lets-cf-events__03-how-to-use.md` |

---

## Prerequisites

Identical to slice 1 — same Ephemeral Kibana, same AWS creds, same
elastic password.

```bash
aws sts get-caller-identity                            # confirm AWS creds
export AWS_DEFAULT_REGION=eu-west-2
export SG_ELASTIC_PASSWORD="MyStrong_Pass-123"
sp el create-from-ami --wait                           # ~80 s — gives us a Kibana stack
```

---

## The two flows

### Flow A — Direct S3-listing mode

Same shape as slice 1's `inventory load`.  Picks files by S3 prefix.

```bash
# Dry-run first (no fetch, no parse, no writes)
sp el lets cf events load --prefix cloudfront-realtime/2026/04/25/ --dry-run --max-files 5

# Real run — fetches 5 files, parses TSV, indexes events, auto-imports the dashboard
sp el lets cf events load --prefix cloudfront-realtime/2026/04/25/ --max-files 5

# Then open Kibana → Dashboards → "CloudFront Logs - Events Overview"
```

Sample output from a real 50-file run during slice 2 phase 4 smoke:

```
  CloudFront events load

            stack    elastic-lucky-maxwell
           run-id    20260426T154435Z-cf-realtime-events-load-eb40
       queue-mode    s3-listing
           bucket    745506449035--sgraph-send-cf-logs--eu-west-2
           prefix    cloudfront-realtime/2026/04/25/
     files-queued    50
  files-processed    50
   events-indexed    565
   events-updated    5
  inventory-flips    0          ← no inventory loaded yet, so nothing to flip
      bytes-total    64,193
        wall-time    11991 ms
      http-status    200
       kibana-url    https://18.175.148.234/app/dashboards
```

### Flow B — Manifest-driven mode (the LETS payoff)

This is what slice 1's `content_processed` field was waiting for.
Daily refresh recipe:

```bash
# 1. Refresh the inventory — this list new .gz files in S3 + adds them
#    with content_processed=false:
sp el lets cf inventory load

# 2. Process only the new ones (the manifest filters for content_processed=false):
sp el lets cf events load --from-inventory --max-files 100
```

Output of step 2 (real run):

```
  CloudFront events load

            stack    elastic-lucky-maxwell
           run-id    20260426T155237Z-cf-realtime-events-load-78f2
       queue-mode    from-inventory                                ← reading manifest
           bucket    745506449035--sgraph-send-cf-logs--eu-west-2
           prefix    (full bucket)                                 ← no prefix in manifest mode
     files-queued    5         ← capped by --max-files
  files-processed    5
   events-indexed    7         ← these particular files have low traffic
   events-updated    0
  inventory-flips    5         ← 5 inventory docs flipped to content_processed=true
      bytes-total    1,971
```

Re-run the same command repeatedly — each time `files-queued` shrinks
by your `--max-files` until the queue is empty.  When `files-queued=0`,
the dataset is fully synced.

### Iteration loop with wipe

`events wipe` takes everything back to a clean slate including resetting
slice 1's manifest, so `from-inventory` finds the full queue again.

```bash
sp el lets cf events load --max-files 5
sp el lets cf events wipe -y
# wipe report:
#   indices-dropped       1
#   data-views-dropped    1
#   saved-objects-dropped 7    ← 1 dashboard + 6 visualisations
#   inventory-resets    425    ← every inventory doc back to content_processed=false
#   duration            300 ms

sp el lets cf events load --from-inventory --max-files 5
# files-queued is back to 5 (or however many --max-files you cap to)
```

---

## Daily commands

### Inspecting

```bash
sp el lets cf events list                  # one row per pipeline_run_id
sp el lets cf events list --top 10
sp el lets cf events health                # 4-check status table
```

`list` example output:

```
  Events runs on elastic-lucky-maxwell

  Run id                                    Events  Files  Bytes    Event range  Loaded at
  20260426T155237Z-cf-realtime-events-load-78f2  7   5      1,971    2026-04-25   2026-04-26 15:52:37
  20260426T154435Z-cf-realtime-events-load-eb40  570 50     64,193   2026-04-25   2026-04-26 15:44:47

  2 run(s)
```

`health` example after a successful load:

```
  ✓  Events health for elastic-lucky-maxwell

     Check               Detail
  ✓  events-indices      1 index(es) match sg-cf-events-*
  ✓  events-data-view    sg-cf-events-* present
  ✓  events-dashboard    sg-cf-events-overview present
  ✓  inventory-link      5 of 425 inventory docs processed (1%)
```

The bonus `inventory-link` row tells you at a glance how complete the
events index is relative to the inventory.

---

## Real-world questions the events dashboard answers

| Question | Panel | KQL filter to dig deeper |
|---|---|---|
| "Any 5xx spike?" | Status code distribution over time | `sc_status_class.keyword: "5xx"` |
| "What fraction is FunctionGeneratedResponse vs origin-served?" | Edge result type breakdown | `x_edge_result_type.keyword: "Hit"` (or Miss / Error / etc.) |
| "What's getting hammered most?" | Top URIs | `cs_uri_stem.keyword: "/api/v1/users"` |
| "Where are bots coming from?" | Geographic distribution + `is_bot:true` filter | `is_bot: true and c_country.keyword: "US"` |
| "P99 latency drift?" | Time-taken percentiles over time | `time_taken_ms > 1000` |
| "Bot vs human ratio in last 24h?" | Bot vs human ratio over time | `bot_category.keyword: "bot_known"` |
| "Which `.gz` produced the most events?" | (Discover) | `terms(source_etag.keyword)` agg |

---

## Combining with hand-built Lens dashboards

Same round trip slice 1 proved.  Build a Lens dashboard in Kibana UI on
top of the `sg-cf-events-*` data view, export, replay anywhere:

```bash
# Build it once in Kibana UI on stack A:
sp el dashboard export <id-or-title> -o my-events-dashboard.json

# On a fresh stack:
sp el delete --all -y
sp el create-from-ami --wait
sp el lets cf events load --prefix cloudfront-realtime/2026/04/25/  # creates auto-dashboard + indexes events
sp el dashboard import my-events-dashboard.json                     # adds your Lens dashboard alongside

sp el dashboard list
#   • CloudFront Logs - Events Overview          (auto-imported by Phase 6 builder)
#   • CloudFront Logs - Inventory Overview       (auto-imported by slice 1)
#   • Synthetic Logs Overview                    (existed from sp el seed)
#   • <your Lens events dashboard>               (just imported)
```

---

## Common failures

### "ConnectTimeout" / hangs on health
Same as slice 1: your IP rotated.  `sp el delete --all -y && sp el
create-from-ami --wait`, OR use `sp el forward --service kibana` to
tunnel via SSM.

### `inventory-link` shows 0% after running events load
The events load was in S3-listing mode (default), not `--from-inventory`.
S3-listing mode does NOT update the inventory manifest (it doesn't
know which inventory doc to flip).  To get coverage:

```bash
sp el lets cf events wipe -y                 # resets manifest + drops events
sp el lets cf inventory load                 # populates inventory
sp el lets cf events load --from-inventory   # processes via manifest, flips flags
```

### "events-updated: N" on what should be a fresh stack
Two causes:
- You ran the command twice — the second run finds the same etag+line_index
  combos already there.  Each subsequent run should keep the count growing
  if there are net-new events; flat counts mean the data is stable.
- Two `.gz` files in the bucket have the same etag (rare; CloudFront
  buffer-flush timing edge case).

### Dashboard renders with empty panels
The data view ensure must have failed — check `sp el lets cf events
health`.  If `events-data-view` is WARN, the dashboard import will have
been skipped (no data view id to bind panels to).  Re-run `events load`.

### Storage class panel red triangle (unlikely; pinned by tests)
The slice 1 lesson is regression-tested in slice 2 too — the dashboard
builder asserts every string-typed terms-agg field ends with `.keyword`.
If this surfaces, it's a new field that was added without `.keyword`;
the test should fail in CI before reaching the dashboard.

---

## Tips and shortcuts

- **`from-inventory` is incremental.**  Run it daily — each run only
  fetches new files.  Cron-ready.
- **`events list` shows file_count via cardinality on source_etag.**
  Useful "did the run process the expected number of files?" check.
- **`events health` rollup is one icon.**  If you see ⚠ in the rollup,
  scan the table for the WARN row; usually it's "data view not found"
  which means just re-run load.
- **Bot classifier is extensible.**  Subclass `Bot__Classifier` and
  add to `KNOWN_BOT_PATTERNS` / `GENERIC_BOT_PATTERNS` for new bots.

## Anti-patterns

- **Don't run `--from-inventory` without first running `inventory load`.**
  Empty inventory → empty queue → no work done.
- **Don't run `--all` without a `--max-files` cap on the first attempt.**
  Multi-thousand-file fetch could take many minutes.
- **Don't expect events `wipe` to leave inventory's `content_processed`
  alone.**  It deliberately resets the manifest so `from-inventory`
  finds the full queue again.  If you only want to clear the events
  index without touching the manifest, manually `DELETE` the events
  indices via Kibana Index Management.

## Recommended starter recipe

```bash
# Once
export AWS_DEFAULT_REGION=eu-west-2
export SG_ELASTIC_PASSWORD="MyStrong_Pass-123"
sp el ami create                                               # ~10-15 min, bake the AMI

# Daily
sp el create-from-ami --wait                                   # ~80s
sp el lets cf inventory load                                   # ~2.5s, marks new files content_processed=false
sp el lets cf events    load --from-inventory --max-files 100  # processes only new, flips flags
sp el lets cf events    health                                 # confirms the round trip
# → poke around in Kibana for an hour
sp el delete --all -y                                          # reclaim the stack

# Weekly
sp el ami delete <old-ami-id> -y
sp el ami create
```

That's it.