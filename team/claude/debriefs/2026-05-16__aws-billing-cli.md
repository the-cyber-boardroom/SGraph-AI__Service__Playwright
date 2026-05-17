---
title: "sg aws billing — AWS Cost Explorer CLI sub-package"
date: 2026-05-16
branch: claude/plan-billing-view-u0NFG
commits: e001bc05 2d5480a9 835918a1 3265b684 8fb7e41b ebcd73ef
status: COMPLETE
---

# sg aws billing — AWS Cost Explorer CLI sub-package

## What was built

A full AWS Cost Explorer CLI sub-package, surfaced as `sg aws billing <verb>`, following the exact pattern of `sg aws dns`. Six commands, Rich terminal output with emojis and ASCII bar charts, typed schemas end-to-end, live-tested against a real AWS account.

### Commands

| Command | Alias | What it shows |
|---------|-------|---------------|
| `sg aws billing last-48h` | `sg> aws b 4` | Daily breakdown for the last 2 days |
| `sg aws billing week` | `sg> aws b w` | Daily breakdown for the last 7 days |
| `sg aws billing mtd` | `sg> aws b m` | Month-to-date daily breakdown |
| `sg aws billing window --start YYYY-MM-DD --end YYYY-MM-DD` | | Custom date range |
| `sg aws billing summary` | `sg> aws b s` | Aggregated service totals with share % and horizontal bars |
| `sg aws billing chart` | `sg> aws b c` | Daily totals bar chart with ▲ peak / ▼ low markers |

All six commands accept `--all-charges` to include credits, refunds, and taxes (default: Usage only, matching the AWS Console default).

### File map

```
sgraph_ai_service_playwright__cli/aws/billing/
  primitives/
    Safe_Decimal__Currency__USD.py     — Decimal-backed USD; min_value=None (credits)
    Safe_Str__Aws_Service_Code.py      — Permissive regex preserving spaces/hyphens/parens
    Safe_Str__Iso8601_Date.py          — ISO-8601 date string
    Safe_Str__Aws_Usage_Type.py        — Usage type string
  enums/
    Enum__Billing__Granularity.py      — DAILY / HOURLY / MONTHLY
    Enum__Billing__Metric.py           — UNBLENDED_COST / BLENDED_COST / …
    Enum__Billing__Group_By.py         — SERVICE / USAGE_TYPE / LINKED_ACCOUNT / REGION
    Enum__Billing__Window_Keyword.py   — LAST_48H / LAST_7D / MONTH_TO_DATE
  schemas/
    Schema__Billing__Window.py         — start / end / granularity / keyword
    Schema__Billing__Line_Item.py      — service / amount_usd / metric
    Schema__Billing__Daily_Bucket.py   — date / total_usd / line_items
    Schema__Billing__Report.py         — window / metric / group_by / buckets / total_usd / account_id / currency / generated_at
  collections/
    List__Schema__Billing__Daily_Bucket.py
    List__Schema__Billing__Line_Item.py
    List__Schema__Billing__Group.py
  service/
    Cost_Explorer__AWS__Client.py      — Sole boto3 boundary; client() seam; NextPageToken pagination
    Billing__Window__Resolver.py       — Maps keywords → (start, end, granularity) tuples
    Billing__Report__Builder.py        — Orchestrates CE queries → typed Schema__Billing__Report
  cli/
    Cli__Billing.py                    — Six Typer commands; Rich rendering; emoji+ASCII art
```

`sgraph_ai_service_playwright__cli/aws/cli/Cli__Aws.py` was updated to register `billing_app` alongside `dns_app` and `acm_app`.

### IAM requirements

The AWS principal running `sg aws billing` needs:

```
ce:GetCostAndUsage      (required — Cost Explorer API)
ce:GetDimensionValues   (optional — future group-by surfaces)
sts:GetCallerIdentity   (required — account provenance in report header and errors)
```

All on `Resource: "*"` — Cost Explorer has no resource-level IAM.

---

## Failures

### GOOD failures (surfaced early, caught by live testing, informed better design)

**G1 — IAM error vs CE-disabled conflation.**
The first live run returned the "Cost Explorer not enabled" message, but CE was clearly enabled (the user had a screenshot of the console showing spend data). Root cause: `AccessDeniedException` (IAM missing `ce:GetCostAndUsage`) and `DataUnavailableException` (CE not enabled at all) were caught in the same `if` block. The live error immediately revealed the conflation. Fixed by splitting into two distinct handlers — one for each error class — with distinct human-readable guidance (CE enablement guide vs IAM policy guide). This fix also uncovered that the IAM principal lacked `ce:GetCostAndUsage`, which the user resolved.

**G2 — Negative amount rejection from credits.**
After the IAM fix, the command ran but crashed: `ValueError: Safe_Decimal__Currency__USD must be >= 0.0, got -1.29046e-05`. AWS Cost Explorer returns tiny negative amounts for credits and refunds. The crash revealed two things simultaneously: (a) `min_value=0.0` in `Safe_Float__Money` propagates to subclasses if not overridden, and (b) the default data fetch includes credit/refund rows. Fixed by setting `min_value=None` in `Safe_Decimal__Currency__USD` and adding a `RECORD_TYPE=Usage` filter as the default (matching the CE console default), with an explicit `--all-charges` flag to opt back in. Both fixes are sound independently — `min_value=None` is correct because credits are legitimate negative values; the default filter is correct because "show me my spend" should mean spend, not credits.

**G3 — Service name mangling to underscores.**
First working output showed service names as `Amazon_Elastic_Compute_Cloud___Compute` (underscores where spaces, hyphens, and parens should be). Root cause: `Safe_Str` default regex `r'[^a-zA-Z0-9]'` (REPLACE mode) strips everything non-alphanumeric to `_`. This is the right default for identifiers, but AWS CE service names like `Amazon EC2 Container Registry (ECR)` are display strings, not identifiers. Fixed by writing `Safe_Str__Aws_Service_Code` with an explicit permissive regex `r'[^A-Za-z0-9 \-().,/&_]'`. The failure exposed a gap in the project's mental model: Safe_Str has two distinct use cases (identifier safety vs display-string sanitisation) that require different defaults.

**G4 — Column alignment broken by 1-cell-wide glyphs.**
After putting emoji + name in a single Rich column, some rows were left-shifted by one character. The user diagnosed it precisely: service rows using `λ` (U+03BB Greek letter, 1-cell wide, not Emoji_Presentation) and `🖧` (U+1F5A7 THREE NETWORKED COMPUTERS, lacks Emoji_Presentation flag, renders 1-cell in most terminals) caused Rich to miscalculate column width. The fix had two stages: (a) split emoji and name into separate Rich columns (`min_width=2, max_width=2` for the emoji column), and (b) replace `λ` with `🟧` (orange square, Emoji_Presentation, 2-cell) and `🖧` with `🧰` (toolbox, Emoji_Presentation, 2-cell). The lesson: terminal column alignment for mixed emoji+text requires Emoji_Presentation glyphs only; any glyph whose Unicode block predates the Emoji_Presentation property (e.g. Greek letters, dingbats, some technical symbols) will render 1-cell regardless of visual appearance in some editors.

### BAD failures

None. All four failures were surfaced and resolved during live testing rather than silently shipped or worked around.

---

## Lessons learned

**L1 — AWS API error codes are not a clean hierarchy.** `DataUnavailableException` and `AccessDeniedException` look structurally equivalent but mean opposite things from the user's perspective ("your data isn't ready" vs "you have no permission"). Any multi-error handler that groups them together will misdirect the user. Pattern: one `if` per error code, with tailored remediation text.

**L2 — `Safe_Str` regex defaults suit identifiers, not display strings.** Every CE service name contains spaces, hyphens, and parentheses. Using `Safe_Str` directly for display strings will corrupt them silently. Pattern for display strings: always write a dedicated `Safe_Str__*` subclass with an explicit permissive regex and `allow_empty=True`.

**L3 — Credit amounts from Cost Explorer are legitimately negative.** The `Safe_Float__Money` base class default (`min_value=0.0`) reflects the most common use case but is wrong for boundary types that accept CE raw output. When subclassing for a CE boundary type, always set `min_value=None` explicitly and document why.

**L4 — The CE `RECORD_TYPE` filter is not optional.** Without `Filter={'Dimensions': {'Key': 'RECORD_TYPE', 'Values': ['Usage'], 'MatchOptions': ['EQUALS']}}`, CE returns credits, refunds, and taxes alongside usage rows. The amounts are tiny but non-zero and break "total = sum of spend" invariants. The filter matches AWS Console default behaviour and should be the hard default.

**L5 — `NextPageToken` is CE's pagination protocol, not standard boto3 paginators.** `boto3.client('ce').get_cost_and_usage` does not support `get_paginator()`. Pagination must be implemented manually by threading `NextPageToken` from each response into the next request. This is documented in the AWS SDK but easy to miss.

**L6 — Emoji terminal widths are a runtime property, not a code-point property.** Whether a glyph consumes 1 or 2 terminal columns depends on (a) the Unicode Emoji_Presentation property, (b) the terminal emulator's font rendering, and (c) whether Rich's `Segment` width measurement agrees with the terminal. Safe rule: only use glyphs from the Emoji_Presentation category (standard coloured emoji like 🟧 🧰 💡) in width-constrained columns. Greek letters, technical symbols, and anything in the Miscellaneous Technical block are unreliable.

**L7 — IAM `Resource: "*"` is mandatory for Cost Explorer.** CE does not support resource-level IAM; any policy that restricts `Resource` to specific ARNs will silently fail. This is a CE-specific quirk worth calling out in error messages.

---

## Architecture notes

### `Cost_Explorer__AWS__Client` — boto3 boundary

Follows the same isolation pattern as `Route53__AWS__Client` and `ACM__AWS__Client`. The `client()` method is the single test seam — in tests, override it to return a fake CE client with a canned `get_cost_and_usage` response.

### `Billing__Report__Builder` — report assembly

`ce_client` is `None` by default; `setup()` lazy-inits it. Set `ce_client` before calling `build()` to avoid real AWS calls in tests. The `all_charges: bool = False` parameter controls the `record_types` filter passed to `get_cost_and_usage`.

### `Cli__Billing` — rendering layer

The rendering layer is self-contained — it imports nothing from the service layer except `Billing__Report__Builder`. The `SERVICE_DISPLAY` dict maps raw CE service names (e.g. `'Amazon Elastic Compute Cloud - Compute'`) to short labels (`'EC2 Compute'`). The `SERVICE_EMOJI` dict maps short labels to Emoji_Presentation glyphs. All values in `SERVICE_EMOJI` must be 2-cell-wide Emoji_Presentation characters.

Key helpers:
- `_bar(value, max_value, width)` — eighth-cell precision ASCII bars using `▏▎▍▌▋▊▉█`
- `_amount_style(amount)` — dim < $0.10, yellow < $10, bold red ≥ $10, green for negatives
- `_trend_arrow(curr, prev)` — `↑` > 20% change, `↓` < -20%, `→` otherwise
- `_header_panel()` — Rich Panel with account, window, grand total, daily avg

---

## Test coverage

136 unit tests pass (up from 130 pre-session). The 6 new billing tests cover the window resolver, the report builder with a fake CE client, and the currency check helper. Live-tested against AWS account 745506449035 across all six commands.

---

## Follow-ups

- No unit tests for the CLI rendering layer (`Cli__Billing.py`) — Rich output requires a real terminal or a `Console(record=True)` harness. Consider adding render smoke tests in a follow-on slice.
- `MONTHLY` granularity is supported by the CE API but no CLI command uses it yet — `mtd` uses `DAILY` to show the per-day breakdown within the month.
- The `LIST__Schema__Billing__Group` collection and `Schema__Billing__Group` schema were scaffolded but are unused in MVP (future: group-by surfaces).
