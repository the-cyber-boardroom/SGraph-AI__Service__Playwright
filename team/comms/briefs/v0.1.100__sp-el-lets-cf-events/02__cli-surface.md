# 02 — CLI surface

All commands nest under `sp el lets cf events`, sibling to the existing
`sp el lets cf inventory`.  Same auto-pick / `--stack` conventions.

---

## Commands

```
sp el lets cf events load   [--prefix Y[/M[/D]]] [--all] [--max-files N]
                             [--from-inventory] [--run-id ID]
                             [--bucket B] [--password P] [--region R]
                             [--dry-run]
sp el lets cf events wipe   [-y] [--password P] [--region R]
sp el lets cf events list                          [--top N] [--password P] [--region R]
sp el lets cf events health                                  [--password P] [--region R]
```

Same four-verb shape as `inventory` — `load` / `wipe` matched pair, two
read-only verbs.

---

## `load` semantics

Order of operations:

1. **Resolve** stack → `kibana_url` (existing helper)
2. **Pick the work queue** — two modes:
   - **Default (S3-listing mode)**: list S3 under the chosen prefix
     (same `S3__Inventory__Lister` as slice 1, reused).  All listed files
     are work.
   - **`--from-inventory` mode**: query Elastic for inventory docs where
     `content_processed=false` (ordered by `delivery_at` desc, capped by
     `--max-files`).  Each result row is one file to fetch.  This is the
     manifest-driven path that pays off slice 1's `content_processed` hook.
3. **Ensure** Kibana data view `sg-cf-events-*` (idempotent)
4. **Build & import** the dashboard ndjson (idempotent, overwrite=true)
5. **Per file:**
   - `s3:GetObject` → bytes
   - `gzip.decompress(bytes)` → TSV string
   - Split lines → list of TSV rows
   - For each row: parse → Stage-1-clean → `Schema__CF__Event__Record`
     with `_id = "{etag}__{line_index}"`, `source_etag = etag`,
     `pipeline_run_id`, `loaded_at`
   - Bulk-post the file's records to the per-day index
     `sg-cf-events-{YYYY-MM-DD}` (keyed on each event's `timestamp[:10]`)
6. **After each file**: update the inventory doc by etag — set
   `content_processed=true`, stamp `content_extract_run_id`
7. **Return** `Schema__Events__Load__Response`

`--max-files` (note: not `--max-keys` — different unit) caps the file
count, not the event count.  ~100 events per file in this dataset, so
`--max-files 10` ≈ 1000 events.

`--dry-run` does steps 1-3 + listing/queue-building, but skips fetch +
bulk-post + inventory update.  Just reports "would have processed N files
totalling M bytes".

---

## The `--from-inventory` flag — manifest-driven path

This is what makes slice 2 worth the architecture investment.  Instead of:

```bash
# Re-list S3, fetch every .gz, hope nothing was already processed
sp el lets cf events load --prefix cloudfront-realtime/2026/04/
```

You can do:

```bash
# Only fetch what hasn't been processed yet
sp el lets cf events load --from-inventory --max-files 50
```

The loader queries Elastic:
```
POST /sg-cf-inventory-*/_search
{
  "size": 50,
  "query": { "term": { "content_processed": false } },
  "sort": [ { "delivery_at": "desc" } ],
  "_source": [ "bucket", "key", "etag", "size_bytes", "delivery_at" ]
}
```

Each hit is one file to fetch.  After processing, the inventory doc is
updated to `content_processed=true`, so the next `--from-inventory` run
sees a smaller queue.

**This is the `Schema__S3__Object__Record.content_processed` field paying
off** — slice 1 added it as a forward declaration; slice 2 is its first
writer + first reader.

Daily refresh recipe:
```bash
sp el lets cf inventory load                     # list today's S3 → mark new files content_processed=false
sp el lets cf events load --from-inventory       # fetch + parse only the new ones
```

Idempotent across re-runs: a file that's already been processed has
`content_processed=true`, so it's not in the next queue.

---

## `wipe` semantics

Same shape as inventory's wipe, applied to events artifacts:

1. Delete every `sg-cf-events-*` index (per-name, not wildcard — same
   `delete_indices_by_pattern` from slice 1)
2. Delete the data view title `sg-cf-events-*`
3. Delete the dashboard `sg-cf-events-overview` + its visualisations
   (deterministic IDs)
4. **Reset the manifest** — `_update_by_query` against `sg-cf-inventory-*`
   to flip every `content_processed=true` back to `false`.  This way,
   the next `events load --from-inventory` finds the full queue again.

Idempotent.  `wipe -y` followed by `wipe -y` reports zeros.

---

## Read-only verbs

**`list`** — distinct `pipeline_run_id` values from `sg-cf-events-*` with
per-run summary (event count, byte sum, source file count, time range).
Same shape as inventory's `list`, different agg fields.

**`health`** — three checks parallel to inventory:
1. `events-indices`: at least one `sg-cf-events-*` index exists
2. `events-data-view`: data view `sg-cf-events-*` exists
3. `events-dashboard`: dashboard `sg-cf-events-overview` exists

Plus a fourth bonus check that's only meaningful for events:

4. `inventory-link`: count of inventory docs where `content_processed=true`
   vs `content_processed=false` — surfaces "X files processed of Y in
   inventory" so you can see at a glance how complete the events index is

WARN doesn't flip the rollup; only FAIL does.

---

## Examples

```bash
# First time, today's events
sp el lets cf events load

# Backfill a month from the manifest
sp el lets cf inventory load --prefix cloudfront-realtime/2026/04/
sp el lets cf events load --from-inventory --max-files 100

# Iterate the loop
sp el lets cf events load --max-files 10 --dry-run     # see what would happen
sp el lets cf events load --max-files 10               # do it
sp el lets cf events list                              # confirm the run
sp el lets cf events wipe -y                           # reset
sp el lets cf events load --from-inventory             # re-fetch from manifest
```
