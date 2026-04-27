# 03 — Source Files to Read

Read these before designing the next phase.  They are ordered by conceptual
layer, not alphabet.  The annotations tell you WHY each file matters.

---

## Step 1 — Mandatory orientation

| File | Why |
|------|-----|
| `.claude/CLAUDE.md` | Non-negotiable rules: no mocks, no Pydantic, Type_Safe, one-class-per-file. Read it fully. |
| `team/roles/librarian/reality/v0.1.31/README.md` | Index of the reality doc (NOTE: stale — does not yet list the lets commands; the code is ahead of the doc) |

---

## Step 2 — The LETS CLI surface

| File | Why |
|------|-----|
| `scripts/elastic_lets.py` | **915-line CLI surface.** Shows the complete command tree, all flags, and the `Console__Progress__Reporter` Rich subclass. Read the header comments, then skim each command. |
| `scripts/elastic.py` (lines ~1230–1250) | The 2-line `add_typer` mount — shows how `lets_app` is wired into the parent `sp el` app. |

---

## Step 3 — Slice 1 (inventory) — the foundation

| File | Why |
|------|-----|
| `team/comms/briefs/v0.1.99__sp-el-lets-cf-inventory/01__principle-and-stages.md` | LETS principle explained in full |
| `team/comms/briefs/v0.1.99__sp-el-lets-cf-inventory/02__cli-surface.md` | Spec for the inventory commands |
| `sgraph_ai_service_playwright__cli/elastic/lets/cf/inventory/schemas/Schema__S3__Object__Record.py` | The inventory doc schema — note the `content_processed` and `content_extract_run_id` fields |
| `sgraph_ai_service_playwright__cli/elastic/lets/cf/inventory/service/Inventory__Loader.py` | How `inventory load` is orchestrated — read the step-by-step header comment |
| `sgraph_ai_service_playwright__cli/elastic/lets/cf/inventory/service/Inventory__HTTP__Client.py` | All Elastic HTTP calls. **Reused by slice 2.** |
| `sgraph_ai_service_playwright__cli/elastic/lets/cf/inventory/service/S3__Inventory__Lister.py` | boto3 boundary + `parse_firehose_filename` helper |

---

## Step 4 — Slice 2 (events) — the content layer

| File | Why |
|------|-----|
| `team/comms/briefs/v0.1.100__sp-el-lets-cf-events/02__cli-surface.md` | Spec for events commands; explains `--from-inventory` manifest-driven mode |
| `sgraph_ai_service_playwright__cli/elastic/lets/cf/events/schemas/Schema__CF__Event__Record.py` | The 38-field event record — every field is a typed primitive or enum |
| `sgraph_ai_service_playwright__cli/elastic/lets/cf/events/service/Events__Loader.py` | **Key orchestrator.** Read the header comment step-by-step. Note the per-file error-and-continue logic. |
| `sgraph_ai_service_playwright__cli/elastic/lets/cf/events/service/CF__Realtime__Log__Parser.py` | TSV → record parsing; all the normalisation helpers |
| `sgraph_ai_service_playwright__cli/elastic/lets/cf/events/service/Bot__Classifier.py` | 28 named-bot regexes + 5 generic indicators |
| `sgraph_ai_service_playwright__cli/elastic/lets/cf/events/service/Inventory__Manifest__Reader.py` | Queries inventory for `content_processed=false` |
| `sgraph_ai_service_playwright__cli/elastic/lets/cf/events/service/Inventory__Manifest__Updater.py` | `mark_processed` + `reset_all_processed` |
| `sgraph_ai_service_playwright__cli/elastic/lets/cf/events/service/Progress__Reporter.py` | No-op base class — understand its hooks before designing the orchestrator |

---

## Step 5 — Phase A diagnostics

| File | Why |
|------|-----|
| `sgraph_ai_service_playwright__cli/elastic/lets/Call__Counter.py` | **Read the header comment.** It explicitly says `SG_Send__Orchestrator` will inject a single counter across all collaborators. This is the next class to build. |
| `sgraph_ai_service_playwright__cli/elastic/lets/Step__Timings.py` | Per-file timing — 5 measured steps |

---

## Step 6 — sg-send layer (what exists)

| File | Why |
|------|-----|
| `sgraph_ai_service_playwright__cli/elastic/lets/cf/sg_send/service/SG_Send__Date__Parser.py` | Date parsing helper — `s3_prefix_for_date()` is reusable for a sync command |
| `sgraph_ai_service_playwright__cli/elastic/lets/cf/sg_send/service/SG_Send__Inventory__Query.py` | ES query by date — shows the pattern for reading inventory data |
| `sgraph_ai_service_playwright__cli/elastic/lets/cf/sg_send/service/SG_Send__File__Viewer.py` | Single-file inspect — shows how to reuse the events parser from a thin wrapper |
| `scripts/elastic_lets.py` lines 737–920 | The two sg-send commands as implemented. Note the `Console__Progress__Reporter` above them (~line 55–90) as a pattern for Rich output. |

---

## Step 7 — Tests to understand the in-memory test pattern

| File | Why |
|------|-----|
| `tests/unit/sgraph_ai_service_playwright__cli/elastic/lets/cf/inventory/service/Inventory__HTTP__Client__In_Memory.py` | The in-memory Elastic HTTP client — **this is how all tests work**. No mocks. The in-memory class is the seam. |
| `tests/unit/sgraph_ai_service_playwright__cli/elastic/lets/cf/events/service/S3__Object__Fetcher__In_Memory.py` | Same pattern for S3 |
| `tests/unit/sgraph_ai_service_playwright__cli/elastic/lets/cf/inventory/service/test_Inventory__Loader.py` | How to test an orchestrator. The `SG_Send__Orchestrator` tests should follow this shape. |
| `tests/unit/sgraph_ai_service_playwright__cli/elastic/lets/cf/events/service/test_Events__Loader.py` | Same for the events orchestrator — more complex, shows the `--from-inventory` path. |

---

## Step 8 — Debriefs (for context, not required)

| File | Why |
|------|-----|
| `team/claude/debriefs/2026-04-26__lets-cf-inventory__03-how-to-use.md` | Real-world usage flows for slice 1 |
| `team/claude/debriefs/2026-04-26__lets-cf-events__03-how-to-use.md` | Real-world usage flows for slice 2, incl. the `--from-inventory` daily refresh recipe |

---

## What you do NOT need to read

- The Playwright service itself (`sgraph_ai_service_playwright/`) — the
  `lets` commands are entirely in the CLI sibling package.
- The agent_mitmproxy package.
- The Lambda / Docker / ECR deploy tooling.
- The `sp os`, `sp prom`, `sp vnc` command subtrees (other CLI domains).
