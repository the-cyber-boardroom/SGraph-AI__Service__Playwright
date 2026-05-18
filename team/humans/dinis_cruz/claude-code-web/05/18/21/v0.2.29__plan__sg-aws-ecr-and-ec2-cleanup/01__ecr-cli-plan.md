---
title: "Plan — sg aws ecr (image cleanup)"
date: 2026-05-18
author: claude (claude-opus-4-7)
status: PROPOSED — does not exist yet
related:
  - sgraph_ai_service_playwright__cli/aws/lambda_/  (mirror layout & conventions)
  - .github/workflows/build-host-control-ecr.yml    (pushes to sgraph_ai_service_playwright_host)
---

# Plan — `sg aws ecr`

Add an ECR sub-package to the SG CLI so untagged images and stale tags can be reviewed and deleted from the laptop without leaving the REPL.

## Why now

The Host Control image (`sgraph_ai_service_playwright_host`) is now built and pushed manually (see `.github/workflows/build-host-control-ecr.yml`). Without a cleanup surface, every manual release leaves prior `:latest`-shadowed images behind until ECR's lifecycle policy fires (or until storage charges add up). `sg aws ecr` gives an inspection + delete workflow that's safe (mutation-gated) and fast (uses cached creds from `sg aws credentials switch`).

## Surface (read-only first, mutations P1)

```
sg aws ecr repos                                              # list ECR repositories
sg aws ecr repo <name>                                        # repo summary: image count, total bytes, lifecycle policy
sg aws ecr images <repo> [--digest] [--untagged] [--older 30d] [--json]
sg aws ecr image  <repo> <tag-or-digest>                      # one image: digest, size, pushed_at, manifest, tags
sg aws ecr scan   <repo> <tag-or-digest>                      # most-recent scan findings (CRITICAL/HIGH/MED/LOW counts)

# P1 mutations — all gated on SG_AWS__ECR__ALLOW_MUTATIONS=1
sg aws ecr prune  <repo> [--untagged] [--older 30d] [--keep-last 5] [--dry-run] [--yes]
sg aws ecr delete <repo> <tag-or-digest> [--yes]
sg aws ecr repo-create <name> [--lifecycle <preset>]
sg aws ecr repo-delete <name> [--force] [--yes]
```

Defaults that matter:
- `images <repo>` sorts by `pushed_at DESC` so the freshest is at the top
- `prune --untagged` only deletes images whose `imageTags` is empty
- `prune --older 30d` accepts the same TTL grammar as `creds get --ttl` (`1h` / `7d` / `30d`)
- `prune --keep-last 5` keeps the 5 most-recent tagged images regardless of age
- `prune` without `--yes` prints a table of what would be deleted and asks; with `--dry-run` it never deletes

## Architecture (mirrors `lambda_`)

```
sgraph_ai_service_playwright__cli/aws/ecr/
├── cli/
│   └── Cli__Ecr.py                                           # typer app + @spec_cli_errors
├── service/
│   ├── ECR__AWS__Client.py                                   # sole boto3('ecr') boundary
│   └── ECR__Prune__Planner.py                                # pure: takes images + policy → delete plan
├── schemas/
│   ├── Schema__ECR__Repo.py
│   ├── Schema__ECR__Image.py                                 # digest, tags, size, pushed_at, scan_summary
│   ├── Schema__ECR__Scan_Findings.py
│   └── Schema__ECR__Prune__Plan.py                           # what prune *would* delete
├── collections/
│   ├── List__Schema__ECR__Repo.py
│   └── List__Schema__ECR__Image.py
├── enums/
│   └── Enum__ECR__Image_Scan_Status.py                       # IN_PROGRESS / COMPLETE / FAILED
└── primitives/
    ├── Safe_Str__ECR__Repo_Name.py                           # ^[a-z0-9][a-z0-9._/-]{1,255}$
    ├── Safe_Str__ECR__Image_Digest.py                        # ^sha256:[a-f0-9]{64}$
    └── Safe_Str__ECR__Tag.py                                 # ^[\w][\w.-]{0,127}$
```

Wired in `aws/cli/Cli__Aws.py`:

```python
from sgraph_ai_service_playwright__cli.aws.ecr.cli.Cli__Ecr import app as ecr_app
app.add_typer(ecr_app, name='ecr')
```

## Phasing

1. **P0 — read** (`repos`, `repo`, `images`, `image`) — purely list operations, no creds-write risk. Plus the in-memory fake client.
2. **P0 — scan** (`scan`) — read of the most recent ECR image scan; no AWS Inspector dependency.
3. **P1 — prune planner** (`ECR__Prune__Planner` + `prune --dry-run`) — generates a `Schema__ECR__Prune__Plan` listing what would be deleted; never calls `batch_delete_image`.
4. **P1 — prune execute** (`prune --yes`) — actually deletes, gated on `SG_AWS__ECR__ALLOW_MUTATIONS=1` (same mutation-gate decorator used by `ec2`, `s3`).
5. **P2 — repo create/delete + lifecycle policy presets** (`keep-last-10`, `keep-30d`, `dev-aggressive`).

## Open questions

- Region handling: ECR is regional and the Host Control image lives in `eu-west-2` (per `AWS_DEFAULT_REGION`). Use `Aws__Region__Resolver()` (already centralised) so the `sg aws credentials switch` flow + per-command `--region` override apply uniformly.
- Cross-region scan: should `prune` operate across all enabled regions by default, or stay single-region? Recommend single-region (matches `ec2`, `lambda`) with a `--all-regions` flag in P2.
- ECR Public vs Private: scope to ECR Private only for v1. ECR Public (us-east-1, separate boto3 service `ecr-public`) can be a follow-up.

## Test strategy

- `ECR__AWS__Client__In_Memory` with dict-backed image store and `_Fake_Paginator` for `describe_repositories` / `describe_images`. Pattern matches `Lambda__AWS__Client__In_Memory` and the recent `ClientError` shape (`RepositoryNotFoundException`, `ImageNotFoundException`).
- `ECR__Prune__Planner` tests with a synthetic image list — no AWS at all. Verifies `--untagged`, `--older`, `--keep-last`, and combinations.
- One CLI smoke test per command via `CliRunner`, using the in-memory client.

Estimated work: P0+P1 = ~1 day for the full read+prune flow (~12 commands, ~8 schemas, ~25 tests). P2 = a follow-up half-day.
