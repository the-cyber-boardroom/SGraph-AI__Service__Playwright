---
title: "Architect Briefing — sg aws dns: Route 53 DNS Management Center"
file: architect__sg-aws-dns__plan.md
author: Architect (Claude)
date: 2026-05-15 (UTC hour 08)
repo: SGraph-AI__Service__Playwright @ dev (v0.1.140 line)
status: PLAN — no code, no commits. For human ratification before Dev picks up.
parent: team/humans/dinis_cruz/claude-code-web/05/15/03/architect__vault-app__cf-route53__plan.md
---

# Architect Briefing — sg aws dns: Route 53 DNS Management Center

> **PROPOSED — does not exist yet.** Nothing in this brief is implemented today.
> Verified: there is no `route53` / `Hosted_Zone` / `Route53__Client` reference
> anywhere under `sg_compute_specs/`, `sg_compute/`, or
> `sgraph_ai_service_playwright__cli/`. The `sgraph_ai_service_playwright__cli/aws/`
> directory exists but contains only `Stack__Naming.py` — a shared helper, not
> a CLI Typer surface. There is currently no `sg aws` command group registered
> anywhere.

---

## 1. Context & relationship to the larger CF+R53 brief

The bigger brief at `team/humans/dinis_cruz/claude-code-web/05/15/03/architect__vault-app__cf-route53__plan.md`
("vault-app: CloudFront + Route 53 + ACM") proposes a *full* edge stack —
CloudFront distribution + ACM wildcard cert + Route 53 alias record — wired into
the vault-app stack-create lifecycle. In that brief, Route 53 is one of three
moving parts and the `Route53__Client` only ever serves the stack-create /
stack-destroy workflow.

**This brief carves out the Route 53 management subset and lifts it to a
standalone CLI surface (`sg aws dns`) that is useful on its own.** It gives the
operator a generic DNS management center — list zones, list records, add /
update / delete records on any zone — independent of whether a stack-creation
flow is in play. The same `Route53__Client` primitive that this brief
introduces is then *consumed* by the larger CF+R53 plan: the bigger plan stops
having to define one and instead orchestrates this one. Concretely:

- **This brief delivers:** `Route53__Client`, the DNS schemas, the `sg aws dns`
  Typer surface, and the test scaffolding (in-memory + integration).
- **The CF+R53 brief later consumes:** `Route53__Client.upsert_a_alias_record(...)`,
  `Route53__Client.upsert_record(...)` (for the `_acme-challenge` TXT DNS-01 flow),
  and `Route53__Client.delete_record_set(...)` during stack tear-down.

That sequencing makes this brief the **pre-requisite** for the CF+R53 plan's
P1 slice, not a competitor. It is also useful in isolation: most operator pain
around DNS today is "list/edit records in the console" — a CLI is faster and
scriptable.

---

## 2. Goals & non-goals

### Goals

1. **List + show hosted zones** in the account, with id / name / public-or-private
   / record-count / comment.
2. **List + get + add + update + delete records** within any zone, addressable
   by zone name or zone id.
3. **Generic, not stack-coupled.** No EC2 / vault-app / stack-name machinery.
   The CLI is callable against any zone, including ones not created by this
   tooling.
4. **JSON output mode** alongside the rich-table default, so the surface is
   scriptable for the larger CF+R53 plan and for any pipeline.
5. **`osbot-aws` discipline.** A new `Route53__AWS__Client` is the **sole**
   boto3 boundary for Route 53 in this repo. Documented narrow exception, same
   pattern as `Elastic__AWS__Client`.
6. **Type_Safe everywhere.** No raw `str` / `int` / `dict` on schemas; no
   Pydantic; no Literals.
7. **Safety net for destructive ops.** Confirmation prompts on `update` /
   `delete`, plus a `--yes` flag for scripted runs.

### Non-goals

- **No ACM cert provisioning.** Covered by the CF+R53 brief.
- **No CloudFront distribution lifecycle.** Covered by the CF+R53 brief.
- **No DNS-01 ACME challenge wiring.** The TXT-record CRUD primitives are
  exposed but the actual ACME flow stays in `Cert__ACME__Client`'s lineage
  (CF+R53 brief P1).
- **Hosted-zone CRUD is OUT of P0/P1.** This brief covers list/show for zones
  only. Whether to add `zones create` / `zones delete` is **Q3** below — flagged
  as P2 pending user sign-off. The vault.sgraph.ai zone-creation step from the
  bigger brief is a one-time operator action today; lifting it to CLI is a
  judgment call about how much foot-gun surface we want.
- **No IAM policy authorship.** Section 7 lists required actions; drafting the
  JSON policy is a follow-up DevOps task.
- **No record-set health checks, no traffic policies, no DNSSEC, no resolver
  rules.** Out of scope. Files a follow-up brief if needed.
- **No multi-account / cross-account zones.** Same-account only; profile /
  region picked up from the standard `AWS_*` env or `--profile`.

---

## 3. CLI surface

Top-level: `sg aws dns` — a Typer sub-app registered under a new (or existing,
once one ships) `sg aws` group. **There is no `sg aws` group today** (verified —
the `sgraph_ai_service_playwright__cli/aws/` dir exists only as a holder for
the shared `Stack__Naming` helper). This brief proposes registering `sg aws`
as a new top-level Typer group whose first member is `dns`. Future siblings
(`sg aws ec2`, `sg aws iam`, ...) can be added without re-platforming.

### Command tree

```
sg aws dns                                  # group help
sg aws dns zones list                       # list all hosted zones in the account
sg aws dns zones show <zone>                # details of one zone (name or id)
sg aws dns records list <zone>              # list records in a zone
sg aws dns records get <zone> <name>        # show one record (defaults to A)
sg aws dns records add <zone> <name>        # create a record
sg aws dns records update <zone> <name>     # upsert / change values
sg aws dns records delete <zone> <name>     # delete (with confirm)
sg aws dns records alias <zone> <name>      # P2 — alias to CF / ELB / S3 (deferred)
```

Zone arguments accept **either**:
- a **zone id** (`Z01234567ABCDEFGHIJKL`) — passed through verbatim, or
- a **zone name** (`example.com` or `example.com.`) — resolved via
  `ListHostedZonesByName` before any other call.

A `--json` flag on every subcommand swaps the rich-table renderer for a stable
JSON dump of the response schema.

### Flag matrix

| Command | Flags |
|---------|-------|
| `zones list`   | `--json` `--region` (R53 is global but `--region` is forwarded to the boto3 client for endpoint selection only) `--profile` |
| `zones show`   | `--json` |
| `records list` | `--json` `--type A` (filter) `--name <substring>` (filter) `--limit 100` |
| `records get`  | `--json` `--type A` (defaults to `A`) |
| `records add`  | `--type A` (required) `--value <ip|val>` (required, repeatable for multi-value) `--ttl 300` (default) `--comment "..."` `--yes` (skip "create?" confirm) `--json` |
| `records update` | `--type A` (required) `--value <ip|val>` (required, repeatable) `--ttl <int>` `--comment "..."` `--yes` (skip "change?" confirm) `--json` |
| `records delete` | `--type A` (required) `--yes` (skip "delete?" confirm) `--json` |
| `records alias` *(P2)* | `--target-type cloudfront|elb|s3` `--target <id-or-domain>` `--yes` `--json` |

### Example invocations + output

**`sg aws dns zones list`** (default table mode):

```
  Hosted zones in account 123456789012  ·  3 zones

  Zone Id                       Name                       Type     Records  Comment
  ────────────────────────────  ─────────────────────────  ───────  ───────  ────────────────────────
  Z01234567ABCDEFGHIJKL         example.com.               public        12  Primary prod zone
  Z09876543ZYXWVUTSRQPO         vault.sgraph.ai.           public         4  Vault stacks (provisioned)
  Z11122233LMNOPQRSTUVW         internal.example.          private        7  VPC-attached
```

**`sg aws dns zones list --json`**:

```json
{
  "account_id": "123456789012",
  "zones": [
    {
      "zone_id": "Z01234567ABCDEFGHIJKL",
      "name": "example.com.",
      "private": false,
      "record_count": 12,
      "comment": "Primary prod zone"
    },
    {
      "zone_id": "Z09876543ZYXWVUTSRQPO",
      "name": "vault.sgraph.ai.",
      "private": false,
      "record_count": 4,
      "comment": "Vault stacks (provisioned)"
    }
  ]
}
```

**`sg aws dns records list vault.sgraph.ai`** (default table mode):

```
  Records in zone vault.sgraph.ai.  ·  Z09876543ZYXWVUTSRQPO  ·  4 records

  Name                                 Type   TTL   Value / Alias Target
  ───────────────────────────────────  ─────  ────  ────────────────────────────────────────
  vault.sgraph.ai.                     NS      172800  ns-1.awsdns-1.com. ns-2.awsdns-2.net. …
  vault.sgraph.ai.                     SOA   900     ns-1.awsdns-1.com. awsdns-hostmaster.…
  quiet-fermi.vault.sgraph.ai.         A     60      203.0.113.42
  zen-curie.vault.sgraph.ai.           A     60      203.0.113.99
```

**`sg aws dns records add vault.sgraph.ai zen-darwin --type A --value 203.0.113.5 --ttl 60`**:

```
  About to create record:
    zone   : vault.sgraph.ai.  (Z09876543ZYXWVUTSRQPO)
    name   : zen-darwin.vault.sgraph.ai.
    type   : A
    ttl    : 60
    value  : 203.0.113.5
  Continue? [y/N]: y

  ✓  Record created  ·  change-id C0123456ABCDEF  ·  status PENDING
  Use `sg aws dns records get vault.sgraph.ai zen-darwin` once propagated.
```

**`sg aws dns records list vault.sgraph.ai --json`**:

```json
{
  "zone_id": "Z09876543ZYXWVUTSRQPO",
  "zone_name": "vault.sgraph.ai.",
  "records": [
    {
      "name": "vault.sgraph.ai.",
      "type": "NS",
      "ttl": 172800,
      "values": ["ns-1.awsdns-1.com.", "ns-2.awsdns-2.net."],
      "alias": null,
      "set_identifier": ""
    },
    {
      "name": "quiet-fermi.vault.sgraph.ai.",
      "type": "A",
      "ttl": 60,
      "values": ["203.0.113.42"],
      "alias": null,
      "set_identifier": ""
    }
  ]
}
```

---

## 4. Open questions — for human ratification before Dev starts

Style mirrors the Q-with-A/B/C-options convention used in the CF+R53 brief.

### Q1 — Where does the code live? Spec-style folder vs CLI-side module.

| Opt | Position |
|-----|----------|
| **A** | New `sg_compute_specs/aws_dns/` mirroring `vault_app/` — `cli/ service/ schemas/ enums/ primitives/ tests/`. Treat it as a full spec. |
| **B** | New `sgraph_ai_service_playwright__cli/aws/dns/` next to the existing `Stack__Naming.py`, with sibling `cli/ service/ schemas/ enums/ primitives/ tests/` folders rooted there. |

**Recommendation: B.** The `sg_compute_specs/*` convention exists to package
**ephemeral-stack** specs (vault-app, elastic, vnc, opensearch, etc.) — every
existing spec ships an EC2 stack lifecycle (Schema__*__Create__Request /
Create__Response / Info / List / `service/*__Service.py` orchestrator). DNS
management has none of that — no stack, no create/destroy, no lifecycle. Forcing
the spec scaffold yields empty `Schema__*__Create__Request.py` files and an
awkward `service/Aws_Dns__Service.py` that doesn't really orchestrate anything.

The `sgraph_ai_service_playwright__cli/aws/` directory **already exists** as the
home for "shared AWS surface used by the CLI but not bound to one stack" (today,
`Stack__Naming.py` lives there). Adding `dns/` next to it is a natural fit:

```
sgraph_ai_service_playwright__cli/aws/
├── __init__.py            (empty, rule #22)
├── Stack__Naming.py       (existing)
├── cli/
│   └── Cli__Aws_Dns.py    (Typer surface)
├── dns/
│   ├── __init__.py        (empty)
│   ├── service/
│   │   └── Route53__AWS__Client.py
│   ├── schemas/
│   │   ├── Schema__Route53__Hosted_Zone.py
│   │   ├── Schema__Route53__Record.py
│   │   ├── Schema__Route53__Record__Alias.py
│   │   ├── Schema__Route53__Change__Result.py
│   │   └── Schema__Route53__Zone__List.py
│   ├── enums/
│   │   └── Enum__Route53__Record_Type.py
│   ├── primitives/
│   │   ├── Safe_Str__Hosted_Zone_Id.py
│   │   ├── Safe_Str__Domain_Name.py
│   │   ├── Safe_Str__Record_Name.py
│   │   ├── Safe_Str__Record_Value.py
│   │   └── Safe_Int__TTL.py
│   └── collections/
│       ├── List__Schema__Route53__Hosted_Zone.py
│       └── List__Schema__Route53__Record.py
└── tests/
    ├── __init__.py
    ├── service/
    │   └── test_Route53__AWS__Client.py
    └── cli/
        └── test_Cli__Aws_Dns.py
```

This keeps **all per-class files one-class-per-file** (rule #21) and **all
`__init__.py` empty** (rule #22). The `cli/Cli__Aws_Dns.py` exposes a Typer
`app` that the eventual top-level `sg aws` Typer group adds as a sub-app via
`aws_app.add_typer(dns_app, name='dns')` (mirroring `firefox/cli/__init__.py`
line 551).

If/when a second AWS surface lands (`sg aws ec2`, `sg aws iam`, ...) the same
`aws/` directory absorbs them. If/when a true *spec* (stack lifecycle) for DNS
emerges later (very unlikely — DNS isn't ephemeral infra), a thin shim under
`sg_compute_specs/` can import from this CLI module.

### Q2 — `add` semantics: strict create, or implicit upsert?

| Opt | Position |
|-----|----------|
| **A** | **`add` is strict CREATE.** Reject (`ResourceRecordSetAlreadyExists`-style error) if a record with the same name + type already exists. `update` is the only way to change an existing record. |
| **B** | **`add` is UPSERT.** If the record exists, replace it. One command for "make sure this record looks like X". |
| **C** | **`add` is strict CREATE by default; `--upsert` flag opts in.** Best of both, more flags. |

**Recommendation: A.** Route 53's `ChangeResourceRecordSets` API has three
explicit verbs (`CREATE`, `UPSERT`, `DELETE`); we mirror them. The asymmetry
`add` (CREATE) vs `update` (UPSERT) is what an operator expects from any RDBMS
CLI: `INSERT` errors on duplicates, `UPDATE` overwrites. It also makes destructive
no-ops (`add` on an existing record that you forgot about) impossible.

`records update` is then an **UPSERT** — if the record doesn't exist, it gets
created with the new values. That asymmetry is intentional: `update` is the
"make this what I say" verb, `add` is the "this is new" verb.

### Q3 — Hosted-zone CRUD: leave out, or add as P2?

| Opt | Position |
|-----|----------|
| **A** | **List/show only.** Zone create / delete stays an operator action (console or `awscli`). Rationale: deleting a zone with live records is catastrophic — registrar delegation breaks, all subdomains go dark. |
| **B** | **Add `zones create` and `zones delete` as P2**, behind `--yes` + an extra "type the zone name to confirm" prompt for delete. |
| **C** | **Add `zones create` only**, never `zones delete`. Creation is mostly safe; deletion is the foot-gun. |

**Recommendation: C, *but defer to user*.** Zone creation is the one bit that
unblocks the bigger CF+R53 brief's bootstrap step ("operator creates
`vault.sgraph.ai` zone out of band"). Lifting that to the CLI is a real win.
Zone deletion is the foot-gun; leaving it out means a deliberately-destructive
operator has to drop to the AWS console, which is a useful speed bump.

Flagged as **Q3-blocker for user**: pick A / B / C. If C, the scope of P2
grows by exactly one command (`zones create <name> [--comment ...]
[--private-vpc-id ...]`).

### Q4 — Confirmation prompts and destructive-op safety net.

| Opt | Position |
|-----|----------|
| **A** | Confirm on `update` and `delete` only; `add` runs silently. `--yes` skips the prompt. |
| **B** | Confirm on **every** mutation (`add`, `update`, `delete`). `--yes` skips. |
| **C** | Confirm on `delete` only; `add` and `update` are silent. `--yes` skips delete. |

**Recommendation: A.** `add` is the create-only verb (Q2-A) so it can't
overwrite anything; the worst it can do is fail with "already exists." `update`
and `delete` are the destructive verbs and warrant a prompt. Mirrors the
"diff preview" expectation from `terraform plan` / `terraform apply`: show
the change, ask before applying. The prompt body shows the **diff** between
current record value (if any) and the new value, so the operator can verify
they typed the right IP.

**Additionally:** gate destructive ops on a `SG_AWS__DNS__ALLOW_MUTATIONS=1`
env var. Default-off means `records update` / `records delete` refuse to run
without explicit opt-in (an unmistakable "yes I really mean it" gate beyond
`--yes`). This is the operator equivalent of the JS allowlist gate on
`Step__Executor.evaluate` — `sg aws` is shared across stacks and a typo on a
prod record is a worse outcome than a noisy "set the env var" error.

### Q5 — Alias record support: P0/P1 or P2?

| Opt | Position |
|-----|----------|
| **A** | **`records alias` is P2.** P1 ships A/AAAA/CNAME/MX/TXT only. Alias requires modelling `AliasTarget` (HostedZoneId, DNSName, EvaluateTargetHealth) and the CF/ELB/S3 zone-id mapping table. Real but separate work. |
| **B** | **Include `records alias` in P1.** The bigger CF+R53 brief needs an alias to CloudFront. Bundling it here saves the bigger brief work. |
| **C** | **Skip the convenience CLI; expose alias support via `records add --alias-target ...` only.** No separate `alias` subcommand. |

**Recommendation: A (P2).** Alias records require a hard-coded mapping of
CloudFront's published hosted-zone-id (`Z2FDTNDATAQYW2`), ELB's per-region
zone-ids, S3 website's per-region zone-ids, etc. That table is brittle and
needs maintenance. The bigger CF+R53 brief can stand up alias records when it
provisions the distribution — at the point of need, the values are known. P1
ships pure-value record types; P2 adds the alias convenience layer.

### Q6 — Region & profile handling.

| Opt | Position |
|-----|----------|
| **A** | Always use the default boto3 profile + env. No CLI flags. |
| **B** | `--profile` and `--region` flags on every command. Route 53 is a global API but we forward `--region` to the boto3 client anyway (it affects endpoint selection and is required if the user has multiple accounts via SSO profiles). |
| **C** | `--profile` only; no `--region` flag (R53 is global). |

**Recommendation: B.** Consistency with the existing `sp el / sp os / sp vault-app`
flag conventions (`--region`, `--profile` everywhere). Even though R53 is global,
operators expect the flag.

---

## 5. Proposed architecture

### Module location: Option B (per Q1)

```
sgraph_ai_service_playwright__cli/
└── aws/                                       (existing — empty __init__.py + Stack__Naming.py)
    ├── __init__.py                            (empty)
    ├── Stack__Naming.py                       (existing, unchanged)
    │
    ├── cli/
    │   ├── __init__.py                        (empty)
    │   └── Cli__Aws_Dns.py                    (Typer surface — NEW)
    │
    └── dns/                                   (NEW)
        ├── __init__.py                        (empty)
        ├── service/
        │   ├── __init__.py                    (empty)
        │   └── Route53__AWS__Client.py        (sole boto3 boundary — NEW)
        ├── schemas/
        │   ├── __init__.py                    (empty)
        │   ├── Schema__Route53__Hosted_Zone.py
        │   ├── Schema__Route53__Record.py
        │   ├── Schema__Route53__Record__Alias.py    (P2 prep — empty placeholder OK)
        │   ├── Schema__Route53__Change__Result.py
        │   └── Schema__Route53__Zone__List.py
        ├── enums/
        │   ├── __init__.py                    (empty)
        │   └── Enum__Route53__Record_Type.py
        ├── primitives/
        │   ├── __init__.py                    (empty)
        │   ├── Safe_Str__Hosted_Zone_Id.py
        │   ├── Safe_Str__Domain_Name.py
        │   ├── Safe_Str__Record_Name.py
        │   ├── Safe_Str__Record_Value.py
        │   └── Safe_Int__TTL.py
        └── collections/
            ├── __init__.py                    (empty)
            ├── List__Schema__Route53__Hosted_Zone.py
            └── List__Schema__Route53__Record.py
```

### Class relationships (text diagram)

```
                          ┌────────────────────────────┐
                          │   Cli__Aws_Dns.py          │
                          │   ─ Typer app (sub-app)     │
                          │   ─ zones / records groups  │
                          │   ─ rich + JSON renderers   │
                          └────────────┬───────────────┘
                                       │  delegates to
                                       ▼
                          ┌────────────────────────────┐
                          │   Route53__AWS__Client      │
                          │   ─ sole boto3 boundary     │
                          │   ─ Type_Safe Methods       │
                          │   ─ in-memory subclass for  │
                          │     tests                   │
                          └────────────┬───────────────┘
                                       │
                                       ▼
                          ┌────────────────────────────┐
                          │   boto3 route53 client      │  ← documented exception
                          │   (region forwarded)        │
                          └────────────────────────────┘

  Returns/consumes pure Type_Safe schemas:
    Schema__Route53__Hosted_Zone
    Schema__Route53__Record (+ optional Schema__Route53__Record__Alias)
    Schema__Route53__Change__Result
    List__Schema__Route53__{Hosted_Zone,Record}
```

The CLI **never** touches boto3 directly. Only `Route53__AWS__Client` does.
Tests substitute an in-memory subclass (`Route53__AWS__Client__In_Memory`)
following the exact `Elastic__AWS__Client__In_Memory` precedent — no `mock`,
no `patch`.

### `Route53__AWS__Client` method surface

| Method | boto3 call | Notes |
|--------|------------|-------|
| `list_hosted_zones() -> List__Schema__Route53__Hosted_Zone` | `list_hosted_zones` (paginated) | Includes record-count per zone via separate `get_hosted_zone` for each (Q-followup: batch or cache?) |
| `find_hosted_zone_by_name(name: Safe_Str__Domain_Name) -> Schema__Route53__Hosted_Zone` | `list_hosted_zones_by_name` | Returns first exact match; raises if none |
| `get_hosted_zone(zone_id: Safe_Str__Hosted_Zone_Id) -> Schema__Route53__Hosted_Zone` | `get_hosted_zone` | Includes nameservers, delegation set |
| `list_records(zone_id: Safe_Str__Hosted_Zone_Id) -> List__Schema__Route53__Record` | `list_resource_record_sets` (paginated) | Includes alias records — alias payload populated when `AliasTarget` present |
| `get_record(zone_id, name, record_type) -> Optional[Schema__Route53__Record]` | filtered `list_resource_record_sets` with `StartRecordName=name&StartRecordType=type&MaxItems=1` | Returns None if not found |
| `create_record(zone_id, record: Schema__Route53__Record) -> Schema__Route53__Change__Result` | `change_resource_record_sets` with `Action=CREATE` | Errors if record exists |
| `upsert_record(zone_id, record: Schema__Route53__Record) -> Schema__Route53__Change__Result` | `change_resource_record_sets` with `Action=UPSERT` | Used by `update` |
| `delete_record(zone_id, name, record_type) -> Schema__Route53__Change__Result` | reads current via `get_record`, then `change_resource_record_sets` with `Action=DELETE` | DELETE requires the full current RR set |
| `upsert_a_alias_record(zone_id, name, alias_target: Schema__Route53__Record__Alias)` | `change_resource_record_sets` with `Action=UPSERT` + `AliasTarget` block | P2 — consumed by CF+R53 brief |

All methods are decorated `@type_safe` (osbot-utils) and accept/return
Type_Safe-validated values.

---

## 6. Component breakdown

### New files (proposed)

**`sgraph_ai_service_playwright__cli/aws/dns/service/`**

| File | One-line purpose |
|------|-------------------|
| `Route53__AWS__Client.py` | Sole boto3 boundary for Route 53. Methods listed in §5. Header documents the narrow-exception rationale (same template as `Elastic__AWS__Client`). |

**`sgraph_ai_service_playwright__cli/aws/dns/schemas/`** (one class per file — rule #21)

| File | One-line purpose |
|------|-------------------|
| `Schema__Route53__Hosted_Zone.py`     | Pure data: `zone_id`, `name`, `private`, `record_count`, `comment`, `name_servers` (List). |
| `Schema__Route53__Record.py`           | Pure data: `name`, `type` (Enum), `ttl`, `values` (List), `set_identifier`, `alias` (Optional Schema__Route53__Record__Alias). |
| `Schema__Route53__Record__Alias.py`    | Pure data: `hosted_zone_id`, `dns_name`, `evaluate_target_health`. Marked P2 — file ships in P1 as empty-shape placeholder to make the import in `Schema__Route53__Record.py` stable. |
| `Schema__Route53__Change__Result.py`    | Pure data: `change_id`, `status`, `submitted_at` (Safe_Str__ISO datetime). |
| `Schema__Route53__Zone__List.py`        | Pure data: `account_id`, `zones` (List__Schema__Route53__Hosted_Zone). |

**`sgraph_ai_service_playwright__cli/aws/dns/enums/`**

| File | One-line purpose |
|------|-------------------|
| `Enum__Route53__Record_Type.py` | `A`, `AAAA`, `CNAME`, `MX`, `TXT`, `NS`, `SOA`, `PTR`, `SRV`, `CAA`, `ALIAS_A`, `ALIAS_AAAA` (the alias-* members deferred to P2; the underlying enum values match Route 53's `Type` string). |

**`sgraph_ai_service_playwright__cli/aws/dns/primitives/`** (one class per file)

| File | One-line purpose |
|------|-------------------|
| `Safe_Str__Hosted_Zone_Id.py`  | `Z` + 1..32 alphanumerics (Route 53 allocates uppercase alphanumeric). Regex-validated. |
| `Safe_Str__Domain_Name.py`     | RFC-1035-ish: lowercase, dots, hyphens; trailing dot tolerated and normalised. Max length 255. |
| `Safe_Str__Record_Name.py`     | Same shape as `Safe_Str__Domain_Name`; semantically the record's own FQDN. |
| `Safe_Str__Record_Value.py`    | String, max length 4000 (TXT records hard cap); CLI splits on quotes for TXT. |
| `Safe_Int__TTL.py`             | Range 0..2147483647 (Route 53 hard limit); validated 1..86400 in practice. |

**`sgraph_ai_service_playwright__cli/aws/dns/collections/`** (rule #21 — pure type defs, no methods)

| File | One-line purpose |
|------|-------------------|
| `List__Schema__Route53__Hosted_Zone.py` | `Type_Safe__List[Schema__Route53__Hosted_Zone]` |
| `List__Schema__Route53__Record.py`       | `Type_Safe__List[Schema__Route53__Record]` |

**`sgraph_ai_service_playwright__cli/aws/cli/`**

| File | One-line purpose |
|------|-------------------|
| `Cli__Aws_Dns.py` | Typer `app` with sub-groups `zones` and `records`. Imports `Route53__AWS__Client`. Renderers (`_render_zones_list`, `_render_records_list`, `_render_change_result`) using rich.Table + Console — mirrors `Cli__Vault_App.py`'s `_render_vault_app_info` / `_render_vault_app_create` style. `--json` flag swaps the renderer for `console.print_json(data=schema.json())`. |

**`sgraph_ai_service_playwright__cli/aws/tests/`**

| File | One-line purpose |
|------|-------------------|
| `service/test_Route53__AWS__Client.py` | Composition tests against an in-memory subclass — assert method signatures, schema shapes, change-set construction. No boto3 hit. |
| `cli/test_Cli__Aws_Dns.py`              | CliRunner-based tests of the Typer surface — help text, subcommand existence, renderer output, `--json` shape. Mirrors `test_Cli__Vault_App.py`. |

### Existing files — changes

| File | Change |
|------|--------|
| Top-level CLI entry-point (wherever the `sg` Typer root lives) | Add `sg_app.add_typer(aws_app, name='aws')`. **Open: locate this in implementation phase** — the search above turned up no `sg aws` registration today, so this is a new top-level group. |
| `sgraph_ai_service_playwright__cli/aws/__init__.py` | Stays empty (rule #22). |

### Files that **must not** change

- Anything under `sgraph_ai_service_playwright/` (the Playwright service)
- `Step__Executor`, `JS__Expression__Allowlist`, `Artefact__Writer`
- Any existing `sg_compute_specs/*` spec
- `sgraph_ai_service_playwright__cli/aws/Stack__Naming.py`

---

## 7. AWS resources & IAM

### boto3 operations called by `Route53__AWS__Client`

| Method | boto3 client call | Read/Write |
|--------|-------------------|------------|
| `list_hosted_zones` | `route53:ListHostedZones` | R |
| `find_hosted_zone_by_name` | `route53:ListHostedZonesByName` | R |
| `get_hosted_zone` | `route53:GetHostedZone` | R |
| `list_records` | `route53:ListResourceRecordSets` | R |
| `get_record` | `route53:ListResourceRecordSets` (filtered) | R |
| `create_record` | `route53:ChangeResourceRecordSets` | W |
| `upsert_record` | `route53:ChangeResourceRecordSets` | W |
| `delete_record` | `route53:ChangeResourceRecordSets` + `route53:ListResourceRecordSets` | W + R |
| `get_change` (P2 polling) | `route53:GetChange` | R |

STS for account-id resolution (used by the table header): `sts:GetCallerIdentity`.

### Minimum IAM permissions

**Read-only (P0):**
- `route53:ListHostedZones`
- `route53:ListHostedZonesByName`
- `route53:GetHostedZone`
- `route53:ListResourceRecordSets`
- `sts:GetCallerIdentity`

**Read + write (P1):**
- All of the above, plus:
- `route53:ChangeResourceRecordSets` — **scope to specific hosted zone ARN(s)** in the IAM policy resource block to limit blast radius (e.g. `arn:aws:route53:::hostedzone/Z09876543...`)
- `route53:GetChange` — for the eventual `wait` / polling support (P2)

**P2 additions (if Q3-C accepted):**
- `route53:CreateHostedZone`

**No `ec2:*` / `iam:*` / `cloudfront:*` / `acm:*` permissions required.**
DNS-only.

### AWS resource naming

This brief introduces **no** persistent AWS resources of its own. Records and
zones it touches are operator-supplied. No tagging / naming convention applies
from this brief; if the operator wants to tag zones they manage with us, they
do so out of band (Route 53 supports `route53:ChangeTagsForResource` — not in
scope for P0/P1).

---

## 8. Phased rollout

### P0 — Read-only DNS center

**Scope:** zones + records list/show, no mutations.

1. `Route53__AWS__Client` ships with **read methods only**:
   `list_hosted_zones`, `find_hosted_zone_by_name`, `get_hosted_zone`,
   `list_records`, `get_record`.
2. All schemas, enums, primitives, collections shipped.
3. CLI subcommands shipped: `zones list`, `zones show`, `records list`,
   `records get`.
4. `--json` works on all four.
5. In-memory subclass + tests shipped.
6. Reality doc entry filed under
   `team/roles/librarian/reality/{aws-dns,cli}/index.md` (new domain or
   under `cli/`) marking the read-only surface EXISTS.

**Acceptance:**
- `sg aws dns zones list` lists every zone in the dev account.
- `sg aws dns records list vault.sgraph.ai` returns the actual records.
- `sg aws dns records get vault.sgraph.ai quiet-fermi --type A` shows the IP.
- All commands work with `--json`.
- Read-only IAM role suffices (verified by deploying the new lambda execution
  role with only the P0 actions and running the suite).

### P1 — Record mutations (add / update / delete)

**Scope:** make the CLI an editing surface.

1. `Route53__AWS__Client` gains `create_record`, `upsert_record`, `delete_record`.
2. CLI subcommands shipped: `records add`, `records update`, `records delete`.
3. Confirmation prompts on `update` / `delete` (Q4-A).
4. `--yes` flag added.
5. `SG_AWS__DNS__ALLOW_MUTATIONS=1` env gate (Q4 safety net).
6. Diff preview in the confirmation prompt (show old → new).

**Acceptance:**
- `sg aws dns records add ...` creates a record; fails cleanly if it exists.
- `sg aws dns records update ...` upserts.
- `sg aws dns records delete ...` requires `--yes` + env gate or interactive
  confirmation; fails cleanly without.
- All mutations return a `Schema__Route53__Change__Result` printed by the
  renderer (change-id + status).
- An integration test against the real Route 53 dev zone is gated on
  `SG_AWS__DNS__INTEGRATION=1`.

### P2 — Alias records + (optionally) zones CRUD

**Scope:** advanced record types and (pending Q3 sign-off) zone creation.

1. `records alias <zone> <name> --target-type cloudfront|elb|s3 --target <id-or-domain>`
   with the per-service hosted-zone-id lookup table.
2. `Schema__Route53__Record__Alias` becomes a real schema (P1 ships it as a
   placeholder).
3. (Q3-C only) `zones create <name> [--comment ...] [--private-vpc-id ...]`
   plus `Schema__Route53__Hosted_Zone__Create__Request`.
4. `get_change` polling on the `--wait` flag for mutations.

**Acceptance:**
- The bigger CF+R53 brief's P1 stack-create can call
  `Route53__AWS__Client.upsert_a_alias_record(...)` directly and consume the
  result.
- Existing P1 record commands are untouched.

---

## 9. Risks & mitigations

| # | Risk | Mitigation |
|---|------|------------|
| R1 | Fat-fingered `records delete` on prod DNS — site goes dark | (a) Confirmation prompt with diff preview (Q4-A). (b) `SG_AWS__DNS__ALLOW_MUTATIONS=1` env gate. (c) `--yes` is documented as "I have verified the diff". (d) IAM policy in production scoped to specific hosted-zone ARNs only. |
| R2 | `records update` on the wrong record (typo in name resolves to a different existing record) | Confirmation prompt shows the **resolved** FQDN and the current values being replaced. Operator can abort. |
| R3 | Zone-name resolution silently picks the wrong zone in multi-zone accounts (`example.com` vs `example.com.eu`) | `find_hosted_zone_by_name` requires an **exact** name match. If `list_hosted_zones_by_name` returns >1 candidate, raise with the list. Never auto-pick. |
| R4 | TTL set too low (1s) on a high-traffic record — DNS load explodes | `Safe_Int__TTL` validates 1..86400; CLI default 300s; **warn** if TTL < 60s and require `--yes` to proceed. |
| R5 | TXT record with embedded quotes broken by shell quoting | CLI's `--value` flag accepts the raw string; `Route53__AWS__Client` quotes it for the API. Document with examples in the help text. |
| R6 | Cross-account confusion — operator runs `sg aws dns records delete` thinking they're in dev, actually in prod | Default table-header line shows the resolved AWS account-id (from `sts:GetCallerIdentity`) and the profile. Mutations include account-id in the confirmation prompt. |
| R7 | boto3 pagination missed on `list_resource_record_sets` — partial record listings hide records from `records list`, then `add` later fails on duplicate | All `list_*` methods use the boto3 paginator (`get_paginator(...).paginate()`), never raw `list_*` calls. Unit-tested with multi-page in-memory fixture. |
| R8 | `delete_record` requires the full current RR-set body — race condition between read and write means a concurrent mutator's value is silently deleted | Document the race. P2 can add `IfMatch`-style ETag if Route 53 ever supports it (today it doesn't); P1 mitigation is the confirmation prompt + short window. |
| R9 | The `sg aws` Typer group does not exist today; first attempt to wire it could clash with an existing top-level command | Audit the top-level `sg` registration before adding the group. (Pre-Dev task: locate the `sg` Typer root.) |
| R10 | `osbot-aws` later adds Route 53 helpers; our direct-boto3 boundary becomes inconsistent | Document the upgrade path in `Route53__AWS__Client.py`'s header (mirrors the `Elastic__AWS__Client` template). File the upstream-osbot-aws follow-up brief once this lands. |

---

## 10. Test plan sketch

The repo's pytest convention: **no mocks, no patches** (CLAUDE.md, testing
guidance). Two test tracks:

### Track A — unit / in-memory (mandatory, runs in CI)

| Test file | What it asserts |
|-----------|------------------|
| `tests/service/test_Route53__AWS__Client.py` | Construction; method signatures match §5; an `Route53__AWS__Client__In_Memory` subclass (in `tests/service/_in_memory.py`) implements the boto3-layer methods against a dict-backed fixture, no `mock` module; each public method returns the documented schema shape; pagination across multiple pages works; `find_hosted_zone_by_name` raises on ambiguous match. |
| `tests/cli/test_Cli__Aws_Dns.py` | Mirrors `test_Cli__Vault_App.py`: `runner.invoke(app, ['--help'])`, `[zones, --help]`, `[records, --help]`, every subcommand has `--help`. Help text contains expected flags (`--json`, `--type`, `--ttl`, `--yes`). Renderer output (with no-color console) contains expected zone names and record types. `--json` output parses as valid JSON and round-trips through the schema. |
| `tests/schemas/test_Schema__Route53__Record.py` | Type_Safe construction; raw primitives rejected; enum-based `type` field rejects unknown values; round-trips via `.json()` and reconstruction. |
| `tests/primitives/test_Safe_Str__Hosted_Zone_Id.py` | Accepts `Z01234567ABCDEFGHIJKL`; rejects `z012...` (lowercase), `Z01234`-too-short fails only if min-len enforced (decide and assert). |
| `tests/primitives/test_Safe_Int__TTL.py` | 1..86400 accepted; 0 rejected (or accepted, depending on Q-followup); negative rejected. |

### Track B — integration / real Route 53 (gated)

Gate on `SG_AWS__DNS__INTEGRATION=1` (a real AWS profile pointed at a test
hosted zone). Numbered tests, top-down (deploy-via-pytest style):

```
test_1__list_hosted_zones__returns_at_least_one_zone
test_2__find_hosted_zone_by_name__resolves_test_zone
test_3__list_records__returns_default_NS_and_SOA
test_4__create_record__a_record_in_test_zone
test_5__get_record__finds_the_created_record
test_6__upsert_record__changes_the_a_record_value
test_7__delete_record__removes_the_record
test_8__list_records__no_longer_contains_the_record
```

Each test is independent of the *Track A* run; carries state via a tmp-path
fixture (e.g. the test record name is a uuid-derived FQDN so re-runs don't
collide).

### Is an in-memory fake feasible?

**Yes for Track A.** Route 53's API surface is small (∼6 methods used here) and
its data model is a flat list of resource record sets per zone. An
`Route53__AWS__Client__In_Memory` subclass that maintains `{zone_id:
{(name, type): record}}` covers every test we care about — no boto3 hit,
deterministic, fast.

**No for Track B.** Pagination quirks, change-status polling timing, name
servers, and IAM permission edges only show up against the real API. Gate on
the env var; skip cleanly in normal CI.

### Not unit-testable

- Real Route 53 change-status propagation (`PENDING` → `INSYNC`) — Track B only.
- IAM-permission-denied error shapes — manual / Track B with a restricted
  policy.
- Multi-account / multi-profile resolution — manual verification.

---

## 11. Next actions (decisions the user must make before Dev starts)

In order of blockingness:

1. **Q1** — confirm **Option B** (`sgraph_ai_service_playwright__cli/aws/dns/`
   layout) is the right home, or argue for the spec-style `sg_compute_specs/aws_dns/`.
2. **Q3** — pick A / B / C on hosted-zone CRUD. The Architect recommends **C**
   (`zones create` only, no `zones delete`), but the answer drives whether P2
   scope grows by one or zero commands.
3. **Q4 safety net** — confirm the `SG_AWS__DNS__ALLOW_MUTATIONS=1` env gate
   on top of confirmation prompts and `--yes`. This is the headline foot-gun
   mitigation — explicitly accept or reject.
4. **Scope** — confirm the P0 read-only slice is what Dev picks up first
   (smallest, lowest-risk, unblocks the bigger CF+R53 plan's read paths
   immediately). P1 (mutations) follows once the read surface is bedded in.
5. **`sg aws` Typer root location** — pre-Dev task: identify where the
   top-level `sg` Typer is registered (the audit above found `sg vault-app` /
   `sg el` / `sg os` registrations live elsewhere but the `sg aws` group is
   new). Confirm wiring before P0 ships.

When these are answered, the Dev contract is:

- The files in §6 are the slice.
- §5's method table is the boundary.
- §10 Track A is the test bar.
- The reality doc must be updated when the slice lands, registering
  `sg aws dns` zones/records as EXISTS and removing the PROPOSED label at the
  top of this brief.
- The bigger CF+R53 brief (`05/15/03/architect__vault-app__cf-route53__plan.md`)
  can be updated to **consume** `Route53__AWS__Client` rather than define its
  own — one Architect follow-up review entry.

---

*Filed by Architect (Claude), 2026-05-15. No code changed by this document — it
is a plan and a set of decisions for human ratification before Dev picks it up.
This brief is the simpler standalone subset of
`05/15/03/architect__vault-app__cf-route53__plan.md`; the bigger plan will
consume the `Route53__AWS__Client` primitive this brief defines, instead of
introducing its own.*
