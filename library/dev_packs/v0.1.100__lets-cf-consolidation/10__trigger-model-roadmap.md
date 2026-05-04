# 10 — Trigger Model Roadmap

**Status:** 🟡 STUB — to be expanded by Sonnet in Phase 0
**Important constraint:** This doc is **architecture-shaping, not v0.1.101 deliverable**. Do NOT write any cron / Lambda / S3-event / GitHub Actions code in this slice. The doc captures the architectural invariants v0.1.101 must satisfy so future trigger surfaces are easy to add.

---

## Purpose of this doc

Map the maturity path from manual CLI today → scheduled cron → S3-event-triggered Lambda. Identify the architectural invariants v0.1.101 must satisfy to enable each future stage without rewriting the loader.

---

## Sections to include

### 1. The three-stage maturity path

Cross-reference the diagram in the README §"Trigger model roadmap":

```
   Today (v0.1.101)        Soon (v0.1.103+)        Eventually
   ────────────────        ─────────────────       ──────────
   Manual CLI       →      Scheduled cron     →    Triggered (S3 event)
```

For each stage, document:

- **Trigger surface** — who/what fires the workflow
- **Concrete implementation sketch** — code shape, no actual code
- **Operational concerns** — observability, retry, alerting, cost
- **Coordination point** — how this stage knows what to do (CLI args, cron config, S3 event filter)

### 2. Stage 1 — Manual CLI (this slice)

- **Trigger surface:** an operator types `sp el lets cf consolidate load` at a terminal
- **Implementation:** Typer wrapper → `Consolidate__Loader.load(request: Schema__Consolidate__Load__Request) → Schema__Consolidate__Load__Response`
- **Observability:** Console output via Rich; journal record in `sg-pipeline-runs-{date}`
- **Coordination point:** CLI flags — operator chooses date, mode, dry-run

### 3. Stage 2 — Scheduled cron (v0.1.103+)

- **Trigger surface:** GitHub Actions workflow with a `schedule:` trigger (`'0 2 * * *'` for 02:00 UTC daily)
- **Implementation sketch:**

  ```yaml
  # .github/workflows/lets-daily-consolidate.yml
  on:
    schedule:
      - cron: '0 2 * * *'

  jobs:
    consolidate:
      runs-on: ubuntu-latest
      steps:
        - checkout
        - install Python deps
        - run: |
            python -c "
            from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.service.Consolidate__Loader import Consolidate__Loader
            from ...schemas.Schema__Consolidate__Load__Request import Schema__Consolidate__Load__Request
            req = Schema__Consolidate__Load__Request(date='yesterday', mode='full')
            resp = Consolidate__Loader().load(req)
            print(resp.json())
            "
  ```

- **Observability:** GH Actions log + journal record; webhook on failure to a Slack channel
- **Retry:** GH Actions native retry (max 3, exponential backoff)
- **Coordination point:** the cron schedule itself; the workflow yaml is the single source of truth for "when does this run"

**Key architectural requirement (from this slice):** `Consolidate__Loader` must be invokable WITHOUT Typer. The Typer wrapper is in the CLI; the service class is plain Python with a Schema__Request input and a Schema__Response output. Decision #14 in the README enforces this.

### 4. Stage 3 — S3-event-triggered Lambda (v0.1.103+ or later)

- **Trigger surface:** S3 PUT events on the source bucket fire SNS → SQS → Lambda
- **Implementation sketch:**

  ```python
  # lambda_handler.py
  def handler(event, context):
      s3_records = parse_sns_to_s3(event)
      for record in s3_records:
          if matches_consolidate_trigger_pattern(record.key):
              req = Schema__Consolidate__Load__Request(
                  date=extract_date(record.key),
                  mode='incremental',
              )
              Consolidate__Loader().load(req)
  ```

- **Observability:** CloudWatch Logs + journal record; alert on Lambda errors
- **Coordination point:** the SNS topic filter + the Lambda's `matches_consolidate_trigger_pattern` predicate. Worth flagging: the `lets-config.json` at the compat-region root is a natural place for this predicate to live, so the Lambda code stays workflow-agnostic.

**Why this is harder than Stage 2:**

1. Lambda has a 15-minute execution limit — long consolidations may need to chunk
2. Cold-start cost matters — the consolidator needs to be fast to instantiate
3. Concurrent invocations — two S3 events fire near-simultaneously, both invoke the Lambda, both try to consolidate the same date. Need an idempotency lock or a SQS de-duplication strategy.

**Architectural requirements (from this slice):** the same as Stage 2, plus:

- `Consolidate__Loader` must accept a `mode='incremental'` (decision deferred to a future v0.1.103+ brief — for now, only `mode='full'` exists)
- The journal must support an "in progress" state to detect concurrent invocations (current `Schema__Pipeline__Run` has `started_at` + `finished_at`; finished_at empty = in progress)

### 5. Architectural invariants this slice locks in

The trigger model is enabled by getting these decisions right today, not by writing trigger code. Specifically:

| Invariant | Where it's enforced in this slice | Future trigger benefits |
|-----------|------------------------------------|-------------------------|
| **Pure service class with Schema-typed I/O** | Decision #11 + #14 | Cron and Lambda both call `.load(Schema__Request) → Schema__Response` directly |
| **No Typer / Console / Rich in service class** | Decision #14 + R-5 | Lambda log capture works automatically (no Rich escape codes) |
| **No global state** | All shared infra is `Type_Safe` instance state (Call__Counter, Pipeline__Runs__Tracker) | Concurrent Lambda invocations don't interfere |
| **Journal entry per run** | Decision #13 — `Pipeline__Runs__Tracker.record_run()` | Cron and Lambda invocations show up in the same journal as manual ones |
| **Idempotency by content-addressing** | Decision #9 — re-runs of the same date with the same parser are byte-identical | Concurrent invocations or replay don't corrupt state |
| **`lets-config.json` at compat-region root** | Decision #5 | Triggers can read the config to know what workflow to instantiate |

### 6. The orchestrator (v0.1.102) inherits this

The `SG_Send__Orchestrator.sync()` method is the same shape that a cron-triggered `SG_Send__Daily__Sync__Lambda` will call. Designing the orchestrator now with that shape in mind costs nothing extra and saves rewriting it later.

Specifically: the orchestrator must NOT take Typer args directly; it must accept a `Schema__SG_Send__Sync__Request`. The Typer wrapper builds the request from CLI args. The cron / Lambda builds the request from environment / event payload. Same service, three trigger surfaces.

### 7. lets-config.json as the trigger coordination point

A non-obvious benefit of decision #5: when triggered execution arrives, the Lambda doesn't need to be hardcoded to a specific workflow. It reads the `lets-config.json` at the compat-region root and instantiates the workflow class named there:

```python
# Far-future Lambda — purely illustrative
config = Lets__Config__Reader().read(s3_key='lets/raw-cf-to-consolidated/lets-config.json')
WorkflowCls = workflow_registry[config.implementations.consolidator]
WorkflowCls().load(request=...)
```

This is one of the reasons the **compat region** is keyed on the workflow type, not on the date. The trigger surface is workflow-aware via the config; the workflow itself stays workflow-specific.

This is **not** in scope for v0.1.101. We do not implement `workflow_registry`. We just don't *prevent* it by getting decision #5 right.

### 8. What this means for Sonnet in v0.1.101

**Nothing tactical.** Don't write a workflow registry. Don't write a cron config. Don't write a Lambda handler. Just satisfy the architectural invariants in §5 above by following decisions #11, #13, #14 and rule R-5 in the kickoff prompt.

If you find yourself wanting to "make it easier for the future trigger" by adding indirection, stop and ask. The invariants above are sufficient.

---

## Source material

- README §"Trigger model roadmap" — the source of truth
- The kickoff prompt's slice-specific rules R-1, R-5, R-7 — they encode the architectural invariants

---

## Target length

~120–180 lines.
