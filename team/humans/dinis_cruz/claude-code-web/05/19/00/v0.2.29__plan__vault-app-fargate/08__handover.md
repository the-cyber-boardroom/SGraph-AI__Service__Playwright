---
title: "`sg vault-app fargate` — handover / start here"
status: handover
audience: executing-agent
author: claude-opus-4-7
date: 2026-05-19
read_first: true
---

# Start here

You are an executing agent (Sonnet) picking up implementation of
`sg vault-app fargate`. **Read this doc first, then follow it.** Do not
start writing code until you've completed the reading list and the
pre-flight checklist.

## TL;DR — your job

Implement V1 of `sg vault-app fargate` in eight slices, in order. The
design is fully specified in this folder. Your job is execution: read,
verify against the live codebase, delegate each slice to a focused
subagent, review their work, commit + push, move to the next slice.

**Current state when you start:** branch `claude/review-vault-publish-spec-FT9hq`
holds the plan (7 docs in this folder + this handover). No
implementation has begun. Slice 0a is the first commit you'll add.

## Reading order (do this first, in order)

1. `00__overview.md` — north star + architecture, two-mode shape
2. `07__decisions.md` — **authoritative**; overrides earlier docs where
   they conflict (Q1, Q3, Q4 had material revisions)
3. `01__sg-aws-extensions.md` — slice 0 pre-work blockers
4. `02__cli-design.md` — full command tree, output formats, slug/cluster
   semantics
5. `03__orchestrator-design.md` — service classes, schemas, AWS-client
   wiring
6. `04__timing-instrumentation.md` — `Phase__Timer`, live progress, JSON
   envelope
7. `05__implementation-slices.md` — the slice-by-slice plan you'll execute
8. `06__open-questions.md` — historical (already answered by 07); skim
   only if curious about alternatives

After reading: you should be able to answer in one sentence each:
"what does the start command do?", "what's on the cluster's tag set?",
"why is there no config file?", "what's the difference between a slug
and a cluster?", "what env var unlocks mutations?". If any answer
isn't crisp, re-read.

## Pre-flight checklist (before slice 0a)

Run from the repo root, do not skip:

```bash
# 1. Sync dev — the plan was researched at a specific commit; dev moves
git fetch origin dev
git merge origin/dev --no-edit
git push -u origin claude/review-vault-publish-spec-FT9hq

# 2. Verify baseline tests green
python -m pytest tests/unit/sgraph_ai_service_playwright__cli/aws/ -q --no-header \
  --ignore=tests/unit/sgraph_ai_service_playwright__cli/aws/iam/service/test_Waker__Policy__Template.py

# (The Waker_Policy_Template failure is pre-existing on dev — not your
# problem. If any OTHER test fails, stop and ask before proceeding.)

# 3. Re-verify the slice-0a gaps still exist in the live tree
#    (the plan researched these at a specific moment; dev moves)
grep -n "executionRoleArn\|portMappings\|launchType\|capacityProviderStrategy" \
  sgraph_ai_service_playwright__cli/aws/fargate/service/Fargate__AWS__Client.py | head -20
ls sgraph_ai_service_playwright__cli/aws/logs/cli 2>/dev/null     # should NOT exist
ls sgraph_ai_service_playwright__cli/aws/ec2/cli/Cli__EC2__Eni.py 2>/dev/null  # should NOT exist
```

If any pre-flight finding contradicts the plan (e.g. someone added
`--port-mapping` on dev while you were reading), **stop and re-scope
the slice before starting** — don't silently work around it.

## Canonical files to read end-to-end before writing any new code

These are the patterns the plan tells you to mirror. Read them as
literal source-code references, not summaries:

- `sgraph_ai_service_playwright__cli/aws/ecr/cli/Cli__Ecr.py`
- `sgraph_ai_service_playwright__cli/aws/ecr/service/ECR__AWS__Client.py`
- `tests/unit/sgraph_ai_service_playwright__cli/aws/ecr/service/ECR__AWS__Client__In_Memory.py`
- `tests/unit/sgraph_ai_service_playwright__cli/aws/ecr/cli/test_Cli__Ecr.py`
- `sgraph_ai_service_playwright__cli/aws/fargate/cli/Cli__Fargate.py` (what you'll extend in slice 0a)
- `sgraph_ai_service_playwright__cli/aws/fargate/service/Fargate__AWS__Client.py` (what you'll extend in slice 0a)
- `sgraph_ai_service_playwright__cli/aws/_shared/Mutation__Gate.py` (the `@require_mutation_gate` decorator pattern)
- `sg_compute_specs/vault_publish/setup/cli/Cli__Setup.py` (the live-progress renderer at lines 673–715)
- `sg_compute_specs/vault_publish/cli/Cli__Vault_Publish.py` (the wake-style HTTP poll at lines 95–196)
- The project CLAUDE.md at `/home/user/SGraph-AI__Service__Playwright/.claude/CLAUDE.md` — non-negotiable conventions

## How to execute a slice (the loop)

For each slice in `05__implementation-slices.md`, in order:

1. **Re-read the slice section** in `05__implementation-slices.md` for
   the slice you're about to do.
2. **Verify the prior slice's commits are on the branch and pushed.**
   (Slices stack; later slices import from earlier ones.)
3. **Delegate the implementation to a focused subagent.** Use the
   template in the next section. Run in background. Do NOT try to write
   the slice inline — past experience: each slice is 600–1500 LOC and
   delegating keeps your context for review + integration.
4. **Wait for the subagent to complete.** It will report files changed,
   test counts, and any deviations.
5. **Review the changes.**
   - `git status -s` to see scope
   - Spot-read the most critical file (the service class or CLI module)
   - Run tests yourself: full `tests/unit/sgraph_ai_service_playwright__cli/aws/`
     suite must be green (minus the pre-existing Waker_Policy_Template).
6. **Commit + push** with a descriptive message (see existing commits on
   this branch for tone — `226dbce5`, `21e10273`, `600cc0d1` are good
   models — multi-paragraph body explaining what + why + test counts).
7. **Move to the next slice.**

**Do NOT batch slices into a single commit.** Each slice is a separate
commit so the work can be reviewed and reverted independently.

## Subagent delegation template

This is the prompt shape that worked across ECR + EC2 slices. Adapt
per-slice but keep the structure. Use `subagent_type: general-purpose`
unless the task is purely exploratory (then `Explore`).

```
Implement Slice <N> of `sg vault-app fargate` — <short slice name>.

**Working directory:** /home/user/SGraph-AI__Service__Playwright
**Branch:** claude/review-vault-publish-spec-FT9hq (already checked out)
**Plan section:** /home/user/SGraph-AI__Service__Playwright/team/humans/dinis_cruz/claude-code-web/05/19/00/v0.2.29__plan__vault-app-fargate/05__implementation-slices.md (Slice <N> section)
**Reading list (read end-to-end before writing code):**
  - <list canonical files for the slice — see "Canonical files" above>
  - <plus the prior slice's output as a near-neighbor pattern>

**Scope (be specific):**
  - <copy the slice's bullet list from 05__implementation-slices.md>

**Conventions (non-negotiable, from .claude/CLAUDE.md):**
  - Type_Safe everywhere; no plain Python classes
  - One class per file; empty __init__.py; never re-export
  - 80-char ═ headers on every Python file
  - No docstrings, ever; inline comments only
  - No mocks, no patches — use in-memory clients
  - Mutation commands use @require_mutation_gate(<env_var>) from aws/_shared/Mutation__Gate.py
  - All AWS calls go through aws/<service>/service/*__AWS__Client.py — vault-app code never imports boto3

**Tests:**
  - Mirror the ECR test file layout
  - Run after writing: `python -m pytest tests/unit/.../<your-area>/ -v`
  - Full aws/ suite must remain green (minus pre-existing Waker_Policy_Template failure)

**Do NOT:**
  - Commit or push (the parent agent will do that after review)
  - Implement anything outside this slice's scope
  - Touch <list explicitly off-limits areas>

**Report on completion:**
  - Files created/modified (paths)
  - Approximate LOC + test counts
  - Any deviations from the brief and why
  - Any contradictions found between the plan and the live codebase
```

## What "done" looks like for each slice

- New + edited files match the slice's scope (no surprise areas touched)
- `python -m pytest tests/unit/sgraph_ai_service_playwright__cli/aws/ -q --no-header --ignore=tests/unit/sgraph_ai_service_playwright__cli/aws/iam/service/test_Waker__Policy__Template.py` is green
- One commit on `claude/review-vault-publish-spec-FT9hq`, pushed to origin
- Commit message explains what + why + test counts (see existing commits as models)

For the V1 finale (after slice 7): the branch should be ready for a PR
to dev. Don't open the PR unless the user explicitly asks for it.

## Contradiction-handling protocol

If, while executing, you find the plan contradicts the live codebase:

- **Trivial divergence** (e.g. a file moved by one directory) — fix the
  plan reference and proceed; mention in the commit message.
- **Material divergence** (e.g. a flag the plan says to add already
  exists; an in-memory client now uses a different shape; the mutation
  gate decorator was renamed) — **stop, write up the divergence in a
  short note, and ask the user** before proceeding. Do not silently
  work around it; the divergence might mean the slice changes shape
  or becomes unnecessary.

Sync with dev between slices if more than ~30 minutes elapse, or if
a slice fails to build because something it depends on has shifted.

## Where you start

Slice 0a. Read `05__implementation-slices.md` § "Slice 0a — `sg aws
fargate` essential flags", then run the pre-flight checklist above,
then delegate per the template.

Good luck. Ship one slice at a time.
