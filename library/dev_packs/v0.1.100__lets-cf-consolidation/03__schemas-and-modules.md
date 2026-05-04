# 03 — Schemas and Modules

**Status:** 🟡 STUB — to be expanded by Sonnet in Phase 0

---

## Purpose of this doc

Specify every new Type_Safe class — enums, primitives, schemas, collections, services — and the module tree they inhabit. Mirror the structure of slice 1's and slice 2's `03__schemas-and-modules.md`.

This is the most important doc for Phase 1 (Type_Safe foundations) — get the surface right here and Phase 1 is straightforward.

---

## Sections to include

1. **Module tree** — full path listing under `sgraph_ai_service_playwright__cli/elastic/lets/cf/consolidate/`. Mirror the inventory/ and events/ folder shape:

   ```
   consolidate/
       __init__.py                            (empty)
       enums/
           __init__.py
           Enum__Lets__Workflow__Type.py      (consolidate / compress / expand)
       primitives/
           __init__.py
           Safe_Str__Lets__Compat__Region.py
           Safe_Str__S3__Output__Key.py
           Safe_Str__Parser__Version.py
       schemas/
           __init__.py
           Schema__Lets__Config.py
           Schema__Lets__Config__Implementations.py
           Schema__Lets__Config__Input__Source.py
           Schema__Lets__Config__Output__Format.py
           Schema__Consolidated__Manifest.py
           Schema__Consolidate__Source.py
           Schema__Consolidate__Run__Summary.py
           Schema__Consolidate__Load__Request.py
           Schema__Consolidate__Load__Response.py
           Schema__Consolidate__Wipe__Request.py
           Schema__Consolidate__Wipe__Response.py
           Schema__Consolidate__Verify__Response.py
       collections/
           __init__.py
           List__Schema__Consolidate__Source.py
           List__Schema__Consolidate__Run__Summary.py
       service/
           __init__.py
           S3__Object__Writer.py                  (boto3 boundary — sibling of Fetcher)
           NDJSON__Writer.py
           NDJSON__Reader.py
           Lets__Config__Reader.py                (validates compat region)
           Lets__Config__Writer.py                (writes config at first use)
           Manifest__Builder.py                   (assembles per-day manifest)
           Consolidate__Loader.py                 (the orchestrator)
           Consolidate__Wiper.py                  (matched-pair wipe)
           Consolidate__Verifier.py               (drift / mismatch detection)
           Consolidated__Dashboard__Builder.py    (1-panel ndjson)
   ```

   Plus **changes to existing classes** (additive only):
   - `Schema__S3__Object__Record` — add `consolidation_run_id`, `consolidated_at` fields (decision #7)
   - `Enum__Pipeline__Verb` — add `CONSOLIDATE` value
   - `Inventory__HTTP__Client` — new optional parameters per §"Elastic optimisations"
   - `Events__Loader` — new `--from-consolidated` queue mode (decision #8)

2. **Schema__Lets__Config — the compatibility-region config** — full field list. Source the JSON example in the README §"S3 layout and config-at-folder-root" — translate it to Type_Safe form. This is the most novel schema in the slice.

3. **Schema__Consolidated__Manifest — the per-day sidecar** — fields: `run_id`, `started_at`, `finished_at`, `source_etags` (List__Safe_Str), `source_count`, `event_count`, `byte_count_input`, `byte_count_output`, `compression_ratio`. Cross-reference decision #5c.

4. **Schema__Consolidate__Source — one entry per consumed source file** — fields: `etag`, `s3_key`, `byte_offset_start`, `byte_offset_end`, `line_count_in_consolidated`. Used so a single line in `events.ndjson.gz` can be traced back to its source `.gz`.

5. **The two new fields on `Schema__S3__Object__Record`** — show diff vs current. Defaults must be backward-compatible (empty string + epoch-zero).

6. **`S3__Object__Writer` — the new boto3 boundary** — interface signature only (Phase 2 implements it). Sibling of `S3__Object__Fetcher`. Methods: `put_object_bytes(bucket, key, data, content_type)`, `put_object_json(bucket, key, payload)`, `head_object(bucket, key)` (for verify-mode existence checks).

7. **Reuse map** — existing classes imported untouched:
   - `S3__Inventory__Lister` (lists source files for the date)
   - `S3__Object__Fetcher` (reads each source)
   - `CF__Realtime__Log__Parser` (TSV → records)
   - `Bot__Classifier` (UA → category)
   - `Inventory__HTTP__Client` (gets new optional params, but existing methods unchanged)
   - `Inventory__Manifest__Updater` (the `terms`-filter `_update_by_query` extension goes here)
   - `Run__Id__Generator`
   - `Pipeline__Runs__Tracker` (gains a new caller, no API change)

8. **Type_Safe checklist for every new class** — explicit confirmation that:
   - No raw primitives in any attribute
   - No Pydantic, dataclass, or plain class
   - No Literals (use Enum__* classes)
   - One class per file
   - File named exactly after the class
   - `__init__.py` empty in every new folder

---

## Source material

- README §"Architect's locked decisions" (especially #5, #5c, #5d, #7, #8, #11)
- `00b__consolidation-lets-pattern.md` §3 (the design diagram showing the data layout)
- `00b__consolidation-lets-pattern.md` §7 (the reusable building blocks list)
- Slice 2 brief: `team/comms/briefs/v0.1.100__sp-el-lets-cf-events/03__schemas-and-modules.md` for shape and tone
- Existing inventory/events module trees as the structural template

---

## Target length

~180–220 lines, matching slice 2's `03__schemas-and-modules.md` (which is the densest doc in slice 2's brief).
