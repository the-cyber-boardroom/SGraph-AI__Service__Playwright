# 09 — LETS Workflow Taxonomy

**Status:** 🟡 STUB — to be expanded by Sonnet in Phase 0
**Important constraint:** This doc is **vocabulary only**, NOT a roadmap commitment. Do NOT extract a generic base class in this slice (see slice-specific rule R-7 in the kickoff prompt).

---

## Purpose of this doc

Name the three categories of LETS workflow — **consolidate**, **compress**, **expand** — so future briefs can reference them with shared vocabulary. Document the shared scaffolding the three categories use (8 steps), making it easy to spot when a future workflow falls into a known category.

This doc explicitly does NOT:

- Implement a generic `Lets__Workflow__Loader` base class
- Commit to a delivery date for any future workflow
- Specify schemas for any future workflow

It DOES:

- Define the three categories with concrete examples
- List the shared scaffolding observed across all three
- Identify candidates inside the SGraph ecosystem that would benefit from each

---

## Sections to include

### 1. The three workflow types

Cross-reference the diagram in the README §"LETS workflow taxonomy":

- **📦 CONSOLIDATE** — many small immutable units → one bigger artefact. Fewer files, same total bytes (or smaller). Shape preserved per-record. *This slice is the first instance.*
- **🗜️ COMPRESS** — records → aggregations / rollups. Fewer records, less detail. Shape changes — schema becomes denser.
- **📈 EXPAND** — one record → many derivatives. More artefacts, more detail. Shape changes — one input produces a graph of outputs.

For each type, expand to ~half a page with:

- Pattern signature (what tells you this is the right category)
- Concrete worked example
- Why the LETS principle is honoured

### 2. The shared scaffolding (8 steps)

Restate the 8 steps from the README §"All three share the same scaffolding":

```
  1. Read lets-config.json at compat-region root
  2. Resolve work queue (from inventory, from manifest, from previous workflow output, …)
  3. Loop: per-input → transform → write output
  4. Persist output to a new compat region
  5. Write per-day manifest sidecar
  6. Index manifest doc into Elastic
  7. Flip a "this was processed" flag on the source
  8. Record one Schema__Pipeline__Run journal entry
```

For each step, identify which existing class provides it in this slice:

| Step | Provided by (in this slice) |
|------|------------------------------|
| 1 | `Lets__Config__Reader` |
| 2 | `S3__Inventory__Lister` + `Inventory__Manifest__Reader` |
| 3 | `Consolidate__Loader` (orchestrating the loop) |
| 4 | `S3__Object__Writer` |
| 5 | `Manifest__Builder` + `S3__Object__Writer` |
| 6 | `Inventory__HTTP__Client` |
| 7 | `Inventory__Manifest__Updater` |
| 8 | `Pipeline__Runs__Tracker` |

### 3. Concrete future workflows worth flagging

Cross-reference the table in the README §"LETS workflow taxonomy"; expand each row into a paragraph-length sketch:

#### `consolidate mitm-flows`
- Input: mitmproxy session dumps (one file per HTTP flow recorded during a session)
- Output: `flows.ndjson.gz` per session
- Why it matters: investigation sessions today produce 100s of small files; one consolidated artefact per session unlocks fast Kibana exploration

#### `consolidate playwright-sessions`
- Input: per-page artefact bundles (HAR + screenshots + traces + console logs)
- Output: `session.ndjson.gz` plus an `assets/` sub-prefix for binaries (screenshots, video)
- Why it matters: the per-page-and-per-resource artefact count balloons quickly; consolidation makes a session greppable

#### `compress cf-hourly-rollup`
- Input: consolidated events (output of THIS slice)
- Output: `hourly-rollup.ndjson` — one doc per hour with pre-aggregated panels (top URIs, top UAs, status code distribution, bot ratio)
- Why it matters: Kibana panels become instant for the rollup view; full detail is still available via the events index when needed

#### `compress cf-daily-summary`
- Input: consolidated events
- Output: one summary doc per day
- Why it matters: this is the `sg-send report` Tier 3 command, productised as a workflow
- Note: this is what the v0.1.102 orchestrator's `report` command should call, not a separate read-only script

#### `expand mcp-tool-replay`
- Input: tool-call log (one entry per MCP tool invocation)
- Output: replay artefacts (request, response, state delta, env snapshot) per call
- Why it matters: investigation-time forensics — given a failed tool call, regenerate the exact context it ran in

#### `expand cf-event-screenshot`
- Input: event with `404` status (or other anomaly)
- Output: Playwright screenshot of the URI at that timestamp
- Why it matters: debug-aid for production weirdness — "what did this 404 page actually look like?"

### 4. The pattern recognition heuristic

A practical guide for *future Architects* deciding whether a new pipeline maps to one of these three types. Suggested checklist:

```
   Is your input dataset composed of many small immutable units?
       YES → consolidate is likely
       NO  → check the next two

   Does your transform reduce the record count and produce denser docs?
       YES → compress is likely

   Does your transform produce more artefacts than it consumes?
       YES → expand is likely

   None of the above? Probably not a LETS workflow — might be a SQL view,
   a streaming pipeline, or just a script.
```

### 5. Why we name the categories without implementing a base class

This is the heart of the **R-7 anti-abstraction rule** in the kickoff prompt. Premature abstraction at this stage would:

- Lock in design choices before there's evidence (only one concrete instance exists)
- Conflate accidental aspects of consolidation with essential aspects of "all LETS workflows"
- Make the second instance harder to write, not easier (it would have to fit the prematurely-defined base class)

The right move: ship two or three concrete workflows in different categories, *then* extract the abstraction once the shared shape is proven. This matches the standard "Rule of Three" for code abstraction.

When the abstraction does emerge (likely v0.1.105 or later), it'll be obvious what the shape needs to be — and probably different from what we'd have guessed today.

### 6. What this means for v0.1.101

**Nothing tactical.** This doc exists so future briefs can reference "consolidate" / "compress" / "expand" by name. It also exists to prevent Sonnet from prematurely abstracting in this slice (R-7).

The shared-scaffolding table above is observation, not implementation. `Consolidate__Loader` does all 8 steps inline. A future workflow will do all 8 steps inline too. When we have three concrete workflows and the shape is proven, *then* we extract.

---

## Source material

- README §"LETS workflow taxonomy" — the source of truth for the three categories
- `00b__consolidation-lets-pattern.md` §6 — the pattern recognition criteria
- `00b__consolidation-lets-pattern.md` §11 — the questions raised on the broader pattern

---

## Target length

~120–160 lines.
