# 2026-04-26 — `sp el lets cf inventory` (LETS slice 1) — 1 / 3 — Why we built this

This is part one of a three-part debrief on the first LETS slice on the
Ephemeral Kibana stack.

| Part | File |
|------|------|
| 1 — **Why we built this** *(this doc)* | `2026-04-26__lets-cf-inventory__01-why.md` |
| 2 — What we built | `2026-04-26__lets-cf-inventory__02-what.md` |
| 3 — How to use it | `2026-04-26__lets-cf-inventory__03-how-to-use.md` |

---

## The problem

The previous slice (sp-elastic-kibana, 2026-04-25) shipped **the cluster** —
single-command lifecycle for an ephemeral Elasticsearch + Kibana on EC2
that you spin up, demo, and tear down.  Beautiful, but it was empty.  The
seeded "Synthetic Logs Overview" dashboard demonstrated the plumbing but
not real signal.

Meanwhile, AWS Firehose has been writing CloudFront real-time logs to S3
(`s3://745506449035--sgraph-send-cf-logs--eu-west-2/cloudfront-realtime/`)
for weeks.  ~300-400 `.gz` objects per day, sub-2KB each, all sitting there
unread.  We had no operational view into:

- volume over time (is the site getting more or less traffic?)
- delivery cadence (are logs arriving on schedule, or are there gaps?)
- who's hitting it (Firehose preserves country code + bot-distinguishing
  user-agent suffixes inside the .gz contents — but we couldn't see any of
  that without tooling)

The gap: **a way to point the Ephemeral Kibana at this real bucket**, see
what's there, and discard the stack when done.

## What "LETS" means here

The user's [LETS architecture](https://github.com/owasp-sbot/MGraph-AI/...)
(Load, Extract, Transform, Save) framing was the missing organising
principle:

> *"Persist Everything Important BEFORE Indexing Anything.  Elasticsearch
> is NOT the source of truth — it is an index, a cache, a search layer, a
> visualisation layer."*

That principle has two consequences for this slice:

1. **The `cloudfront-realtime/` S3 bucket IS the Load layer.** Firehose
   writes immutable, gzipped, date-partitioned objects there.  We don't
   re-copy or re-format them.  We treat the bucket as already-canonical
   raw input.
2. **The data inside Kibana is throwaway by design.** Every `load` has a
   matched `wipe`.  Either the index is rebuilt from S3 (re-run `load`)
   or the entire stack is rebuilt from an AMI and `load` is re-run.  No
   state lives only in Kibana.

Slice 1 ships the smallest possible vertical pass that proves both
properties end-to-end.

## Why metadata-only on slice 1

Three reasons the *first* pass uses S3 listing metadata only and never
fetches a `.gz`:

1. **Cost shape is right.** ListObjectsV2 is one paginated call per 1000
   objects; GetObject is one round-trip per file.  For ~375 files/day the
   listing fits in one page and no GetObject calls are needed.  Tiny
   blast radius if anything's wrong.
2. **Stage 1 (security cleaning) has no work to do on metadata.** The
   realtime-log export config has already pre-stripped `c-ip`,
   `x-forwarded-for`, `cs-cookie`, and `cs-uri-query`.  Nothing PII-bearing
   remains in the listing surface.  Letting us defer the cleaning module
   to slice 2 without faking it.
3. **The inventory itself is a useful manifest.** Once the inventory is in
   Elastic with a `content_processed` flag, slice 2 can iterate that
   manifest instead of re-listing S3 to decide what to fetch.  The manifest
   pays for itself even before slice 2 ships.

## Alternative paths considered

| Option | Why it didn't fit |
|--------|-------------------|
| **Lambda-based ingest** (the obvious cloud-native shape) | Adds a permanent service to maintain.  Doesn't compose with the "ephemeral cluster" guarantee — Lambda would keep writing to a destination that doesn't exist when the stack is dead. |
| **AWS Athena over S3 directly** | Athena solves a different problem (ad-hoc SQL, no index).  Doesn't give a Kibana-shaped UI for browsing files; doesn't give a programmatic dashboard surface. |
| **Just `aws s3 ls --recursive` to a CSV** | Fine for a one-shot.  Doesn't give time-series visualisations; doesn't generalise to a second source; doesn't give the LETS-shaped manifest that slice 2 will need. |
| **Logstash / Filebeat → Kibana** | Permanent pipeline service.  Requires a node to babysit.  Anti-thesis of the "ephemeral cluster" property the previous slice fought hard for. |

The chosen shape — typed Python service classes + thin Typer CLI + the
existing Ephemeral Kibana — gets us to "real signal in Kibana from real S3
data, kill it, repeat" with no permanent footprint.

## What "good" looks like

The slice is "done" when:

- [x] One command loads today's S3 inventory metadata into Kibana
- [x] One command wipes everything the load created
- [x] `load → wipe → load` returns to identical state both times
- [x] The auto-imported dashboard renders 5 populated panels with no
      manual click-through
- [x] Test coverage for every service path with no mocks (150 unit tests)
- [x] A human-built Lens dashboard, exported via `sp el dashboard export`,
      re-imported via `sp el dashboard import`, lights up against the
      same `sg-cf-inventory-*` data view (auto-rebound by title-match)
- [x] No regression in the 165 existing elastic tests
- [x] Side-effect surface ≤ 1 modification to one existing production
      file (`scripts/elastic.py` — 2 additive lines for the Typer mount)

All boxes ticked.

## Open follow-ups

Things noted during the slice but explicitly out of scope, in rough
priority order:

1. **`.gz` content reads (slice 2 — the "events" verb)** — fetch each
   `.gz` via GetObject, parse the TSV, write `sg-cf-events-*` with
   parsed CloudFront fields (sc-status, c-country, x-edge-result-type,
   user-agent classification, etc.).  Updates the inventory doc to
   `content_processed: true` + stamps `content_extract_run_id`.

2. **`sp el forward`** — SSM port-forwarding for kibana / elastic / nginx.
   ~30 lines.  Useful when corporate networks block :443 (which is the
   only way to reach the ephemeral Kibana from outside) — SSM goes via
   the AWS API path so it bypasses the SG entirely.  Forwarding the
   inner Kibana on 5601 also bypasses the self-signed-cert pain.

   Implementation sketch:
   ```
   sp el forward [STACK] [--service kibana|elastic|nginx]
                 [--local-port N]  # default = remote
                 [--region R]
   ```
   Mechanics: resolve stack → instance_id (existing helper); pick remote
   port from `--service` (5601/9200/443); shell out to `aws ssm
   start-session --document-name AWS-StartPortForwardingSession`.

3. **`sp el health` — better hint when tcp-443 fails** — append "OR port
   443 may be blocked on this network — try `sp el forward`" to the
   existing `Likely fix:` block.  Two lines in `cmd_health`.

4. **LETS Save layer** — `lets/save/{run_id}/manifest.json` + Playwright
   dashboard screenshot → S3 vault.  Decouples the dashboards from the
   live Kibana so analysis snapshots survive `sp el delete --all`.
   Pairs naturally with slice 2 (gives the events-pass a place to drop
   its run summary).

5. **FastAPI duality** — mirror every `sp el lets cf inventory` verb as an
   HTTP route on `Fast_API__SP__CLI` so the daily morning load can be a
   scheduled HTTP POST from GitHub Actions.

6. **Second source** — pick: agent_mitmproxy audit log, sgraph-send app
   logs, or another CloudFront distribution.  Drives a source registry
   and shakes out the `cf`-specific assumptions baked into slice 1.

7. **Per-doc index template** — slice 1 relies on ES auto-mapping for the
   indexed-doc fields.  Auto-mapping was correct except for the well-known
   "string fields need `.keyword` for terms aggs" gotcha (caught in
   smoke).  An explicit index template would make the schema decisions
   visible in code and prevent a recurrence on future schema additions.

See part 2 ("What we built") for the full inventory and part 3 ("How to
use it") for the user-facing recipes.