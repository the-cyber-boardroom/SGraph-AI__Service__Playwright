---
title: "sg aws acm — ACM certificate inventory"
file: 03__acm.md
author: Architect (Claude)
date: 2026-05-17
parent: README.md
---

# 03 — `sg aws acm`

Read-only view of AWS Certificate Manager certificates. No mutations — no gate needed.

---

## Commands

### `sg aws acm list`

List ACM certificates. **Dual-region by default:** scans the current region **plus `us-east-1`** (because CloudFront cert region). Each row shows ARN, domain name, status, type, in-use-by.

```bash
sg aws acm list
sg aws acm list --json
```

**Flags:**
- `--region/-r R` — single-region scan instead
- `--json`

```bash
sg aws acm list --region us-east-1
sg aws acm list --json | jq '.[] | select(.status=="ISSUED" and .domain=="*.sgraph.app")'
```

### `sg aws acm show ARN`

Detailed view of one certificate — SANs, validation status per SAN, key algorithm, issued date, days-to-expiry, in-use-by ARNs.

```bash
sg aws acm show arn:aws:acm:us-east-1:123456789012:certificate/abcd1234
sg aws acm show <arn> --json
```

The region is auto-detected from the ARN — no `--region` needed.

---

## Patterns

**Find every cert that expires in <30 days:**

```bash
sg aws acm list --json | \
  jq -r '.[] | select(.days_to_expiry < 30) | "\(.domain) \(.arn)"'
```

**Find the CloudFront cert covering `*.sgraph.app`:**

```bash
sg aws acm list --region us-east-1 --json | \
  jq -r '.[] | select(.domain | test("sgraph\\.app$")) | .arn'
```

---

## What backs this

Code at `sgraph_ai_service_playwright__cli/aws/acm/`:

| Class | What it does |
|-------|-------------|
| `ACM__AWS__Client` | List dual-region / single-region; `describe_certificate` |

Tests: `tests/unit/sgraph_ai_service_playwright__cli/aws/acm/`.

---

## Not yet implemented

The current surface is read-only. Cert **request / issue / validate / delete** verbs are PROPOSED — covered by v2 vault-publish phase 2a (`sg aws cf` / ACM additions); see the lab harness pack at [`library/dev_packs/v0.3.0__sg-aws-lab-harness/`](../../../dev_packs/v0.3.0__sg-aws-lab-harness/README.md) for the consumer. Today, mint certs via the AWS console or the `aws` CLI.
