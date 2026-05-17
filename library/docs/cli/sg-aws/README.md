---
title: "sg aws — User Guide"
file: README.md
author: Architect (Claude)
date: 2026-05-17
updated: 2026-05-17
repo: SGraph-AI__Service__Playwright @ dev (v0.2.29 line)
status: REFERENCE — describes commands that exist today; v0.2.29 new surfaces marked PROPOSED until slice PRs land.
---

# `sg aws` — User Guide

How to drive the `sg aws *` command surface from a terminal. This pack is a **user reference**, not an architecture brief. Each file covers one AWS service area and lists the verbs, flags, env-var gates, and copy-paste examples an operator actually needs.

> **Scope:** only commands that exist in code at v0.2.27. Anything proposed (e.g. `sg aws lab`; the expanded `sg aws cf` / `sg aws lambda` surface in v2 vault-publish phases 2a/2b) is **not** in this pack — see [`library/dev_packs/v0.3.0__sg-aws-lab-harness/`](../../../dev_packs/v0.3.0__sg-aws-lab-harness/README.md) for the lab harness consumer.

---

## Read order

| # | File | What it covers |
|---|------|----------------|
| 00 | this README | Layout, conventions, global flags, env-var gates |
| 01 | [`01__getting-started.md`](01__getting-started.md) | AWS auth, JSON output, mutation gates, confirmation prompts |
| 02 | [`02__dns.md`](02__dns.md) | `sg aws dns` — Route 53 zones, records, propagation checks |
| 03 | [`03__acm.md`](03__acm.md) | `sg aws acm` — read-only ACM certificate inventory |
| 04 | [`04__billing.md`](04__billing.md) | `sg aws billing` — daily/weekly/MTD spend + charts |
| 05 | [`05__cloudfront.md`](05__cloudfront.md) | `sg aws cf` — distribution list / show / create / disable / delete / wait |
| 06 | [`06__iam.md`](06__iam.md) | `sg aws iam` — roles, trust policies, policy attach/detach, audit |
| 07 | [`07__lambda.md`](07__lambda.md) | `sg aws lambda` — info / details / config / logs / invocations / invoke / url |
| 08 | [`08__credentials.md`](08__credentials.md) | `sg aws credentials` — Keychain-backed long-lived credentials store |
| 09 | `09__s3.md` *(PROPOSED — Slice A)* | `sg aws s3` — S3 object and bucket management |
| 10 | `10__ec2.md` *(PROPOSED — Slice B)* | `sg aws ec2` — EC2 instance management |
| 11 | `11__fargate.md` *(PROPOSED — Slice C)* | `sg aws fargate` — ECS Fargate clusters and tasks |
| 12 | `12__iam-graph.md` *(PROPOSED — Slice D)* | `sg aws iam graph` — IAM-as-graph discovery and cleanup |
| 13 | `13__bedrock.md` *(PROPOSED — Slice E)* | `sg aws bedrock` — Bedrock chat, agents, tools |
| 14 | `14__cloudtrail.md` *(PROPOSED — Slice F)* | `sg aws cloudtrail` — CloudTrail events and trails (read-only) |
| 15 | `15__creds.md` *(PROPOSED — Slice G)* | `sg aws creds` — scoped STS credential delivery |
| 16 | `16__observe.md` *(PROPOSED — Slice H)* | `sg aws observe` — unified observability REPL |

---

## At-a-glance command map

```
sg aws
├── dns                 ← Route 53                  (zones, records, propagation)
│   ├── zones list
│   ├── zone {show,list,check,purge}
│   ├── records {get,add,update,delete,check}
│   └── instance create-record
├── acm                 ← ACM (read-only)           (list, show)
├── billing             ← Cost Explorer             (last-48h, week, mtd, window, summary, chart)
├── cf                  ← CloudFront                (distribution lifecycle)
│   ├── distributions list
│   └── distribution {show,create,disable,delete,wait}
├── iam                 ← IAM                       (role / policy management + audit)
│   ├── role {list,show,create,delete,check}
│   └── policy {attach,detach,list}
├── credentials         ← Keychain credentials store (long-lived keys — see 08__)
├── lambda              ← Lambda                    (per-function verbs + fuzzy name match)
│   ├── list
│   └── <function-name> {info,details,config,logs,invocations,invoke,deploy,delete,
│                         url {create,show,delete}, tags, versions, aliases}
├── s3          ← S3 (PROPOSED — Slice A)           (ls, view, cat, cp, mv, rm, sync, …)
├── ec2         ← EC2 (PROPOSED — Slice B)           (list, describe, start, stop, terminate, …)
├── fargate     ← ECS Fargate (PROPOSED — Slice C)  (cluster/task lifecycle)
├── iam
│   └── graph   ← IAM graph (PROPOSED — Slice D)    (discover, filter, delete, stats, …)
├── bedrock     ← Bedrock (PROPOSED — Slice E)       (chat, agent, tool sub-trees)
├── cloudtrail  ← CloudTrail (PROPOSED — Slice F)    (events, trails — read-only)
├── creds       ← Scoped STS (PROPOSED — Slice G)    (get, scope, audit)
└── observe     ← Observability REPL (PROPOSED — Slice H) (tail, query, stats, agent-trace)
```

`<function-name>` accepts a **fuzzy substring** — e.g. `sg aws lambda waker info` resolves to `sg-compute-vault-publish-waker`.

---

## Global conventions

### `--json`

Every command accepts `--json` for machine-readable output. Without it you get a Rich-rendered table or panel.

```bash
sg aws dns zones list                  # pretty table
sg aws dns zones list --json           # JSON to stdout
sg aws billing mtd --json | jq '.totals'
```

### Mutation-gate env vars

Mutating commands refuse to run unless the relevant env var is set. This is a deliberate, narrow safety net — set it for the duration of a single shell session, not in CI.

| Surface | Env var | Gated verbs |
|---------|---------|-------------|
| DNS | `SG_AWS__DNS__ALLOW_MUTATIONS=1` | `records add/update/delete`, `zone purge`, `instance create-record` |
| CloudFront | `SG_AWS__CF__ALLOW_MUTATIONS=1` | `distribution create/disable/delete` |
| IAM | `SG_AWS__IAM__ALLOW_MUTATIONS=1` | `role create/delete`, `policy attach/detach` |
| Lambda | `SG_AWS__LAMBDA__ALLOW_MUTATIONS=1` | `<name> deploy/delete`, `<name> url create/delete` |

Read-only verbs (everything in `acm`, `billing`, every `*list/show/check/get/wait`) never require a gate.

### Confirmation prompts

Mutating verbs additionally prompt `[y/N]` unless you pass `--yes` (or `-y`). Inside scripted runs you typically combine `--yes` with the env-var gate:

```bash
SG_AWS__DNS__ALLOW_MUTATIONS=1 sg aws dns records delete tmp.sg-compute.sgraph.ai --yes
```

### AWS credentials and region

All commands use the standard AWS credential chain (`AWS_PROFILE`, `~/.aws/credentials`, env vars, IMDS on EC2, etc.). Override the region with `AWS_REGION=us-west-2` per invocation.

`sg aws acm list` is the one exception — it scans both the **current region** and **`us-east-1`** by default (because CloudFront certs live in us-east-1). Use `--region` to single-region it.

### Help is always there

```bash
sg aws --help
sg aws dns --help
sg aws dns records --help
sg aws dns records add --help
```

Every level of the tree prints its own help. The per-file pages in this pack include the same content but with copy-paste examples a `--help` page doesn't.

---

## Source-of-truth pointer

When a flag in this pack disagrees with what the CLI prints, **the CLI wins**. Open a PR fixing the doc. The CLI surface lives under:

```
sgraph_ai_service_playwright__cli/aws/<area>/cli/
sgraph_ai_service_playwright__cli/aws/lambda_/cli/         ← lambda is a dynamic Click group
```

Backing service classes live one level up under `service/`. The user pages in this pack include a short "what backs this" pointer at the bottom of each section.
