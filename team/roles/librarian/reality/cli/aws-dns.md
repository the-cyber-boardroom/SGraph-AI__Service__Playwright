# cli — `sg aws dns` + `sg aws acm`

**Parent:** [`index.md`](index.md) | **Last updated:** 2026-05-17
**Source:** `_archive/v0.1.31/16__sg-aws-dns-and-acm.md` (2026-05-15 slice).

Route 53 DNS management + ACM certificate inventory CLI surface. Layered on top of the `sg_compute.cli.Cli__SG:app` aggregator (post-`provision_ec2.py` retirement).

---

## EXISTS (code-verified)

### CLI surface — under `sg aws`

```
sg aws dns
├── zones list                                  # account-wide: list all hosted zones
├── zone (z)                                    # operations on one zone
│   ├── show  [<zone>]                          # metadata (default: sg-compute.sgraph.ai)
│   ├── list  [<zone>]                          # records in zone
│   ├── check [<zone>]                          # health-check: orphaned / stale / unmatched / ignored
│   └── purge [<zone>] [--only orphaned|stale]  # batch DELETE candidates
├── records (r)
│   ├── add    [<arg1>] [<arg2>] [--value <ip>] [--type A] [--ttl 60] [--zone <z>] [--yes] [--no-verify] [--wait] [--wait-timeout] [--force] [--json]
│   ├── update <name> --value <ip> [--type A] [--ttl 60] [--zone <z>] [--yes] [--no-verify] [--json]
│   ├── delete <name> [--type A] [--zone <z>] [--yes] [--json]
│   ├── check  <name> [--type A] [--zone <z>] [--expect <v>] [--public-resolvers] [--local] [--all] [--yes] [--min-resolvers N] [--json]
│   ├── get    <name> [--type A] [--zone <z>] [--json]
│   └── list   [<zone>] [--json]
└── instance (i)
    └── create-record [<instance>] [--name <fqdn>] [--zone <z>] [--ttl 60] [--type A] [--yes] [--no-verify] [--wait] [--wait-timeout] [--force] [--json]

sg aws acm
├── list [--region <r>] [--all-regions] [--json]
└── show <arn>          [--region <r>] [--json]
```

### Mutation gates

- `records update` and `records delete` require `SG_AWS__DNS__ALLOW_MUTATIONS=1` env var (Q4 safety net).
- `records add` and `instance create-record` use confirmation prompts only (skippable with `--yes`).
- `zone purge` uses confirmation prompt only (multi-DELETE — preview table shown before prompt).

**Default zone:** `sg-compute.sgraph.ai`. Override with `SG_AWS__DNS__DEFAULT_ZONE`.

### Smart `records add` positional dispatch

| Invocation | Behaviour |
|------------|-----------|
| `records add` | Latest running SG-managed instance + derived `<stack>.<default-zone>` |
| `records add <fqdn>` (has dots) | Latest instance + given FQDN |
| `records add <i-id\|stack-name>` | That instance + derived name |
| `records add <i-id\|stack-name> <fqdn>` | Both pinned |
| `records add <fqdn> --value <ip>` | Explicit value (no instance lookup) |
| `records add <i-id> --value <fqdn>` | Instance + given FQDN (alternative syntax) |

---

### Module layout — `sgraph_ai_service_playwright__cli/aws/`

| Layer | Files |
|-------|-------|
| **dns/enums** (4) | `Enum__Route53__Record_Type`, `Enum__Dns__Resolver` (8 public; smart-verify subset of 6), `Enum__Dns__Check__Mode`, `Enum__Smart_Verify__Decision` |
| **dns/primitives** (4) | `Safe_Str__Hosted_Zone_Id`, `Safe_Str__Domain_Name` (incl. `*.` wildcard), `Safe_Str__Record_Name` (multi-label RFC 1035), `Safe_Int__TTL` |
| **dns/schemas** (7) | `Schema__Route53__Hosted_Zone`, `Schema__Route53__Record`, `Schema__Route53__Change__Result`, `Schema__Dig__Result`, `Schema__Dns__Check__Result`, `Schema__Smart_Verify__Decision`, `Schema__Smart_Verify__Result` |
| **dns/collections** (2) | `List__Schema__Route53__Hosted_Zone`, `List__Schema__Route53__Record` |
| **dns/service** (8) | `Route53__AWS__Client` (boto3 boundary — list/get/create/upsert/delete/batch-delete + get_change/wait_for_change), `Dig__Runner` (subprocess wrapper, `LC_ALL=C`), `Route53__Authoritative__Checker` (direct NS query via `dig @ns +norecurse`), `Route53__Public_Resolver__Checker` (6 / 8-resolver fan-out), `Route53__Local__Checker` (host default resolver), `Route53__Check__Orchestrator`, `Route53__Smart_Verify`, `Route53__Zone__Resolver` (deepest-zone label walker), `Route53__Instance__Linker` (EC2 i-id / Name tag / `--latest` resolver) |
| **dns/cli** (1) | `Cli__Dns` — full Typer surface, three WARNING banners as module-level constants, `@spec_cli_errors` on every command |
| **acm/enums** (2) | `Enum__ACM__Cert_Status`, `Enum__ACM__Cert_Type` |
| **acm/schemas** (1) | `Schema__ACM__Certificate` |
| **acm/collections** (1) | `List__Schema__ACM__Certificate` |
| **acm/service** (1) | `ACM__AWS__Client` (boto3 boundary — list/describe + `get_validation_record_names`) |
| **acm/cli** (1) | `Cli__Acm` |
| **cli** (1) | `Cli__Aws` — parent Typer group wiring `dns` + `acm` |

**Wiring:** `sg_compute/cli/Cli__SG.py` adds one `add_typer(_aws_app, name='aws')` line.

**Aliases:** `r` → `records`, `z` → `zone`, `i` → `instance` (hidden short aliases).

---

### Verification design — zero-cache-pollution by default

`records check` (and the smart-verify path inside `records add/update/delete`) is built around the asymmetry between authoritative and recursive DNS lookups:

| Mode | Default | What it does | Cache impact |
|------|---------|--------------|--------------|
| `--authoritative` | yes | `route53:GetHostedZone` → 4 NS → `dig @<ns> +short +norecurse <name>` on each | **Zero** |
| `--public-resolvers` | opt-in (banner + `[y/N]`) | Fan-out to 8 public resolvers | Each caches for the record's TTL → locks in staleness |
| `--local` | opt-in (banner + `[y/N]`) | `dig` against host's default resolver | Local / upstream / corporate proxy caches |
| `--all` | opt-in (combined banner) | All three | Both pollutants |

Verbatim WARNING banners are module-level constants in `Cli__Dns.py` (signed off in brief rev 4).

**Smart-verify after `records add`:**
- **NEW_NAME** path: authoritative + 6-resolver EU+US fan-out automatically. Safe — no prior cache to pollute.
- **UPSERT / DELETE** paths: authoritative only. Skip line tells the operator to wait for the old TTL before running `--public-resolvers` manually.

**`--wait`** polls `route53:GetChange` until status = INSYNC (every 2s, single-line inline progress via `\r`), then runs the authoritative check as final confirmation.

---

### `zone check` classification

| Status | Triggers | Auto-purgeable? |
|--------|----------|-----------------|
| `OK` | A record's leftmost label matches a running EC2 `Name` tag AND the public IP matches the record value | No |
| `STALE` | Name tag matches but public IP differs | Yes |
| `ORPHANED` | A record but no running instance has this `Name` tag | Yes |
| `UNMATCHED` | A record with a multi-label leaf (`api.staging.<zone>`) — manual review | **Never** |
| `IGNORED` | SOA / NS / zone apex / non-A record (incl. CloudFront alias A) | Never |

Smarter classification for IGNORED records (so operators see what each is for):

| Pattern | Note |
|---------|------|
| Alias A → `*.cloudfront.net` | `alias → CloudFront distribution` |
| Alias A → `*.elb.amazonaws.com` | `alias → Elastic Load Balancer` |
| Alias A → `*.s3.amazonaws.com` / `s3-website-*` | `alias → S3 website` |
| Alias A → `*.execute-api.*` | `alias → API Gateway` |
| CNAME value contains `*.acm-validations.aws` | Cross-references `ACM__AWS__Client.get_validation_record_names()` — match → IGNORED (active cert); no match → ORPHANED (stale validation) |
| CNAME name contains `_domainkey` | DKIM record |
| CNAME name starts with `_amazonses.` | SES domain verification |
| CNAME name starts with `autodiscover.` | email autodiscover |
| CNAME name starts with `_acme-challenge` | Let's Encrypt DNS-01 challenge |
| TXT value contains `v=DMARC1` / `v=spf1` / `v=DKIM1` | DMARC / SPF / DKIM policy |
| TXT value contains `google-site-verification` | Google site verification |
| MX | email routing |

ACM lookup is lazy — only fires when an ACM-shaped CNAME is actually seen in the zone.

---

### `--latest` instance detection

Matches running EC2 instances tagged with either:
- Legacy `sg:*` prefix (elastic / playwright / vnc / podman / firefox / neko via `__cli/*/service/*_Tags__Builder.py`).
- New `sg_compute` platform tag `Purpose=ephemeral-ec2` (vault_app / ollama / open_design / etc. via `sg_compute/platforms/ec2/helpers/EC2__Tags__Builder.py`).

Sorted by `LaunchTime` descending; first match wins.

---

### IAM permissions required

| Action | Used by |
|--------|---------|
| `route53:ListHostedZones` | every read command |
| `route53:GetHostedZone` | `zones show`, `zone show`, authoritative-checker (NS lookup) |
| `route53:ListResourceRecordSets` | `zone list`, `records get`, `records add` (pre-flight) |
| `route53:ChangeResourceRecordSets` | all mutations + `zone purge` |
| `route53:GetChange` | `--wait` polling |
| `acm:ListCertificates` | `acm list`, `zone check` ACM cross-reference |
| `acm:DescribeCertificate` | `acm show`, `zone check` ACM cross-reference |
| `ec2:DescribeInstances` | `instance create-record`, `records add`, `zone check`, `--latest` |

---

### Tests — 136 unit tests under `tests/unit/sgraph_ai_service_playwright__cli/aws/`

| File | Cases | Coverage |
|------|------:|----------|
| `test_Stack__Naming` | 9 | Pre-existing (kept) |
| `dns/service/test_Route53__AWS__Client` | 36 | Read + mutation + batch + `get_change` + `wait_for_change` |
| `dns/service/test_Dig__Runner` | 11 | Command construction, exit codes, FileNotFoundError, timeout |
| `dns/service/test_Route53__Authoritative__Checker` | 7 | NS fetch + per-NS dig + agreement |
| `dns/service/test_Route53__Smart_Verify` | 8 | NEW_NAME / UPSERT / DELETE decisions; force_public; no_verify |
| `dns/service/test_Route53__Zone__Resolver` | 9 | Apex / direct child / deepest-match / apex-of-child-zone regression / trailing dot / cache |
| `dns/service/test_Route53__Instance__Linker` | 13 | Instance-id lookup, Name-tag lookup, `--latest` (both `sg:*` and `Purpose=ephemeral-ec2`) |
| `dns/service/test_Route53__Local__Checker` | 4 | Match / mismatch / empty / no-values |
| `dns/cli/test_Cli__Dns__helpers` | 12 | `_resolve_zone_id_for_record` deepest-match + apex-of-child-zone + env-var-override |
| `acm/service/test_ACM__AWS__Client` | 21 | List / describe / dual-region dedupe |

All tests use in-memory subclasses (no `unittest.mock`, no `pytest-mock`).

---

### Known gaps (NOT shipped)

- **`acm list --all-regions`** stubs `"not implemented in P0"`.
- **`acm request` / `acm delete`** (ACM mutations) not in scope.
- **`dns instance create-record`** redundant with smart `records add` — both work; not deprecated yet.
- **§12 ADDENDUM (cert workflow)** — not started. The cert-warning info block points users at `sg playwright vault re-cert --hostname <fqdn>`, which does not exist. **Q9 still PENDING** (DNS-01 vs HTTP-01 for the cert sidecar). Highest-value remaining work.
- **CloudFront support** — entirely deferred (main P2 deliverable of the bigger CF+R53 brief). Partially landed in v0.2.23 (`sg aws cf` — see [`sg-compute/index.md`](../sg-compute/index.md)).
- **Reverse lookup** (which records does instance `i-...` own?) — not in scope.

---

## See also

- Parent: [`index.md`](index.md)
- Source: [`_archive/v0.1.31/16__sg-aws-dns-and-acm.md`](../_archive/v0.1.31/16__sg-aws-dns-and-acm.md)
- Markdown style guide: `library/guides/v0.2.15__markdown_doc_style.md`
- SG/Compute: [`sg-compute/index.md`](../sg-compute/index.md) — v0.2.23 added `sg aws cf` + `sg aws lambda` cousins
