# Brief: LETS Workflow — Next Phase Planning
**Date:** 2026-04-27  
**For:** Claude web session — architectural planning  
**From:** Claude Code session (claude/spell-commands-observability-vO6wV)  
**Repo:** `the-cyber-boardroom/SGraph-AI__Service__Playwright`  
**Branch:** `dev` (all code described here is merged and live)

---

## Purpose

This brief is a handover pack for a new Claude web session whose task is to
**plan the next phases of the LETS workflow** for the `sp el lets cf`
command suite.  It is not a development brief — it is an architectural
planning brief.  The output should be a phased plan document (or set of
documents) that the Dev role can pick up and implement.

---

## Reading order

| Doc | Purpose |
|-----|---------|
| [`01__history-and-context.md`](01__history-and-context.md) | Why we built this, in chronological order |
| [`02__what-exists-today.md`](02__what-exists-today.md) | Exact CLI surface, module tree, key classes |
| [`03__source-files-to-read.md`](03__source-files-to-read.md) | Annotated reading list — what to open first |
| [`04__next-phase-planning-prompt.md`](04__next-phase-planning-prompt.md) | The actual task for the planning session |
| [`05__ephemeral-kibana-setup-and-debug.md`](05__ephemeral-kibana-setup-and-debug.md) | The prerequisite stack: how to launch, inspect, and debug the Ephemeral Kibana |

Read in order.  By the end of doc 3 you will have a clear mental model of
the existing system.  Doc 4 frames the planning question.  Doc 5 is the
operator reference for the underlying stack that all LETS commands target.

---

## One-paragraph orientation

The SG Playwright Service has a CLI tool (`sp`) with a sub-command tree.
The `sp el lets cf` branch of that tree implements a **LETS pipeline**
(Load, Extract, Transform, Save) over CloudFront real-time logs that AWS
Firehose writes to S3.  Two slices are complete: **inventory** (S3 listing
metadata → Kibana) and **events** (`.gz` content reading → parsed
`Schema__CF__Event__Record` → Kibana).  A third sibling command group,
`sp el lets cf sg-send`, provides convenience shortcuts hardcoded to the
SGraph-Send CloudFront bucket.  Two of those shortcuts exist today (`files`
and `view`).  The planning session should design the rest.
