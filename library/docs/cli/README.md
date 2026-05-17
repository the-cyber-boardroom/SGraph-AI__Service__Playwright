---
title: "CLI Reference Docs"
file: README.md
author: Architect (Claude)
date: 2026-05-17
---

# CLI Reference Docs

Operator-facing reference for the CLI surfaces shipped by this repo. Each sub-folder is a self-contained pack covering one top-level command tree.

| Pack | Surface | Covers |
|------|---------|--------|
| [`sg-aws/`](sg-aws/README.md) | `sg aws *` | Route 53 / ACM / Billing / CloudFront / IAM / Lambda. User-focused — how to use each command, env-var gates, copy-paste examples. |

Implementation briefs (architect → dev) live under [`library/dev_packs/`](../../dev_packs/). The packs in this folder describe **what exists today**; the packs in `dev_packs/` describe **what's being built next**.
