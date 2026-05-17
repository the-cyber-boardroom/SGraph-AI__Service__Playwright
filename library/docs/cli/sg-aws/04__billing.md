---
title: "sg aws billing — Cost Explorer views"
file: 04__billing.md
author: Architect (Claude)
date: 2026-05-17
parent: README.md
---

# 04 — `sg aws billing`

Daily AWS spend, summaries, and ASCII charts. All commands are read-only (Cost Explorer API).

---

## Global flags

All `billing` commands accept:

| Flag | Default | Notes |
|------|---------|-------|
| `--json` | — | JSON to stdout |
| `--top N` | `10` | Top-N services per row |
| `--metric M` | `UnblendedCost` | Cost Explorer metric (`UnblendedCost`, `AmortizedCost`, `BlendedCost`, …) |
| `--group-by D` | `SERVICE` | Group by dimension (`SERVICE`, `REGION`, `LINKED_ACCOUNT`, …) |
| `--all-charges` | off | Include credits, refunds, taxes (off → costs only) |

---

## Window verbs

### `sg aws billing last-48h`

Last 48 hours, two daily buckets.

```bash
sg aws billing last-48h
sg aws billing last-48h --top 5
sg aws billing last-48h --json
```

### `sg aws billing week`

Last 7 days, daily buckets.

```bash
sg aws billing week
sg aws billing week --metric AmortizedCost
```

### `sg aws billing mtd`

Month-to-date, daily buckets.

```bash
sg aws billing mtd
sg aws billing mtd --top 15
```

### `sg aws billing window START END`

Explicit date range. Dates are `YYYY-MM-DD`, inclusive of start, exclusive of end.

```bash
sg aws billing window 2026-05-01 2026-05-15
sg aws billing window 2026-05-01 2026-05-15 --group-by REGION
```

---

## Aggregation verbs

### `sg aws billing summary [last-48h|week|mtd]`

Aggregated totals over the window — services sorted by total spend with a percentage and an ASCII bar. The window verb is positional and defaults to `mtd`.

```bash
sg aws billing summary week
sg aws billing summary mtd --top 5
sg aws billing summary last-48h --json
```

### `sg aws billing chart [last-48h|week|mtd]`

Daily-totals ASCII bar chart. Same positional window verb.

```bash
sg aws billing chart week
sg aws billing chart mtd
```

---

## Patterns

**"Did anything change today?":**

```bash
sg aws billing last-48h
```

**Sanity-check the running monthly total:**

```bash
sg aws billing summary mtd --top 5
```

**Find which region is most expensive this month:**

```bash
sg aws billing window 2026-05-01 2026-05-17 --group-by REGION --json | \
  jq '[ .rows[] | { region: .group, total: .total } ] | sort_by(.total) | reverse | .[0:3]'
```

---

## Cost Explorer notes

- The first Cost Explorer call in an account takes **24 h** to be enabled. After that, day-grain data is available with ~24 h delay.
- Cost Explorer itself is billable — `$0.01` per API call. These commands batch where possible; a typical day's use is a few cents.
- `--all-charges` adds the non-`Usage` record types (credits, refunds, taxes). Off by default because the headline number people want is "what did we spend".

---

## What backs this

Code at `sgraph_ai_service_playwright__cli/aws/billing/`:

| Class | What it does |
|-------|-------------|
| `Billing__Report__Builder` | Build typed cost reports from Cost Explorer responses |
| `Billing__Window__Resolver` | Translate `last-48h` / `week` / `mtd` → concrete date range |
| `Cost_Explorer__AWS__Client` | boto3 wrapper over `ce.*` |

Tests: `tests/unit/sgraph_ai_service_playwright__cli/aws/billing/`.
