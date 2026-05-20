---
title: "Screen-Idiom Catalogue — reusable TUI shapes to pick off the shelf"
file: 03__screen-idiom-catalogue.md
author: Architect (Claude)
date: 2026-05-20 (UTC hour 23)
repo: SGraph-AI__Service__Playwright @ claude/review-cf-logging-docs-QYfEq (v0.2.36 line)
status: GUIDE — reusable menu. Pick idioms when choosing screens for a new TUI.
parent: README.md
---

# Screen-Idiom Catalogue

Seven recurring TUI shapes, abstracted from real screens. When briefing a new TUI (template `02`, §4), **pick idioms off this shelf** rather than inventing layouts from scratch. None is mandatory; mix and match. The "art of the possible" is partly *which idioms suit which service* — that's a thing to learn, so try unexpected pairings.

Each idiom lists: what it shows · when to use it · the data shape it needs · interactivity · a tiny sketch · where it'd fit beyond CloudFront.

---

## 1. Live Tail
**Shows:** newest-first stream of parsed events. The data-plane `tail -f`.
**Use when:** the service emits a continuous event stream you want to watch in real time.
**Needs:** a list-newest + fetch + parse path; throttling/sampling for high volume.
**Interactivity:** medium — pause, filter by type, drill to an Inspector.
**Update:** real-time, 5–10 Hz.
```
23:04:08  GET /sources/cv   200  142ms  US  ● human
23:04:07  GET /robots.txt   200   18ms  DE  ◆ bot
[Space] pause  [f]ilter  [Enter] inspect
```
**Beyond CF:** CloudWatch Logs tail · CloudTrail event feed · SQS/Kinesis message peek.

---

## 2. Flow / Pipeline Map
**Shows:** processing **stages** as boxes-and-arrows, each with counts / bytes / freshness.
**Use when:** there's a multi-stage pipeline (ETL, S3→S3 chain, state machine) and stage health matters.
**Needs:** per-stage counters and a last-updated signal; ideally trigger hooks (run / dry-run / wipe).
**Interactivity:** medium→high — open a stage, trigger it.
**Update:** 5–10 s.
```
RAW ──L,E──▶ PARSED ──T──▶ ENRICHED ──S──▶ AGGREGATED
412 .gz      9,140 ev       +bot+geo        18 rollups
● fresh      ◐ 2m ago       ○ stale         ○ none
```
**Beyond CF:** any LETS chain · Step Functions · Glue/EMR jobs · Firehose→S3→processing.

---

## 3. Topology / Wiring Map
**Shows:** a **resource graph** — who is wired to what — enumerated from live state.
**Use when:** the question is "how is this actually deployed/connected?"
**Needs:** `list/describe` primitives across the resources; honest handling of edges you can't confirm.
**Interactivity:** medium — drill into a node.
**Update:** on demand / 30 s.
```
CloudFront ─▶ Firehose ─▶ S3 ─▶ LETS ─▶ consumers
  E1ABC ●      (inferred)   …obj    stages
  ⚠ rt-log config UNVERIFIED
```
**Beyond CF:** VPC/subnet/EC2/ENI graph · IAM role-trust graph · ALB→target-group→instances.
**Note:** mark inferred/unconfirmed edges (`⚠`) — never draw a clean line that lies (playbook §7).

---

## 4. Record / Field Inspector
**Shows:** one item walked **field-by-field**, raw → transformed, with lineage.
**Use when:** you need to explain *what a transform does to the fields*, or inspect a single object deeply.
**Needs:** one fetch + the schema; highlight raw→derived deltas.
**Interactivity:** high — scroll fields, toggle raw/transformed.
**Update:** static per record.
```
RAW TSV (26)        DERIVED (4)       LINEAGE (5)
user-agent Moz%2F → ua_decoded Moz/  doc_id {etag}__17
sc-status  200      status_class 2xx  source_etag E3…
[↑↓] field  [t] toggle raw/transformed
```
**Beyond CF:** S3 object metadata + tags · a DynamoDB item · an IAM policy document · any schema'd record.

---

## 5. Reality Dashboard
**Shows:** aggregates — bars, sparklines, top-N, distributions — the "what's going on" panel.
**Use when:** you want health/usage at a glance.
**Needs:** an aggregation over a window (sample live, or read a pre-aggregated artefact).
**Interactivity:** medium — filter by dimension, export a card.
**Update:** 10–30 s.
```
THROUGHPUT ▂▃▄▅▆▇█▇▆▅   BOT/HUMAN ▓▓▓▓▓▓ 61% bot
TOP URIs  /sources/cv 1204   STATUS 2xx 88% 4xx 7%
```
**Beyond CF:** CloudWatch metrics dashboard · billing/cost summary · Fargate task health · request analytics.

---

## 6. Comparison / Drift
**Shows:** N-column side-by-side (e.g. local vs edge vs deployed) with drift called out.
**Use when:** the question is "what's different across environments/versions/configs?"
**Needs:** the same shape fetched from N sources; a diff/drift rule.
**Interactivity:** low–medium — refresh, drill into a diff, optionally sync.
**Update:** on demand.
```
COMPONENT    LOCAL     EDGE      DEPLOYED
edge-proxy   v0.27.55  v0.27.55  v0.27.43  ◐ drift
vault-app    v0.27.55  v0.27.55  v0.27.55  ● in sync
```
**Beyond CF:** env/version drift · resource config vs IaC · two-account resource compare.

---

## 7. Simulator / Dry-Run
**Shows:** a preview of a **transform or mutation** — field-diff (adds/changes/drops) and a sample — **before** any write.
**Use when:** designing a new transform stage, or about to mutate state; you want to see the effect first.
**Needs:** the pure transform runnable over real input; write gated behind `…_ALLOW_MUTATIONS`.
**Interactivity:** high — pick input, sample, then explicitly commit.
**Update:** on demand.
```
stage: parsed → enriched   input: lets/parsed/2026-05-20 (9,140)
+ adds: bot_category, geo_country_name   ~ changes: status_class
out: 9,140 (1:1)  est 0.9MB → lets/enriched/…   [W] WRITE (needs ALLOW_MUTATIONS)
```
**Beyond CF:** any LETS stage · S3 bulk op preview · IAM policy change preview · resource teardown preview.
**Note:** this is often the **highest-value** screen — it makes designing the next pipeline stage far faster (playbook §6).

---

## Quick chooser

| If the question is… | Reach for |
|---|---|
| "what's happening right now?" | Live Tail (1), Reality Dashboard (5) |
| "what are the stages and are they healthy?" | Flow Map (2) |
| "how is this wired/deployed?" | Topology (3) |
| "what does this transform do to the data?" | Inspector (4), Simulator (7) |
| "what's different across X?" | Comparison (6) |
| "what will this change before I run it?" | Simulator (7) |

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
