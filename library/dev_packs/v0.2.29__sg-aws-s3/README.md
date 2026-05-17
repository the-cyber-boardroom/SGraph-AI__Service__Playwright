---
title: "v0.2.29 — sg aws s3 (Slice A)"
file: README.md
author: Architect (Claude)
date: 2026-05-17
status: PROPOSED — independent sibling pack of v0.2.29__sg-aws-primitives-expansion
size: M-L — ~2200 prod lines, ~800 test lines, ~3 calendar days
parent_umbrella: library/dev_packs/v0.2.29__sg-aws-primitives-expansion/
source_brief: team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__dev-brief__s3-native-cli-support.md
feature_branch: claude/aws-primitives-support-uNnZY-s3
---

# `sg aws s3` — Slice A

S3 absorbed into the type-safe SG `sg aws *` surface, including the vim round-trip edit flow the recent vim-from-CLI capability unlocked.

> **PROPOSED — does not exist yet.** Cross-check `team/roles/librarian/reality/aws-and-infrastructure/` before describing anything here as built.

---

## Where this fits

This is **one of eight sibling slices** of the v0.2.29 milestone. The umbrella pack at [`v0.2.29__sg-aws-primitives-expansion/`](../v0.2.29__sg-aws-primitives-expansion/README.md) owns the locked decisions, the [Foundation brief](../v0.2.29__sg-aws-primitives-expansion/02__common-foundation.md), and the [orchestration plan](../v0.2.29__sg-aws-primitives-expansion/03__sonnet-orchestration-plan.md). **Read the umbrella first.**

This slice can be reviewed, approved, scheduled, cancelled, or descoped without affecting any other sibling. Slice H (observability) depends on this slice's `S3__AWS__Client` — but that dependency is mediated by the Foundation-shipped interface stub, so the slices run in parallel.

---

## Source brief

[`v0.27.43__dev-brief__s3-native-cli-support.md`](../../../team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__dev-brief__s3-native-cli-support.md) is ground truth. This pack restates the brief's command surface for Dev convenience; if anything below contradicts the brief, the brief wins.

The [`addendum`](../../../team/humans/dinis_cruz/briefs/05/17/from__daily-briefs/v0.27.43__addendum__s3-and-observability-additional-context.md) flags that CloudFront-via-Firehose logs already land in S3 — they're a configured S3 prefix, not a new source. No new code here; just relevant for Slice H consumption.

---

## What you own

**Folder:** `sgraph_ai_service_playwright__cli/aws/s3/` (Foundation ships the skeleton; you fill in the bodies)

### Verbs (per the brief §"The Command Surface")

| Verb | Tier | Notes |
|------|------|-------|
| `ls [path]` | read-only | List buckets, or list within an `s3://bucket/prefix/` |
| `view <s3-path>` | read-only | Pretty-print with format detection (JSON/YAML/MD/CSV) |
| `cat <s3-path>` | read-only | Raw content to stdout; streams for large objects |
| `tail <s3-path>` | read-only | `-n N` (default 100); useful for logs |
| `head <s3-path>` | read-only | `-n N` (default 10) |
| `stat <s3-path>` | read-only | Size, ETag, modified, encryption, versioning, storage class |
| `presign <s3-path>` | read-only | Generate presigned URL with `--ttl <duration>` (default 1 h, cap 7 d) |
| `search <bucket> <pattern>` | read-only | Glob-style key match; paginated |
| `bucket-list` | read-only | All buckets in account |
| `bucket-stat <name>` | read-only | Object count, total size, storage class breakdown |
| `edit <s3-path>` | mutating | vim round-trip with ETag conflict detection |
| `cp <src> <dst>` | mutating | Either side `s3://...` or local |
| `mv <src> <dst>` | mutating | `cp` + delete |
| `rm <s3-path>` | mutating | Delete; `[y/N]` prompt + `--yes` |
| `sync <src> <dst>` | mutating | rsync-style: `--dry-run`, `--delete`, `--exclude`, `--include`, `--checksum`, `--reverse` |
| `bucket-create <name>` | mutating | Sensible defaults (versioning on, public access blocked, SSE-S3 default) |
| `bucket-config <name>` | mutating | Set versioning / lifecycle / encryption / public-access-block |

**Mutation gate:** `SG_AWS__S3__ALLOW_MUTATIONS=1` required for `edit / cp / mv / rm / sync / bucket-create / bucket-config`.

### vim integration

The brief §"The vim Integration" is the spec. Concretely:

1. `edit <s3-path>` resolves the path to a versioned (ETag-captured) object.
2. Downloads to a temp file (`$SG_AWS__S3__EDIT_TMPDIR` or `/tmp/sg-aws-s3-edit-<run-id>/`).
3. Invokes `$EDITOR` (default `vim`).
4. On editor exit code 0:
   - If file unchanged → log "no change, skipping upload" and exit clean.
   - If changed → re-GET head to compare ETag.
     - ETag unchanged → upload with `IfMatch=<original-etag>` (S3 conditional PUT).
     - ETag changed → refuse upload, write the new file to `<temp>.conflict`, surface a diff between local and remote, exit non-zero.
5. Always cleans up temp file unless `--keep-local`.

### Format-aware rendering (per brief §"Smart Format Handling")

| Format | Detection | Rendering |
|--------|-----------|-----------|
| JSON | extension `.json` or content-sniff | Rich JSON syntax highlight |
| YAML | extension `.yml`/`.yaml` | Rich YAML highlight |
| Markdown | extension `.md` | Light Rich render |
| CSV/TSV | extension or first-line sniff | Rich table (auto-column-width) |
| Plain text / logs | default | Raw |
| Binary (images, PDFs, etc.) | content-sniff | Metadata panel; offer `--download` |
| `.tar.gz`, `.zip` | extension | List contents without extracting |
| `.encrypted` (vault header) | first-bytes sniff | Note encryption state; offer to decrypt if a key is loaded |

`--raw` skips detection.

### Sync semantics

Mirrors `aws s3 sync` defaults but with the SG conventions: every transferred object gets the standard `sg:*` tags; `--dry-run` is the default first iteration when used interactively; `--checksum` mode uses MD5 (S3 ETag for single-part) or SHA256 (sg-managed objects).

---

## Production files (indicative)

```
aws/s3/
├── cli/
│   ├── Cli__S3.py
│   └── verbs/
│       ├── Verb__S3__Ls.py
│       ├── Verb__S3__View.py
│       ├── Verb__S3__Cat.py
│       ├── Verb__S3__Tail.py
│       ├── Verb__S3__Head.py
│       ├── Verb__S3__Stat.py
│       ├── Verb__S3__Presign.py
│       ├── Verb__S3__Search.py
│       ├── Verb__S3__Edit.py
│       ├── Verb__S3__Cp.py
│       ├── Verb__S3__Mv.py
│       ├── Verb__S3__Rm.py
│       ├── Verb__S3__Sync.py
│       ├── Verb__S3__Bucket__List.py
│       ├── Verb__S3__Bucket__Stat.py
│       ├── Verb__S3__Bucket__Create.py
│       └── Verb__S3__Bucket__Config.py
├── service/
│   ├── S3__AWS__Client.py             # wraps Sg__Aws__Session
│   ├── S3__Path__Resolver.py          # s3://bucket/key parsing + default-bucket fallback
│   ├── S3__Format__Detector.py
│   ├── S3__Vim__Editor.py             # the round-trip flow
│   ├── S3__Sync__Engine.py
│   └── S3__Source__Adapter.py         # implements Source__Contract — consumed by Slice H
├── schemas/                            # per-class files: Schema__S3__Object, ...Bucket__Stat, ...Sync__Plan, etc.
├── enums/                              # Enum__S3__Storage_Class, Enum__S3__Conflict__Resolution
├── primitives/                         # Safe_Str__S3__Path, Safe_Str__S3__Bucket, Safe_Str__S3__Key, Safe_Str__S3__ETag
└── collections/                        # List__Schema__S3__Object, Dict__S3__Sync__Delta
```

---

## What you do NOT touch

- Any other surface folder under `aws/`
- `aws/_shared/` (Foundation-owned; import only, never modify)
- `Cli__Aws.py` (Foundation already wired your group)
- Vault-aware wrappers (`s3 vault-open/sync/diff/ls`) — out of scope, ship in v0.2.30
- Direct boto3 calls — `S3__AWS__Client` wraps `Sg__Aws__Session` via `osbot-aws`

---

## Acceptance

Run from a fresh checkout of the integration branch with Foundation merged:

```bash
# read-only
sg aws s3 bucket-list                                                  # → table or --json
sg aws s3 ls s3://sg-test-bucket/                                      # → key listing
sg aws s3 stat s3://sg-test-bucket/sample.json                         # → metadata panel
sg aws s3 view s3://sg-test-bucket/sample.json                         # → pretty JSON
sg aws s3 view s3://sg-test-bucket/data.csv                            # → Rich table
sg aws s3 tail s3://sg-test-bucket/logs/today.log -n 50                # → last 50 lines
sg aws s3 presign s3://sg-test-bucket/sample.json --ttl 15m            # → URL
sg aws s3 search sg-test-bucket "logs/2026-05-*.log" --json | jq length

# mutating (gated)
SG_AWS__S3__ALLOW_MUTATIONS=1 sg aws s3 bucket-create sg-test-tmp-$(date +%s) --yes
SG_AWS__S3__ALLOW_MUTATIONS=1 sg aws s3 cp ./local.json s3://sg-test-bucket/uploaded.json --yes
SG_AWS__S3__ALLOW_MUTATIONS=1 sg aws s3 edit s3://sg-test-bucket/configs/agent.json   # vim opens; modify; :wq → upload
SG_AWS__S3__ALLOW_MUTATIONS=1 sg aws s3 sync ./local-dir s3://sg-test-bucket/synced/ --dry-run
SG_AWS__S3__ALLOW_MUTATIONS=1 sg aws s3 rm s3://sg-test-bucket/uploaded.json --yes

# vim conflict round-trip
# (start `edit` in one shell; in another, mutate the object; complete the edit; expect refusal with diff)

# unit tests
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/s3/ -v

# integration tests (gated on a real test bucket env var)
SG_AWS__S3__TEST_BUCKET=sg-test-bucket-<unique> \
  pytest tests/integration/sgraph_ai_service_playwright__cli/aws/s3/ -v
```

---

## Deliverables

1. All files under `aws/s3/` per the layout above
2. Unit tests under `tests/unit/sgraph_ai_service_playwright__cli/aws/s3/` (no mocks; in-memory composition)
3. Integration tests under `tests/integration/sgraph_ai_service_playwright__cli/aws/s3/` (gated on `SG_AWS__S3__TEST_BUCKET`)
4. New user-guide page `library/docs/cli/sg-aws/09__s3.md` (~6-7 KB, same shape as `07__lambda.md`)
5. One row added to `library/docs/cli/sg-aws/README.md` "at-a-glance command map"
6. Reality-doc update: new `team/roles/librarian/reality/aws-and-infrastructure/s3.md` marked `LANDED — v0.2.29`

---

## Risks to watch

- **ETag conflict semantics.** S3 multipart uploads have multi-component ETags; equality check works for single-part but you cannot reconstruct it from local content. Use conditional `If-Match` PUT and surface the AWS-returned 412 cleanly.
- **Default bucket.** A `$SG_AWS__S3__DEFAULT_BUCKET` env var lets users omit `s3://bucket/` from short commands. Refuse to mutate when no bucket is explicit in the path AND no env var set (avoids "oops wrong bucket" mutations).
- **vim cleanup on Ctrl-C.** Register a signal handler so `Ctrl-C` during the `edit` flow still deletes the temp file unless `--keep-local`.
- **Streaming for `cat / tail` on large objects.** Don't buffer the full object; use the streaming `GetObject` body and chunk to stdout.
- **Public-access defaults on `bucket-create`.** Default to fully blocked (BlockPublicAcls / IgnorePublicAcls / BlockPublicPolicy / RestrictPublicBuckets all `true`). Override only with explicit `--allow-public` flag plus the mutation gate.
- **`sync --delete`.** Off by default. Always print the deletion list before action.
- **Compression handling.** `view` / `cat` / `tail` should transparently de-compress `.gz` and `.zstd`. `cp` / `sync` do not transcode.

---

## Commit + PR

Branch: `claude/aws-primitives-support-uNnZY-s3` (off `claude/aws-primitives-support-uNnZY`)

Commit message style: `feat(v0.2.29): sg aws s3 — primitives, vim round-trip, format-aware rendering`.

Open PR against `claude/aws-primitives-support-uNnZY` (integration branch). Tag the Opus coordinator. Do **not** merge yourself.

---

## Cancellation / descope

This pack is independent. To cancel: archive this folder with a `STATUS: CANCELLED` note in the README and drop the row from the umbrella's sibling-pack index. No other artefact needs to change. Slice H falls back to its `S3__AWS__Client` interface stub and ships its S3 source as `NotImplementedError` until S3 lands later.
