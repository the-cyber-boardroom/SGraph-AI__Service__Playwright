---
title: "Reality — sg aws namespace"
file: aws.md
domain: cli
author: Librarian (Claude)
date: 2026-05-17
version: v0.2.29
status: ACTIVE — umbrella index for all `sg aws *` sub-groups
---

# Reality — `sg aws` namespace

Umbrella index for the `sg aws *` CLI surface. Each sub-group has its own entry below. Sub-groups marked PROPOSED do not yet have implementations — they are stubbed at the Click level but every verb body raises `NotImplementedError`.

---

## Shared scaffold — `aws/_shared/` (v0.2.29 Foundation)

Landed in v0.2.29 Foundation PR on `claude/aws-primitives-support-uNnZY`.

| Component | Status | File |
|-----------|--------|------|
| `Mutation__Gate` | LANDED | `aws/_shared/Mutation__Gate.py` |
| `Aws__Tagger` | LANDED | `aws/_shared/Aws__Tagger.py` |
| `Aws__Region__Resolver` | LANDED | `aws/_shared/Aws__Region__Resolver.py` |
| `Aws__Confirm` | LANDED | `aws/_shared/Aws__Confirm.py` |
| `Source__Contract` ABC | LANDED | `aws/_shared/source_contract/Source__Contract.py` |
| Shared primitives | LANDED | `aws/_shared/primitives/` |
| Shared schemas | LANDED | `aws/_shared/schemas/` |
| Shared enums | LANDED | `aws/_shared/enums/` |

---

## Mounted sub-groups

| Sub-group | Status | CLI path | Reality doc |
|-----------|--------|----------|-------------|
| `dns` | LANDED — v0.2.x | `aws/dns/cli/Cli__Dns.py` | [`aws-dns.md`](aws-dns.md) |
| `acm` | LANDED — v0.2.x | `aws/acm/cli/Cli__Acm.py` | — |
| `billing` | LANDED — v0.2.x | `aws/billing/cli/Cli__Billing.py` | — |
| `cf` | LANDED — v0.2.x | `aws/cf/cli/Cli__Cf.py` | — |
| `iam` | LANDED — v0.2.x | `aws/iam/cli/Cli__Iam.py` | — |
| `lambda` | LANDED — v0.2.x | `aws/lambda_/cli/` | — |
| `credentials` | LANDED — v0.2.28 (remounted from `sg credentials` per locked decision #13) | `credentials/cli/Cli__Credentials.py` | — |
| `s3` | PROPOSED — Slice A | `aws/s3/cli/Cli__S3.py` (stub) | `aws-s3.md` *(pending Slice A)* |
| `ec2` | PROPOSED — Slice B | `aws/ec2/cli/Cli__EC2.py` (stub) | `aws-ec2.md` *(pending Slice B)* |
| `fargate` | PROPOSED — Slice C | `aws/fargate/cli/Cli__Fargate.py` (stub) | `aws-fargate.md` *(pending Slice C)* |
| `iam graph` | PROPOSED — Slice D | `aws/iam/graph/cli/Cli__Iam__Graph.py` (stub) | `aws-iam.md` extension *(pending Slice D)* |
| `bedrock` | PROPOSED — Slice E | `aws/bedrock/cli/Cli__Bedrock.py` (stub) | `aws-bedrock.md` *(pending Slice E)* |
| `cloudtrail` | PROPOSED — Slice F | `aws/cloudtrail/cli/Cli__CloudTrail.py` (stub) | `aws-cloudtrail.md` *(pending Slice F)* |
| `creds` | PROPOSED — Slice G | `aws/creds/cli/Cli__Creds.py` (stub) | `aws-creds.md` *(pending Slice G)* |
| `observe` | PROPOSED — Slice H | `aws/observe/cli/Cli__Observe.py` (stub) | `aws-observe.md` *(pending Slice H)* |

---

## Notes

- `sg credentials` continues to work as a hidden alias of `sg aws credentials` (muscle-memory preservation). It will be removed in v0.2.30.
- The existing `cli/observability.md` covers the AMP/OpenSearch/Grafana **infrastructure** surface (`sg aws observability` — separate package). The unified observability **read** surface (`sg aws observe`) will live at `aws-observe.md` once Slice H lands.
- Each sibling slice updates its row from PROPOSED → LANDED and creates its own `aws-<surface>.md` in its PR.
