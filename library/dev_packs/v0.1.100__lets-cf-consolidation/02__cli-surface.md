# 02 — CLI Surface

**Status:** 🟡 STUB — to be expanded by Sonnet in Phase 0

---

## Purpose of this doc

Specify every command, flag, default, and console-output shape for the new verbs. Mirror the structure of slice 1's and slice 2's `02__cli-surface.md`.

---

## Sections to include

1. **The new verb tree** — 5 verbs:

   ```
   sp el lets cf consolidate load                  Run the C-stage for a date
   sp el lets cf consolidate wipe                  Drop consolidated artefacts + reset flags
   sp el lets cf consolidate list                  Show consolidation runs from the journal
   sp el lets cf consolidate health                Plumbing checks
   sp el lets cf consolidate verify <date>         Read manifest + recompute checksums
   ```

   For each verb: full flag list, defaults, exit codes, sample console output (use slice 2's `events load` Rich-table style as the reference).

2. **The new third queue mode for `events load`** — `--from-consolidated`:

   ```
   sp el lets cf events load --from-consolidated [--prefix YYYY/MM/DD]
   ```

   Full flag interaction matrix with the existing `--from-inventory` and default modes. What happens if you combine flags. What happens if the consolidated artefact for the date doesn't exist (clear error, not silent fallback).

3. **lets-config.json validation behaviour** — every `consolidate` and `--from-consolidated` command checks the compat-region's `lets-config.json` first. Specify:
   - When the file is created (first `consolidate load` for a region)
   - When it's validated (every read)
   - What "incompatible" means (parser_version mismatch, schema_version mismatch, …)
   - What error message the user sees on incompat (concrete sample)

4. **Sample console outputs** — at least one full Rich-table example for each verb. Match the existing inventory/events output style (Step__Timings table at the bottom, Call__Counter summary, run_id link).

5. **--dry-run semantics for each verb** — what `--dry-run` does for each, what it doesn't do.

6. **Auto stack pick** — same behaviour as slice 1/2: if exactly one Ephemeral Kibana stack is running, use it; otherwise require `--stack-id`.

7. **Defaults for `--prefix`** — `consolidate load` defaults to "today UTC" (matches existing slices). `consolidate wipe` defaults to nothing (require explicit date). `verify` requires `<date>` as positional.

---

## Source material

- README §"Architect's locked decisions" (especially #1, #5b, #8, #9, #10)
- `00b__consolidation-lets-pattern.md` §8 (CLI sketch)
- Slice 2 brief: `team/comms/briefs/v0.1.100__sp-el-lets-cf-events/02__cli-surface.md` for shape and tone
- Existing CLI source: `scripts/elastic_lets.py` (slice 1 + 2 verbs already there)

---

## Target length

~120–140 lines, matching slice 2's `02__cli-surface.md`.
