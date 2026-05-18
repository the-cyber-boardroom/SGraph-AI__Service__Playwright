---
title: "Plans — sg aws ECR + EC2 AMI/SG cleanup"
date: 2026-05-18
author: claude (claude-opus-4-7)
status: PROPOSED
---

# `sg aws` cleanup surfaces — plan set

Two plans + one status audit for the CLI cleanup work requested on 2026-05-18:

1. **[01__ecr-cli-plan.md](01__ecr-cli-plan.md)** — new `sg aws ecr` sub-package (repo list, image list, scan summary, prune planner + execute). Mutation-gated.
2. **[02__ec2-ami-and-sg-status.md](02__ec2-ami-and-sg-status.md)** — `sg aws ec2` currently has NO AMI or security-group surface. Plan adds two new sub-apps (`ec2 ami`, `ec2 sg`) with `list` / `show` / `orphans` / `delete` commands.

## Trigger

After moving the Host Control ECR image build/push from CI auto-trigger to manual-only (`build-host-control-ecr.yml`), it became obvious that the next gap is "how do I clean up the images this leaves behind, without leaving the REPL". Same for AMIs and SGs — the `ec2 create` command works fine, but there's nothing for finding what to delete.

## Common conventions across both plans

- All new sub-packages mirror the `aws/lambda_` layout (cli/service/schemas/collections/primitives/enums).
- All boto3 calls live in `*__AWS__Client.py` (one file per AWS service).
- All schemas extend `Type_Safe`; no raw dicts cross boundaries.
- All mutations are gated on `SG_AWS__<SERVICE>__ALLOW_MUTATIONS=1` (same pattern as `s3`, `ec2.terminate`).
- All commands use `@spec_cli_errors` so the friendly AWS-error renderer (UnrecognizedClientException, AccessDenied, etc.) kicks in.
- Tests use the `*__In_Memory` fake-client pattern with properly-shaped `ClientError` (not plain `Exception`).
- Region resolution goes through `Aws__Region__Resolver()` so `sg aws credentials switch <role>` flows propagate.

## Not in scope

- ECR Public (separate boto3 service `ecr-public`, us-east-1 only) — defer to a v2 slice.
- AMI sharing across accounts — read-only path is trivial, the cleanup mutations need extra safety thinking; defer.
- Cross-region cleanup — both plans target the active region only; `--all-regions` is a P2 flag in both.
