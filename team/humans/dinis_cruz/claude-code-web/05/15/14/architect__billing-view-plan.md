---
title: "Architect Plan — sg aws billing: AWS Spend View"
file: architect__billing-view-plan.md
author: Architect (Claude)
date: 2026-05-15 (UTC hour 14)
repo: SGraph-AI__Service__Playwright @ claude/plan-billing-view-u0NFG
status: PROPOSED — does not exist yet. Plan-only deliverable. All open questions resolved 2026-05-15; ready for Dev pickup pending final ratification.
revisions:
  - 2026-05-15 (UTC hour 14) — initial plan published
  - 2026-05-15 — open questions resolved (see §10 and Revision history)
parallel-to: sgraph_ai_service_playwright__cli/aws/dns/
parent: .claude/CLAUDE.md
---

# Architect Plan — `sg aws billing`: AWS Spend View

> **PROPOSED — does not exist yet.** Every file path, class, schema, command, and IAM permission below is an aspirational design. Nothing in this plan is shipped. Cross-check `team/roles/librarian/reality/` before claiming any of it exists.

---

## 1. Feature Summary (MVP)

A read-only CLI surface that lets the operator inspect current AWS spend from the same terminal they already use for `sg aws dns` and `sg el`. MVP scope:

- **Last 48 hours of spend** — daily granularity (AWS Cost Explorer floor for non-CUR consumers), service breakdown.
- **Last 7 days of spend** — daily granularity, service breakdown, plus a single total.
- **Account-wide totals** — unblended cost, USD, no forecasting, no anomaly detection.
- **By-service breakdown** — top N services by cost, descending; remainder rolled into `OTHER`.
- **CLI output** — Rich table by default, `--json` for machine consumption, mirroring DNS ergonomics exactly.

Out of scope is enumerated in §11.

---

## 2. Parallel to `sg aws dns` — File-for-File Mapping

The DNS sub-package is the template. The billing sub-package mirrors it one-for-one. Where DNS has multiple verifiers/checkers (a domain-specific concern), billing collapses to a single orchestrator because there is no analogue of authoritative-vs-public-resolver fan-out.

| DNS file (today) | Billing file (proposed) | Role |
|---|---|---|
| `aws/dns/cli/Cli__Dns.py` | `aws/billing/cli/Cli__Billing.py` | Typer surface, sub-apps, Rich rendering, no AWS calls |
| `aws/dns/service/Route53__AWS__Client.py` | `aws/billing/service/Cost_Explorer__AWS__Client.py` | Single boto3 boundary, paginates Cost Explorer |
| `aws/dns/service/Route53__Zone__Resolver.py` | `aws/billing/service/Billing__Window__Resolver.py` | Resolves window keywords (`48h`, `week`, `month-to-date`) to `(start, end, granularity)` |
| `aws/dns/service/Route53__Check__Orchestrator.py` | `aws/billing/service/Billing__Report__Builder.py` | Composes a `Schema__Billing__Report` from raw client output |
| `aws/dns/service/Route53__Instance__Linker.py` | (no analogue in MVP — instance-level cost needs CUR) | — |
| `aws/dns/schemas/Schema__Route53__Hosted_Zone.py` | `aws/billing/schemas/Schema__Billing__Line_Item.py` | Pure data schemas |
| `aws/dns/schemas/Schema__Route53__Record.py` | `aws/billing/schemas/Schema__Billing__Report.py` | Pure data schemas |
| `aws/dns/collections/List__Schema__Route53__Record.py` | `aws/billing/collections/List__Schema__Billing__Line_Item.py` | Typed list per rule 21 |
| `aws/dns/enums/Enum__Route53__Record_Type.py` | `aws/billing/enums/Enum__Billing__Granularity.py` | Enum, no Literals |
| `aws/dns/primitives/Safe_Str__Domain_Name.py` | `aws/billing/primitives/Safe_Str__Aws_Service_Code.py` | Domain-specific Safe_* primitives |
| (n/a) | `aws/billing/primitives/Safe_Decimal__Currency__USD.py` | Local USD money primitive — subclasses `osbot_utils ... Safe_Float__Money` (which is `Safe_Float` with `use_decimal=True`, 2 dp). See §10.1 / §4.1 for the codebase scan that resolved this. |
| `aws/cli/Cli__Aws.py` (existing) | edit — adds `app.add_typer(billing_app, name='billing')` | The only cross-package edit |

---

## 3. Proposed File Layout

Strict one-class-per-file (CLAUDE.md rule 21), empty `__init__.py` files (rule 22).

```
sgraph_ai_service_playwright__cli/aws/billing/
  __init__.py
  cli/
    __init__.py
    Cli__Billing.py
  service/
    __init__.py
    Cost_Explorer__AWS__Client.py
    Billing__Window__Resolver.py
    Billing__Report__Builder.py
  schemas/
    __init__.py
    Schema__Billing__Line_Item.py
    Schema__Billing__Group.py
    Schema__Billing__Daily_Bucket.py
    Schema__Billing__Report.py
    Schema__Billing__Window.py
  collections/
    __init__.py
    List__Schema__Billing__Line_Item.py
    List__Schema__Billing__Group.py
    List__Schema__Billing__Daily_Bucket.py
  enums/
    __init__.py
    Enum__Billing__Granularity.py
    Enum__Billing__Window_Keyword.py
    Enum__Billing__Metric.py
    Enum__Billing__Group_By.py
  primitives/
    __init__.py
    Safe_Str__Aws_Service_Code.py
    Safe_Str__Aws_Usage_Type.py
    Safe_Str__Iso8601_Date.py
    Safe_Decimal__Currency__USD.py
```

One edit outside the new package:

- `sgraph_ai_service_playwright__cli/aws/cli/Cli__Aws.py` — register `billing_app`, mirroring the `dns_app` line.

---

## 4. Type_Safe Schemas

All extend `Type_Safe`. Zero raw primitives — `Safe_*`, `Enum__*`, and collection subclasses only. No methods on schemas.

### 4.1 Primitives

| Name | Base | Constraint |
|---|---|---|
| `Safe_Str__Aws_Service_Code` | `Safe_Str` | Cost Explorer `Dimensions.SERVICE` value (e.g. `Amazon Elastic Compute Cloud - Compute`). Length-bounded; allowed charset includes spaces and hyphens. |
| `Safe_Str__Aws_Usage_Type` | `Safe_Str` | Cost Explorer `Dimensions.USAGE_TYPE` value. |
| `Safe_Str__Iso8601_Date` | `Safe_Str` | `YYYY-MM-DD`. Validated by regex in the primitive. |
| `Safe_Decimal__Currency__USD` | `Safe_Float__Money` (osbot-utils, `domains/numerical/safe_float/Safe_Float__Money.py` — `Safe_Float` with `use_decimal=True`, `decimal_places=2`, `min_value=0.0`, `round_output=True`). | Non-negative USD amount. Inherits 2-dp Decimal-backed arithmetic from `Safe_Float__Money`; we override to 4 dp at the boundary to match Cost Explorer precision before bucket totals are summed and re-rounded to 2 dp at render. |

### 4.2 Enums

| Name | Members |
|---|---|
| `Enum__Billing__Granularity` | `HOURLY`, `DAILY`, `MONTHLY` (Cost Explorer values; MVP only uses `DAILY`) |
| `Enum__Billing__Window_Keyword` | `LAST_48H`, `LAST_7D`, `MONTH_TO_DATE` |
| `Enum__Billing__Metric` | `UNBLENDED_COST`, `BLENDED_COST`, `NET_UNBLENDED_COST`, `AMORTIZED_COST` (MVP defaults to `UNBLENDED_COST`) |
| `Enum__Billing__Group_By` | `SERVICE`, `USAGE_TYPE`, `LINKED_ACCOUNT`, `REGION` (MVP exposes `SERVICE` only) |

### 4.3 Schemas

```
Schema__Billing__Window
  start         : Safe_Str__Iso8601_Date    # inclusive
  end           : Safe_Str__Iso8601_Date    # exclusive (Cost Explorer semantics)
  granularity   : Enum__Billing__Granularity
  keyword       : Enum__Billing__Window_Keyword

Schema__Billing__Line_Item                  # one row in a daily bucket, grouped by service
  service       : Safe_Str__Aws_Service_Code
  amount_usd    : Safe_Decimal__Currency__USD
  metric        : Enum__Billing__Metric

Schema__Billing__Group                      # legacy/alt grouping (usage-type, region) — present for forward-compat
  group_key     : str                       # opaque key, kept generic to support multi-dim group-by
  amount_usd    : Safe_Decimal__Currency__USD
  metric        : Enum__Billing__Metric

Schema__Billing__Daily_Bucket
  date          : Safe_Str__Iso8601_Date
  total_usd     : Safe_Decimal__Currency__USD
  line_items    : List__Schema__Billing__Line_Item

Schema__Billing__Report
  window        : Schema__Billing__Window
  metric        : Enum__Billing__Metric
  group_by      : Enum__Billing__Group_By
  buckets       : List__Schema__Billing__Daily_Bucket
  total_usd     : Safe_Decimal__Currency__USD
  account_id    : str                       # populated from STS GetCallerIdentity at render time, not from Cost Explorer (the resolved caller account is the desired scope — no --org flag in MVP)
  currency      : str                       # hard-coded "USD" at MVP. If Cost Explorer returns a non-USD unit, the builder raises and aborts with the §10.1 currency-mismatch message — we never render a non-USD report.
  generated_at  : Safe_Str__Iso8601_Date    # UTC date the report was built
```

**Codebase scan result (resolves the §10.1 open question).** Direct inspection of the installed `osbot-utils` package and this repo's primitives folders on 2026-05-15:

- `osbot_utils/type_safe/primitives/core/` ships `Safe_Str`, `Safe_Int`, `Safe_UInt`, `Safe_Float` — **no `Safe_Decimal` base.**
- `osbot_utils/type_safe/primitives/domains/numerical/safe_float/` ships seven Safe_Float subclasses including **`Safe_Float__Money`** (`decimal_places=2`, `use_decimal=True`, `allow_inf=False`, `allow_nan=False`, `min_value=0.0`, `round_output=True`) and `Safe_Float__Financial`. `Safe_Float__Money` internally uses `Decimal` arithmetic, so the "decimal" semantic is already covered.
- This repo's own `*/primitives/` folders (under `sg_compute/`, `sg_compute_specs/*/`, `sgraph_ai_service_playwright__cli/*/`) ship dozens of `Safe_Str__*` and `Safe_Int__*` primitives but **no money/decimal/currency primitive.**

**Decision (Dinis, 2026-05-15):** add `Safe_Decimal__Currency__USD` as a local subclass of `Safe_Float__Money` in the billing primitives folder. The "Decimal" in the name reflects the *internal* representation (`use_decimal=True` is inherited from `Safe_Float__Money`), not a separate Python base class. No upstream PR or `Safe_Float` fallback needed — the upstream base already gives us Decimal-backed money arithmetic. The class is a thin override (constraints + naming) so the rest of the billing tree never mentions `Safe_Float`.

---

## 5. AWS Access

### 5.1 The osbot-aws gap

DNS chose to use raw `boto3` because no `osbot-aws` Route 53 wrapper existed at write-time. `Cost_Explorer__AWS__Client.py` lands in the same situation: at the time of writing, no `osbot-aws` Cost Explorer wrapper exists.

**Recommendation: narrow local wrapper, mirroring `Route53__AWS__Client` exactly.**

- One file (`Cost_Explorer__AWS__Client.py`) imports `boto3` directly.
- Header documents the exception (rule-7 module banner referencing the precedent set by `Route53__AWS__Client`).
- Every other file in the billing tree stays pure Type_Safe + osbot-utils, so the boto3 boundary is one greppable file.
- File-level FOLLOW-UP comment: migrate to osbot-aws once a `Cost_Explorer` wrapper exists there.

The alternative — adding Cost Explorer support to `osbot-aws` first — is cleaner long-term but blocks delivery on an upstream PR cycle. Recommend the narrow-wrapper route now and an osbot-aws contribution as a follow-up slice.

### 5.2 API surface used

| Operation | Purpose |
|---|---|
| `ce.get_cost_and_usage` | The only Cost Explorer call needed for MVP. Inputs: `TimePeriod`, `Granularity=DAILY`, `Metrics=['UnblendedCost']`, optional `GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]`. |
| `sts.get_caller_identity` | Populate `account_id` on the report. Already wrapped in `osbot-aws` — use that wrapper, not raw boto3. |

Pagination uses `NextPageToken` (Cost Explorer-specific — not a boto3 paginator). The client class handles it internally.

### 5.3 Granularity reality-check

- `DAILY` is the lowest free-tier granularity for `GetCostAndUsage`.
- `HOURLY` requires opt-in (`UpdateCostAllocationTagsStatus`-style account configuration) and is **billable** ($0.01/request after the free tier).
- Resource-level cost requires `GetCostAndUsageWithResources` and a 14-day retention window — not in MVP.
- True hourly + per-resource needs the Cost & Usage Report (CUR) export to S3 + Athena — far out of scope.

MVP design: `last-48h` is rendered as two daily buckets. Document in CLI help text that "48h" is two daily readings, not a 48-hour rolling window.

---

## 6. CLI Command Shape

Match DNS ergonomics: a `billing_app` Typer, sub-apps for verbs, every command supports `--json`, no AWS calls in `Cli__Billing.py` (pure delegation).

```
sg aws billing                       # help (no_args_is_help=True)

sg aws billing last-48h              # 2 daily buckets, by-service breakdown, top 10
sg aws billing week                  # 7 daily buckets, by-service breakdown, top 10
sg aws billing mtd                   # month-to-date, by-service breakdown
sg aws billing window <start> <end>  # explicit date range (escape hatch)

# Common flags on every command:
  --json                              # JSON output instead of Rich table
  --top N                             # how many services to show before rolling into OTHER (default 10)
  --metric unblended|blended|amortized  # which cost metric (default unblended)
  --group-by service|region|account   # MVP: only service exercised; flag exists for forward-compat
```

**Read-only — no mutation gate.** No analogue to `SG_AWS__DNS__ALLOW_MUTATIONS`. The whole feature is `ce:Get*` only.

**Rich table layout (default):**

```
  AWS Spend — last 48h  ·  account 123456789012  ·  metric: UnblendedCost

  Date          Service                                            USD
  2026-05-14    Amazon Elastic Compute Cloud - Compute          12.43
  2026-05-14    AWS Lambda                                        0.87
  2026-05-14    Amazon Simple Storage Service                     0.31
  2026-05-14    (subtotal)                                      13.61
  2026-05-15    Amazon Elastic Compute Cloud - Compute          11.92
  ...
  Total                                                          27.84
```

`--json` mirrors `Schema__Billing__Report.json()` directly.

---

## 7. Test Strategy

Mirrors `tests/unit/sgraph_ai_service_playwright__cli/aws/dns/` exactly. No mocks, no patches (CLAUDE.md testing rule 1).

### 7.1 Unit tests (default `pytest` run)

| Test file | What it asserts |
|---|---|
| `tests/unit/.../aws/billing/service/test_Cost_Explorer__AWS__Client.py` | In-memory subclass overrides `client()` to return a fake whose `get_cost_and_usage` returns canned Cost Explorer payloads. Asserts payload-to-schema mapping. |
| `tests/unit/.../aws/billing/service/test_Billing__Window__Resolver.py` | Pure resolver — windowing math, no AWS. Asserts `last-48h` → correct `(start, end)`. |
| `tests/unit/.../aws/billing/service/test_Billing__Report__Builder.py` | Composes Builder + an in-memory Cost_Explorer client; asserts a fully-typed `Schema__Billing__Report`. |
| `tests/unit/.../aws/billing/cli/test_Cli__Billing__helpers.py` | Rich-table render + JSON-mode output structure (using Typer's `CliRunner`). |
| `tests/unit/.../aws/billing/schemas/test_Schema__Billing__Report.py` | Schema round-trip (`.json()` → `from_json` parity). |

In-memory subclass pattern (DNS precedent — `Route53__AWS__Client.client()` is the single seam):

```python
class Cost_Explorer__AWS__Client__In_Memory(Cost_Explorer__AWS__Client):
    canned_responses : dict = {}
    def client(self):
        return _Fake_CE_Client(self.canned_responses)
```

### 7.2 Real-AWS integration test (gated)

Gate on `SG_AWS__BILLING__LIVE_TEST=1` (mirrors `SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE` skip pattern). When set, calls real Cost Explorer for `last-48h` and asserts:

- HTTP 200 round-trip
- Non-empty `buckets`
- All `amount_usd` decimal-valid and non-negative
- `account_id` matches `sts.get_caller_identity`

Skipped cleanly without the gate. CI does NOT set it (Cost Explorer is billable per request).

---

## 8. IAM / Permissions

The principal executing the CLI needs:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage",
        "ce:GetDimensionValues"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "sts:GetCallerIdentity",
      "Resource": "*"
    }
  ]
}
```

Notes:

- Cost Explorer does not support resource-level IAM (`Resource: "*"` is the only option AWS accepts for `ce:*`).
- Cost Explorer must be **manually enabled in the AWS console once per account** before the API works. First call after enablement can fail for up to 24h. Document this in the CLI help text.
- The principal must be in the *payer* account for organisation-wide totals; member-account principals see only their own spend.

For the workstation/dev path, the existing AWS credential resolution chain (env vars / `~/.aws/credentials` / SSO) is sufficient — no new credential plumbing.

---

## 9. CLAUDE.md Compliance Checklist

- [x] All classes extend `Type_Safe` (rule 1)
- [x] Zero raw primitives — `Safe_*`, `Enum__*`, collection subclasses (rule 2)
- [x] No `Literal`s — `Enum__Billing__*` for fixed-value sets (rule 3)
- [x] Schemas are pure data — no methods (rule 4)
- [x] Collection subclasses are pure type definitions (rule 5)
- [x] Routes (if any are added later — none in this MVP) would return `.json()` on Type_Safe (rule 6)
- [x] `═══` 80-char headers in Python files only; this Markdown deliverable uses YAML frontmatter (rule 7)
- [x] Inline comments only — no docstrings (rule 8)
- [x] No underscore prefix for private methods (rule 9)
- [x] One class per file; empty `__init__.py` (rules 21, 22)
- [x] `osbot-aws` for STS; documented carve-out for Cost Explorer matching DNS precedent (Stack rule)
- [x] Read-only — no allowlist concerns, no mutation gate
- [x] No new AWS credentials in Git
- [x] No new security groups, so rules 14 and 15 do not apply

---

## 10. Open Questions — RESOLVED (Dinis, 2026-05-15)

All six questions are now closed. Decisions captured below; see "Revision history" at the bottom of this doc for the audit trail.

### 10.1 `Safe_Decimal__Currency__USD` — RESOLVED

**Decision:** add `Safe_Decimal__Currency__USD` as a local subclass of `osbot_utils ... Safe_Float__Money` in `aws/billing/primitives/`. Name uses "Decimal" because the upstream parent already sets `use_decimal=True` (Decimal-backed internally) — the name describes the storage semantic, not a Python base class.

Scan evidence (see §4.1 in full):
- `osbot_utils/type_safe/primitives/core/` — no `Safe_Decimal` base exists.
- `osbot_utils/type_safe/primitives/domains/numerical/safe_float/Safe_Float__Money.py` — exists; `Safe_Float` + `decimal_places=2` + `use_decimal=True` + `min_value=0.0`.
- This repo's primitives folders — no money/decimal primitive exists today; this is the first one.

Upstream PR for a true `Safe_Decimal` base is **not pursued**. Fallback to bare `Safe_Float` is **not used** (would lose Decimal semantics we already have for free).

### 10.2 Account scope — RESOLVED

**Decision:** default scope is whatever account the current AWS credentials resolve to via `sts:GetCallerIdentity`. Drop the `--org` opt-in entirely from MVP. If a payer-account credential happens to be in scope, the totals it shows are simply the totals it has permission to see — we make no special org/payer detection.

Implementation impact:
- `Billing__Report__Builder` calls `sts.get_caller_identity` once per report and stamps `account_id` on `Schema__Billing__Report`.
- No CLI flag for organisation rollup. `GroupBy=LINKED_ACCOUNT` stays in `Enum__Billing__Group_By` only for forward-compat (already noted §11).
- IAM requirements in §8 are unchanged (already minimal).

### 10.3 `mtd` and `window <start> <end>` in MVP — RESOLVED

**Decision:** confirmed in MVP, alongside `last-48h` and `week`. Locked in. No change to §6 — the four verbs (`last-48h`, `week`, `mtd`, `window <start> <end>`) are the MVP surface.

### 10.4 Cost Explorer "not yet enabled" error — RESOLVED

**Decision:** catch the error in `Cost_Explorer__AWS__Client`, abort with an actionable message styled on the DNS `--zone unset` error. Specifically, when boto3 raises a `DataUnavailableException` or `AccessDenied`-with-`ce:GetCostAndUsage` from a known-good principal, surface:

```
Error: AWS Cost Explorer is not enabled for account <account_id>.

Cost Explorer must be enabled once per account from the AWS Console:
  https://console.aws.amazon.com/cost-management/home#/cost-explorer

After enabling, the first API call may fail for up to 24 hours while AWS
prepares the data. Re-run `sg aws billing <verb>` once that window has
passed.
```

The principal/account is filled in from `sts:GetCallerIdentity` (already in the report path). The CLI exits with status 2 (mirrors DNS unset-zone exit code).

### 10.5 Currency — RESOLVED

**Decision:** hard-code USD. If `get_cost_and_usage` returns a `Unit` other than `USD` for any bucket, `Billing__Report__Builder` **raises and aborts** — no partial rendering, no warning. Error:

```
Error: AWS Cost Explorer returned non-USD currency unit '<unit>' for account
<account_id>. This CLI hard-codes USD output; multi-currency rendering is
out of scope for MVP. File an issue if you need <unit> support.
```

Schema-level enforcement: `Schema__Billing__Report.currency` is set unconditionally to the literal `"USD"` by the builder; any divergence from the API response triggers the abort above before the schema is constructed. (Future slice can promote `currency` to an `Enum__Currency` if multi-currency lands.)

### 10.6 Caching — RESOLVED

**Decision:** not in MVP. Cost Explorer charges per request after the free tier; that risk is accepted for the MVP cadence.

**Future-slice note (Dinis's words):** a future slice will use **vaults** to hold cached billing data. No design here — that slice will land alongside the broader vault-cached-data pattern. The current plan stays cache-free; do not stub a cache interface "just in case".

---

## 11. Out of Scope (deferred)

Explicitly **not** in this plan, to be revisited in follow-up slices:

- **Forecasting** (`ce:GetCostForecast`) — separate API, separate ergonomic story.
- **Anomaly detection** (`ce:GetAnomalies`) — needs the AWS-native anomaly monitor set up first.
- **AWS Budgets** (`budgets:DescribeBudgets`) — separate API and IAM surface.
- **CUR / Athena queries** — hourly + per-resource truth source, but requires a CUR S3 export + Glue catalogue. Multi-week setup.
- **Per-resource attribution** (`ce:GetCostAndUsageWithResources`) — requires opting the account in and is rate-limited.
- **Reservation / Savings Plans coverage / utilisation reports** — separate Cost Explorer APIs.
- **HTML / web dashboard** — the Playwright service has no UI for billing; this is CLI-only. A future FastAPI route serving `Schema__Billing__Report.json()` is a natural follow-up but adds nothing today.
- **Multi-account org rollup with linked-account labels** — possible with `GroupBy=LINKED_ACCOUNT` but needs label resolution (the API returns account IDs, not aliases).
- **Cross-region cost view** — `GroupBy=REGION` enum exists for forward-compat but no CLI surface for it in MVP.
- **Cost-anomaly alerting to Slack/email** — not a CLI concern.
- **Tag-based grouping** (cost-allocation tags) — requires per-tag activation; deferred.

---

## 12. Handoff

When this plan is ratified:

1. File a Dev brief under `team/comms/briefs/` linking back to this document.
2. Dev opens a feature branch under `claude/feat-billing-mvp-*` and implements top-down: primitives → enums → schemas → collections → service classes → CLI → tests.
3. QA runs the unit suite + the gated live-AWS test against a sandbox account.
4. Librarian appends a "PROPOSED" entry under the relevant domain (`cli/` or a new `cli/aws-billing/` sub-domain) and flips it to "EXISTS" only once the merge lands.
5. Historian files a slice debrief under `team/claude/debriefs/`.

---

## 13. Revision history

| Date (UTC) | Author | Change |
|---|---|---|
| 2026-05-15 hour 14 | Architect (Claude) | Initial plan published (commit `d0f02d45`). |
| 2026-05-15 | Architect (Claude) | Folded in Dinis's decisions on all six open questions: (1) `Safe_Decimal__Currency__USD` subclasses upstream `Safe_Float__Money` (confirmed by direct osbot-utils scan — no `Safe_Decimal` base, but `Safe_Float__Money` already gives Decimal-backed money arithmetic); (2) default scope is the STS caller identity, `--org` removed from MVP; (3) `mtd` and `window <start> <end>` locked into MVP; (4) Cost Explorer not-enabled error caught and rendered with actionable guidance matching DNS `--zone unset` style; (5) USD hard-coded, builder aborts on non-USD `Unit` from Cost Explorer; (6) caching deferred to a future vault-backed slice. |
