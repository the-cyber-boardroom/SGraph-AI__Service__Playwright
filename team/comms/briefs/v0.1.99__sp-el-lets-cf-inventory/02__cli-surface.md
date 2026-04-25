# 02 — CLI surface

All commands are nested under `sp el lets cf inventory`.  The nesting reflects
the conceptual scope: this work targets a specific Ephemeral Kibana stack
(`sp el`), follows the LETS philosophy (`lets`), pulls from a specific source
(`cf` for CloudFront real-time logs), and operates on a specific use case
(`inventory` — listing-metadata only, vs a future `events` for parsed
content).

The `--stack` flag and the existing auto-pick behaviour from `sp el` apply
unchanged.

---

## Commands (slice 1 scope)

```
sp el lets cf inventory load    [--prefix YYYY[/MM[/DD]]] [--all] [--max-keys N]
                                [--run-id ID] [--stack NAME] [--dry-run]
sp el lets cf inventory wipe    [-y] [--stack NAME]
sp el lets cf inventory list                                     [--stack NAME]
sp el lets cf inventory show    --run-id ID                      [--stack NAME]
sp el lets cf inventory health                                   [--stack NAME]
```

Five verbs, one matched pair (`load` / `wipe`), three read-only inspection
verbs (`list`, `show`, `health`).  No orchestrator / chained `run` verb in
slice 1 — pin individual commands first, prove idempotency, then add chaining.

---

## `load` semantics

Order of operations:

1. **Ensure stack** — auto-pick or `--stack`; bail if no stack is running
   (`sp el create-from-ami --wait` is a precondition).
2. **List S3** — paginated `ListObjectsV2` under the chosen prefix.
3. **Ensure index template + data view + dashboard** — idempotent calls.
   `sg-cf-inventory-template` index template, `sg-cf-inventory-*` data view,
   "CloudFront Logs - Inventory Overview" dashboard saved-objects.  No-op
   if already present.
4. **Stream-build records in memory** — for each S3 object, build one
   `Schema__S3__Object__Record` (no file write).  Stamp:
   - `pipeline_run_id` (the request's run-id or auto-generated)
   - `loaded_at` (UTC ISO-8601, set once per run)
   - `content_processed: false`
5. **Bulk-post in batches** — `Elastic__HTTP__Client.bulk_post()` with
   `_id = etag` so re-loads dedupe at index time.
6. **Return** `Schema__Inventory__Load__Response` with the run summary.

Default scope (no flags): **today, UTC**, prefix
`cloudfront-realtime/{YYYY}/{MM}/{DD}/`. ~375 docs.  Re-running the same day
is a no-op against the index because the etag-as-id collapses duplicates.

`--prefix` accepts progressive granularity:
- `--prefix 2026/04/25` → one day
- `--prefix 2026/04` → one month
- `--prefix 2026` → one year (full history-to-date)
- `--all` → no prefix filter (the "eventually all of it" path)

`--max-keys N` is a safety cap — stop after N objects regardless of prefix.
Useful for first-time runs and for tests.

`--dry-run` lists how many objects would be indexed without bulk-posting.

---

## `wipe` semantics

Order of operations (idempotent — no-op if any artifact is missing):

1. Delete every `sg-cf-inventory-*` index.
2. Delete the `sg-cf-inventory` data view (Kibana saved-object).
3. Delete the "CloudFront Logs - Inventory Overview" dashboard + every
   visualisation saved-object the dashboard import created (current and
   legacy IDs, mirroring the existing `sp el wipe` self-heal pattern).
4. Return `Schema__Inventory__Wipe__Response` with what was actually
   removed (so `wipe` followed by `wipe` reports zero — proves idempotency).

`wipe` does NOT touch the synthetic-data index or the synthetic-data
dashboard.  `sp el wipe` and `sp el lets cf inventory wipe` are independent
verbs operating on independent datasets within the same Kibana.

---

## Read-only verbs

**`list`** — query Elastic for the distinct `pipeline_run_id` values present,
plus per-run summary stats (count, byte sum, prefix scope, started_at).
Renders a Rich table.

**`show --run-id ID`** — render the full per-run summary plus a sample of
docs (e.g. first 5, last 5).

**`health`** — three checks rendered as a small status table:
- Index template `sg-cf-inventory-template` exists?
- Data view `sg-cf-inventory` exists and points at `sg-cf-inventory-*`?
- Dashboard "CloudFront Logs - Inventory Overview" exists with N panels?

`health` is the "is the dataset's plumbing intact" probe — sibling to the
existing `sp el health` (which checks the stack itself).

---

## Examples

```bash
# First time, today's inventory, auto-picked stack
sp el lets cf inventory load

# Last week, one stack
sp el lets cf inventory load --prefix 2026/04/25 --stack elastic-fierce-faraday

# Try before you index
sp el lets cf inventory load --prefix 2026 --dry-run

# Throwaway loop
sp el lets cf inventory load
sp el lets cf inventory wipe -y
sp el lets cf inventory load --prefix 2026/04

# Where am I?
sp el lets cf inventory list
sp el lets cf inventory health
```
