---
title: "Architect Briefing — sg aws dns: Route 53 DNS Management Center"
file: architect__sg-aws-dns__plan.md
author: Architect (Claude)
date: 2026-05-15 (UTC hour 08)
repo: SGraph-AI__Service__Playwright @ dev (v0.1.140 line)
status: PLAN — no code, no commits. For human ratification before Dev picks up.
parent: team/humans/dinis_cruz/claude-code-web/05/15/03/architect__vault-app__cf-route53__plan.md
revision: "rev 2 (2026-05-15 hour 09) — user feedback folded in: default zone sgraph.ai, propagation checker, ACM list, Q2/Q3/Q4/Q5/Q6 resolved; Q1 re-investigated (B vs C)."
---

# Architect Briefing — sg aws dns: Route 53 DNS Management Center

> **PROPOSED — does not exist yet.** Nothing in this brief is implemented today.
> Verified: there is no `route53` / `Hosted_Zone` / `Route53__Client` reference
> anywhere under `sg_compute_specs/`, `sg_compute/`, or
> `sgraph_ai_service_playwright__cli/`. The `sgraph_ai_service_playwright__cli/aws/`
> directory exists but contains only `Stack__Naming.py` — a shared helper, not
> a CLI Typer surface. There is no `sg aws` command group registered anywhere
> today (the top-level `sg` Typer root is at `scripts/provision_ec2.py:769` —
> verified). There is no `sg_compute_specs/platform/` tier today either, and
> no `sg_image_builder/` package anywhere in the repo (verified).

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
update / delete records on any zone, **verify propagation across public
resolvers**, and **list ACM certificates** — independent of whether a stack-creation
flow is in play. The same `Route53__Client` primitive that this brief
introduces is then *consumed* by the larger CF+R53 plan: the bigger plan stops
having to define one and instead orchestrates this one. Concretely:

- **This brief delivers:** `Route53__AWS__Client`, `Route53__Propagation__Checker`,
  `ACM__AWS__Client`, the DNS / ACM schemas, the `sg aws dns` + `sg aws acm`
  Typer surfaces, and the test scaffolding (in-memory + integration).
- **The CF+R53 brief later consumes:** `Route53__AWS__Client.upsert_a_alias_record(...)`,
  `Route53__AWS__Client.upsert_record(...)` (for the `_acme-challenge` TXT
  DNS-01 flow), `Route53__AWS__Client.delete_record_set(...)` during stack
  tear-down, and `ACM__AWS__Client.describe_certificate(...)` to look up the
  CloudFront cert it provisions.

That sequencing makes this brief the **pre-requisite** for the CF+R53 plan's
P1 slice, not a competitor. It is also useful in isolation: most operator pain
around DNS today is "list/edit records in the console and then refresh whatsmydns.net
in another tab" — a CLI that does both is faster and scriptable.

---

## 2. Goals & non-goals

### Goals

1. **List + show hosted zones** in the account, with id / name / public-or-private
   / record-count / comment.
2. **List + get + add + update + delete records** within any zone, addressable
   by zone name or zone id, defaulting to **`sgraph.ai`** when `--zone` is not
   passed (resolved once per process and cached).
3. **Verify DNS propagation** for any record across a curated set of public
   resolvers (the whatsmydns.net pattern) and against the operator's local
   resolver (via `dig`). Standalone `records check` command in P1; optional
   `--verify` chaining on `records add` / `records update` in P2.
4. **List + show ACM certificates** in the account, dual-region by default
   (current region + us-east-1, because CloudFront certs must live in us-east-1).
5. **Generic, not stack-coupled.** No EC2 / vault-app / stack-name machinery.
   The CLI is callable against any zone, including ones not created by this
   tooling.
6. **JSON output mode** alongside the rich-table default, so the surface is
   scriptable for the larger CF+R53 plan and for any pipeline.
7. **`osbot-aws` discipline.** New `Route53__AWS__Client` and `ACM__AWS__Client`
   are the **sole** boto3 boundaries for their respective services in this
   repo. Documented narrow exception, same pattern as `Elastic__AWS__Client`.
8. **Type_Safe everywhere.** No raw `str` / `int` / `dict` on schemas; no
   Pydantic; no Literals.
9. **Safety net for destructive ops.** Confirmation prompts on `update` /
   `delete`, plus a `--yes` flag for scripted runs, plus a
   `SG_AWS__DNS__ALLOW_MUTATIONS=1` env gate (locked in — see Q4).

### Non-goals

- **No ACM cert issuance / deletion / re-issuance.** P0/P1 ACM commands are
  **read-only** (`list`, `show`). Issuance for CloudFront is covered by the
  CF+R53 brief.
- **No CloudFront distribution lifecycle.** Covered by the CF+R53 brief.
- **No DNS-01 ACME challenge wiring.** The TXT-record CRUD primitives are
  exposed but the actual ACME flow stays in `Cert__ACME__Client`'s lineage
  (CF+R53 brief P1).
- **No hosted-zone CRUD — ever.** (Q3 resolved → A.) List/show zones only.
  Operator creates / deletes zones via the AWS console; the CLI never offers
  `zones create` or `zones delete`.
- **No alias-record convenience command.** (Q5 resolved → A.) `records alias`
  is deferred and **not planned** unless explicitly re-requested. The CF+R53
  brief can stand alias records up directly via `Route53__AWS__Client`'s
  low-level `upsert_a_alias_record(...)` helper at the point of need.
- **No IAM policy authorship.** Section 7 lists required actions; drafting the
  JSON policy is a follow-up DevOps task.
- **No record-set health checks, no traffic policies, no DNSSEC, no resolver
  rules.** Out of scope. File a follow-up brief if needed.
- **No multi-account / cross-account zones.** Same-account only; profile /
  region picked up from the standard `AWS_*` env or `--profile`.

---

## 3. CLI surface

Top-level: `sg aws` — a new Typer sub-app registered under the existing top-level
`sg` Typer root at `scripts/provision_ec2.py:769` (confirmed). The first two
members of `sg aws` are `dns` and `acm`. Future siblings (`sg aws ec2`,
`sg aws iam`, ...) drop in next to them.

### Command tree

```
sg aws                                            # group help
sg aws dns                                        # group help
sg aws dns zones list                             # list all hosted zones in the account
sg aws dns zones show [<zone>]                    # details of one zone (defaults to sgraph.ai)
sg aws dns records list [<zone>]                  # list records in a zone (defaults to sgraph.ai)
sg aws dns records get <name> [--zone <z>]        # show one record (defaults to A; zone defaults to sgraph.ai)
sg aws dns records add <name> [--zone <z>]        # create a record
sg aws dns records update <name> [--zone <z>]     # upsert / change values
sg aws dns records delete <name> [--zone <z>]     # delete (with confirm + env gate)
sg aws dns records check <name> [--zone <z>]      # verify propagation across public resolvers + local dig
sg aws acm                                        # group help
sg aws acm list                                   # list ACM certs (current region + us-east-1 by default)
sg aws acm show <arn|domain>                      # details of one cert
```

(`records alias` deliberately omitted — see Q5.)

### Default zone — `sgraph.ai`

`--zone <name|id>` is **optional** on every `dns records *` and
`dns zones show` command. When unset, the CLI resolves the `sgraph.ai` hosted
zone id once per process via `ListHostedZonesByName` and caches it for the
lifetime of the command run. If `sgraph.ai` is not a zone in the resolved
account, the CLI exits with a clear error (`"--zone unset and no 'sgraph.ai'
hosted zone found in account 123456789012"`).

Zone arguments accept **either**:
- a **zone id** (`Z01234567ABCDEFGHIJKL`) — passed through verbatim, or
- a **zone name** (`example.com` or `example.com.`) — resolved via
  `ListHostedZonesByName` before any other call.

A `--json` flag on every subcommand swaps the rich-table renderer for a stable
JSON dump of the response schema.

### Flag matrix

| Command | Flags |
|---------|-------|
| `dns zones list`   | `--json` `--region` (R53 is global but `--region` is forwarded to the boto3 client for endpoint selection only) `--profile` |
| `dns zones show`   | `--zone <name\|id>` (optional, defaults sgraph.ai) `--json` |
| `dns records list` | `--zone <name\|id>` (optional, defaults sgraph.ai) `--json` `--type A` (filter) `--name <substring>` (filter) `--limit 100` |
| `dns records get`  | `--zone <name\|id>` (optional, defaults sgraph.ai) `--json` `--type A` (defaults to `A`) |
| `dns records add`  | `--zone <name\|id>` (optional, defaults sgraph.ai) `--type A` (required) `--value <ip\|val>` (required, repeatable for multi-value) `--ttl 300` (default) `--comment "..."` `--yes` (skip "create?" confirm) `--json` |
| `dns records update` | `--zone <name\|id>` (optional, defaults sgraph.ai) `--type A` (required) `--value <ip\|val>` (required, repeatable) `--ttl <int>` `--comment "..."` `--yes` (skip "change?" confirm) `--json` |
| `dns records delete` | `--zone <name\|id>` (optional, defaults sgraph.ai) `--type A` (required) `--yes` (skip "delete?" confirm) `--json` |
| `dns records check`  | `--zone <name\|id>` (optional, defaults sgraph.ai) `--type A` (default) `--expect <value>` (the value the operator expects to see — required for ✓/✗ marking) `--min-resolvers 5` (default quorum) `--flush-local` (run OS cache flush before local dig; sudo on macOS) `--json` |
| `acm list`           | `--region <name>` (override; defaults: current + us-east-1) `--all-regions` (loop with rate limiting) `--json` |
| `acm show`           | `--region <name>` (defaults: us-east-1 if `<arn>` is a us-east-1 ARN, else current; or auto-resolve from ARN region segment) `--json` |

### Example invocations + output

**`sg aws dns zones list`** (default table mode):

```
  Hosted zones in account 123456789012  ·  3 zones

  Zone Id                       Name                       Type     Records  Comment
  ────────────────────────────  ─────────────────────────  ───────  ───────  ────────────────────────
  Z01234567ABCDEFGHIJKL         sgraph.ai.                 public        28  Default (sgraph.ai)
  Z09876543ZYXWVUTSRQPO         vault.sgraph.ai.           public         4  Vault stacks (provisioned)
  Z11122233LMNOPQRSTUVW         internal.example.          private        7  VPC-attached
```

**`sg aws dns records list`** (no `--zone` → defaults to `sgraph.ai`):

```
  Records in zone sgraph.ai.  ·  Z01234567ABCDEFGHIJKL  ·  28 records  ·  (default zone)

  Name                                 Type   TTL     Value / Alias Target
  ───────────────────────────────────  ─────  ──────  ────────────────────────────────────────
  sgraph.ai.                           NS     172800  ns-1.awsdns-1.com. ns-2.awsdns-2.net. …
  sgraph.ai.                           SOA    900     ns-1.awsdns-1.com. awsdns-hostmaster.…
  www.sgraph.ai.                       A      300     203.0.113.10
  vault.sgraph.ai.                     NS     86400   ns-9.awsdns-9.net. ns-10.awsdns-10.org. …
  …
```

**`sg aws dns records add zen-darwin --type A --value 203.0.113.5 --ttl 60 --zone vault.sgraph.ai`**:

```
  About to create record:
    zone   : vault.sgraph.ai.  (Z09876543ZYXWVUTSRQPO)
    name   : zen-darwin.vault.sgraph.ai.
    type   : A
    ttl    : 60
    value  : 203.0.113.5
  Continue? [y/N]: y

  ✓  Record created  ·  change-id C0123456ABCDEF  ·  status PENDING
  Use `sg aws dns records check zen-darwin --zone vault.sgraph.ai --expect 203.0.113.5` once propagated.
```

**`sg aws dns records check zen-darwin --zone vault.sgraph.ai --expect 203.0.113.5`**:

```
  Resolving zen-darwin.vault.sgraph.ai.  type A  expect 203.0.113.5

  Public resolvers (8)
  Resolver                          IP                Geo    Answer            Match
  ────────────────────────────────  ────────────────  ─────  ────────────────  ─────
  Google                            8.8.8.8           US     203.0.113.5       ✓
  Google                            8.8.4.4           US     203.0.113.5       ✓
  Cloudflare                        1.1.1.1           Any    203.0.113.5       ✓
  Cloudflare                        1.0.0.1           Any    203.0.113.5       ✓
  Quad9                             9.9.9.9           CH     203.0.113.5       ✓
  OpenDNS                           208.67.222.222    US     —                 ✗  (NXDOMAIN — not converged)
  Yandex                            77.88.8.8         RU     203.0.113.5       ✓
  AdGuard                           94.140.14.14      CY     203.0.113.5       ✓

  Quorum: 7 / 8 match expected (min required: 5)   ✓  PASS

  Local resolver (dig +short @127.0.0.53)
  Answer: 203.0.113.5                              ✓  matches expected

  Exit code: 0
```

**`sg aws acm list`** (default — current region + us-east-1):

```
  ACM certificates  ·  account 123456789012  ·  regions: eu-west-1, us-east-1  ·  5 certs

  ARN (short)              Region      Domain                  SANs  Status   Type           In-use  Renew
  ───────────────────────  ──────────  ──────────────────────  ────  ───────  ─────────────  ──────  ─────
  acm:eu-west-1:…/a1b2     eu-west-1   api.example.com            2  ISSUED   AMAZON_ISSUED       1  ELIGIBLE
  acm:eu-west-1:…/c3d4     eu-west-1   *.internal.example.       12  ISSUED   AMAZON_ISSUED       3  ELIGIBLE
  acm:us-east-1:…/e5f6     us-east-1   *.sgraph.ai                1  ISSUED   AMAZON_ISSUED       1  ELIGIBLE   ← CF cert
  acm:us-east-1:…/g7h8     us-east-1   legacy.example.com         0  EXPIRED  IMPORTED            0  INELIGIBLE
  acm:us-east-1:…/i9j0     us-east-1   pending.example.com        0  PENDING  AMAZON_ISSUED       0  —

  Note: CloudFront certificates MUST live in us-east-1. The `*.sgraph.ai`
  cert above is the one consumed by `vault.sgraph.ai` CloudFront distributions.
```

**`sg aws dns records list --json`**:

```json
{
  "zone_id": "Z01234567ABCDEFGHIJKL",
  "zone_name": "sgraph.ai.",
  "zone_is_default": true,
  "records": [
    {
      "name": "sgraph.ai.",
      "type": "NS",
      "ttl": 172800,
      "values": ["ns-1.awsdns-1.com.", "ns-2.awsdns-2.net."],
      "alias": null,
      "set_identifier": ""
    },
    {
      "name": "www.sgraph.ai.",
      "type": "A",
      "ttl": 300,
      "values": ["203.0.113.10"],
      "alias": null,
      "set_identifier": ""
    }
  ]
}
```

---

## 4. Open questions — for human ratification before Dev starts

Style mirrors the Q-with-A/B/C-options convention used in the CF+R53 brief.
Resolved questions are marked **[RESOLVED — user choice: X]** with the
one-line rationale.

### Q1 — Where does the code live? Three options now on the table.

| Opt | Position |
|-----|----------|
| **A** | Spec-style: `sg_compute_specs/aws_dns/` mirroring `vault_app/` — `cli/ service/ schemas/ enums/ primitives/ tests/`. Treat it as a full spec. |
| **B** | CLI-side: `sgraph_ai_service_playwright__cli/aws/dns/` (+ `…/aws/acm/`) next to the existing `Stack__Naming.py`, with sibling `cli/ service/ schemas/ enums/ primitives/ tests/` folders rooted there. |
| **C** | New `sg_compute_specs/platform/aws/dns/` (+ `…/aws/acm/`) tier — introduces a "platform layer" inside `sg_compute_specs/` for cross-spec shared infrastructure (Route 53, ACM, future CloudFront / IAM). Future-proofs for a forthcoming `sg_image_builder/providers/aws/*`. |

**Re-investigation (Architect, rev 2).**

The user has flagged a misconception worth correcting up front:

> **`sgraph_ai_service_playwright__cli/` is NOT legacy.** Confirmed against
> reality doc `team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md`
> — 449 files, actively expanded; it is the canonical home for the operator
> CLI surface (Typer commands, AWS surface helpers like `Stack__Naming.py`,
> per-spec CLI modules). Calling it legacy would be wrong.

That removes one argument against Option B. The real question is whether to:

- (B) **stay with the existing CLI-side namespace** — `sgraph_ai_service_playwright__cli/aws/`
  already exists, already houses shared AWS surface code (`Stack__Naming.py`),
  and would naturally absorb `dns/`, `acm/`, future `ec2/`, `iam/`, etc.
- (C) **introduce a new `sg_compute_specs/platform/` tier** — a clean separation
  between *spec*-style ephemeral-stack code (under `sg_compute_specs/{vault_app,
  vnc, elastic, …}`) and *platform*-style account-level resource code (under
  `sg_compute_specs/platform/aws/{dns, acm, …}`). Mirrors a hypothetical
  forthcoming `sg_image_builder/providers/aws/*`.

**Arguments for C:**
- Creates a clear "platform layer" tier for cross-spec shared infrastructure
  (Route 53, ACM, future CloudFront / IAM) versus per-spec `vault_app/`,
  `vnc/`, etc.
- Future-proofs: when `sg_image_builder/` lands (the user hints it's coming),
  it would mirror this with `providers/aws/*`.
- Aligns conceptually with the spec convention (every other thing under
  `sg_compute_specs/` follows a structured `cli/ service/ schemas/ …` layout
  — `platform/aws/dns/` would inherit that).
- `sgraph_ai_service_playwright__cli/` arguably *should* shrink, not grow —
  there's an in-progress duality refactor (per reality doc) moving operator
  CLI surface out into spec-shaped modules.

**Arguments against C (and for B):**
- `sg_compute_specs/platform/` does **not** exist today (verified — only
  per-spec directories live there). Introducing a new top-level tier is heavier
  than reusing `sgraph_ai_service_playwright__cli/aws/` (which already exists
  with `Stack__Naming.py`).
- DNS / ACM / CloudFront are not lifecycle-tied to a *compute* spec — they're
  account-level resources. Putting them under `sg_compute_specs/` ties them
  conceptually to compute when they aren't.
- `Stack__Naming.py` would have to migrate too (or live duplicated in two
  places). That's churn against existing imports across the CLI.
- The "future `sg_image_builder/`" is hypothetical — none of it exists. Designing
  the tier *for* a non-existent consumer is speculative.
- The existing top-level `sg` Typer root at `scripts/provision_ec2.py:769`
  already imports from `sgraph_ai_service_playwright__cli/*/cli/*` for every
  current sub-app (`pw`, `elastic`, `vnc`, `firefox`, `vault-app`, …). Adding
  one more `aws/cli/Cli__Aws_Dns.py` import under that pattern is zero-friction.
  An import from `sg_compute_specs/platform/aws/cli/…` would be a brand-new
  pattern.

**Architect recommendation (rev 2): still B**, with a clarifying note that
`sgraph_ai_service_playwright__cli/aws/` is the **"shared AWS surface"
namespace** — distinct from per-spec `sgraph_ai_service_playwright__cli/{elastic,
vnc, vault, …}/aws/` helpers — and is the right home for account-level
resource clients like Route 53 and ACM. The "DNS does not belong under
*compute_specs*" point is the strongest argument: DNS is not compute, has no
stack lifecycle, and forcing it under `sg_compute_specs/` (even via a new
`platform/` sub-tier) muddles the namespace.

If the user pushes for C, the migration path is acceptable but non-trivial:
- Move `Stack__Naming.py` to `sg_compute_specs/platform/aws/naming/` (or leave
  it and accept the duality).
- Add `sg_compute_specs/platform/aws/dns/{service,schemas,enums,primitives,collections}/`.
- Add `sg_compute_specs/platform/aws/acm/{service,schemas,enums,collections}/`.
- Wire `Cli__Aws_Dns.py` and `Cli__Aws_Acm.py` under `sg_compute_specs/platform/aws/cli/`.
- Register from `scripts/provision_ec2.py` exactly as today, just from new paths.

**Decision still pending user sign-off.** If user picks C, §5 layout must be
redrawn (we sketch it below as an addendum in §5).

### Q2 — `add` semantics: strict create, or implicit upsert?

| Opt | Position |
|-----|----------|
| **A** | **`add` is strict CREATE.** Reject (`ResourceRecordSetAlreadyExists`-style error) if a record with the same name + type already exists. `update` is the only way to change an existing record. |
| **B** | **`add` is UPSERT.** If the record exists, replace it. One command for "make sure this record looks like X". |
| **C** | **`add` is strict CREATE by default; `--upsert` flag opts in.** Best of both, more flags. |

**[RESOLVED — user choice: A.]** `add` is strict CREATE; `update` is UPSERT.
Mirrors Route 53's three API verbs and standard RDBMS CLI expectations.

### Q3 — Hosted-zone CRUD: leave out, or add as P2?

| Opt | Position |
|-----|----------|
| **A** | **List/show only.** Zone create / delete stays an operator action (console or `awscli`). |
| ~~**B**~~ | ~~Add `zones create` and `zones delete` as P2.~~ |
| ~~**C**~~ | ~~Add `zones create` only, never `zones delete`.~~ |

**[RESOLVED — user choice: A.]** No zone CRUD ever. List/show only. P2 no
longer grows; the hosted-zone bootstrap step in the CF+R53 brief stays an
out-of-band operator action.

### Q4 — Confirmation prompts and destructive-op safety net.

| Opt | Position |
|-----|----------|
| **A** | Confirm on `update` and `delete` only; `add` runs silently. `--yes` skips the prompt. PLUS `SG_AWS__DNS__ALLOW_MUTATIONS=1` env gate on all destructive ops. |
| **B** | Confirm on every mutation; `--yes` skips. |
| **C** | Confirm on `delete` only; `--yes` skips. |

**[RESOLVED — user choice: A.]** Confirmation on `update` / `delete` with
diff preview, `--yes` flag, **and** `SG_AWS__DNS__ALLOW_MUTATIONS=1` env gate
locked in (see §9 R1).

### Q5 — Alias record support: P0/P1 or P2?

| Opt | Position |
|-----|----------|
| **A** | **No `records alias` CLI command.** Alias support exposed only via `Route53__AWS__Client.upsert_a_alias_record(...)` (consumed by CF+R53 brief at point of need). Deferred and **not planned** as a CLI surface unless explicitly re-requested. |
| ~~**B**~~ | ~~Include `records alias` in P1.~~ |
| ~~**C**~~ | ~~Skip the convenience CLI; expose via `records add --alias-target ...`.~~ |

**[RESOLVED — user choice: A.]** `records alias` removed from the command
tree. `Route53__AWS__Client.upsert_a_alias_record(...)` remains as a library
helper for the CF+R53 brief.

### Q6 — Region & profile handling.

| Opt | Position |
|-----|----------|
| **A** | Always use the default boto3 profile + env. No CLI flags. |
| **B** | `--profile` and `--region` flags on every command. R53 is global but `--region` is forwarded to the boto3 client (endpoint selection only). ACM is region-scoped; defaults to current + us-east-1 dual scan. |
| **C** | `--profile` only; no `--region` flag. |

**[RESOLVED — user choice: B.]** `--profile` + `--region` on every command.
ACM commands additionally default to **dual-region** (current + us-east-1)
because of CloudFront's us-east-1 hard requirement. See §7 "Region semantics"
for the full list of us-east-1-only / global resources relevant here.

### Q7 — New: dnspython dependency

The propagation checker (`records check`) wants `dnspython` for per-resolver
UDP/TCP queries. `dnspython` is **not** currently in `pyproject.toml` and is
not currently a transitive dep (verified via `grep`). Question: add `dnspython`
as a direct dep in `pyproject.toml`, or shell out to `dig` for every resolver
(losing per-resolver query control and parallelism)?

Architect recommendation: **add `dnspython` as a direct dep**. Mature, pure-Python,
small surface, makes the per-resolver + quorum logic clean. Falling back to
`dig` for the *local* check is fine (it's what the operator's machine actually
uses) but the multi-resolver matrix wants programmatic queries.

**[OPEN — user must decide before P1 ships.]**

### Q8 — New: `--verify` chaining on `records add` / `records update`

After P1 ships the standalone `records check` command, should `records add`
and `records update` accept a `--verify` flag that automatically chains
`records check` after the change has been submitted? The Architect leans
**P2** — keep P1 simple, get the `records check` UX bedded in, then add the
chaining once the operator confirms the check's defaults (quorum, resolver
set, exit codes) match what they want. Cheap to add later.

**[OPEN — confirm P2 placement.]**

---

## 5. Proposed architecture

### Module location: Option B (per Q1 recommendation — pending sign-off)

```
sgraph_ai_service_playwright__cli/
└── aws/                                       (existing — empty __init__.py + Stack__Naming.py)
    ├── __init__.py                            (empty)
    ├── Stack__Naming.py                       (existing, unchanged)
    │
    ├── cli/
    │   ├── __init__.py                        (empty)
    │   ├── Cli__Aws.py                        (NEW — Typer parent group `sg aws`)
    │   ├── Cli__Aws_Dns.py                    (NEW — `sg aws dns` sub-app)
    │   └── Cli__Aws_Acm.py                    (NEW — `sg aws acm` sub-app)
    │
    ├── dns/                                   (NEW)
    │   ├── __init__.py                        (empty)
    │   ├── service/
    │   │   ├── __init__.py                    (empty)
    │   │   ├── Route53__AWS__Client.py        (sole boto3 boundary — NEW)
    │   │   └── Route53__Propagation__Checker.py  (NEW — multi-resolver checker)
    │   ├── schemas/
    │   │   ├── __init__.py                    (empty)
    │   │   ├── Schema__Route53__Hosted_Zone.py
    │   │   ├── Schema__Route53__Record.py
    │   │   ├── Schema__Route53__Record__Alias.py   (lib-only — no CLI surface; consumed by CF+R53 brief)
    │   │   ├── Schema__Route53__Change__Result.py
    │   │   ├── Schema__Route53__Zone__List.py
    │   │   └── Schema__Dns__Check__Result.py        (NEW — propagation-check output)
    │   ├── enums/
    │   │   ├── __init__.py                    (empty)
    │   │   ├── Enum__Route53__Record_Type.py
    │   │   └── Enum__Dns__Resolver.py             (NEW — curated public-resolver set)
    │   ├── primitives/
    │   │   ├── __init__.py                    (empty)
    │   │   ├── Safe_Str__Hosted_Zone_Id.py
    │   │   ├── Safe_Str__Domain_Name.py
    │   │   ├── Safe_Str__Record_Name.py
    │   │   ├── Safe_Str__Record_Value.py
    │   │   ├── Safe_Str__Resolver_IP.py            (NEW — IPv4/IPv6 of a public resolver)
    │   │   └── Safe_Int__TTL.py
    │   └── collections/
    │       ├── __init__.py                    (empty)
    │       ├── List__Schema__Route53__Hosted_Zone.py
    │       ├── List__Schema__Route53__Record.py
    │       └── List__Schema__Dns__Check__Resolver_Result.py  (NEW — per-resolver rows)
    │
    ├── acm/                                   (NEW)
    │   ├── __init__.py                        (empty)
    │   ├── service/
    │   │   ├── __init__.py                    (empty)
    │   │   └── ACM__AWS__Client.py             (sole boto3 boundary for ACM — NEW)
    │   ├── schemas/
    │   │   ├── __init__.py                    (empty)
    │   │   ├── Schema__ACM__Certificate.py
    │   │   └── Schema__ACM__Certificate__List.py
    │   ├── enums/
    │   │   ├── __init__.py                    (empty)
    │   │   ├── Enum__ACM__Cert_Status.py            (NEW — PENDING_VALIDATION/ISSUED/EXPIRED/…)
    │   │   └── Enum__ACM__Cert_Type.py               (NEW — AMAZON_ISSUED/IMPORTED/PRIVATE)
    │   └── collections/
    │       ├── __init__.py                    (empty)
    │       └── List__Schema__ACM__Certificate.py
    │
    └── tests/
        ├── __init__.py
        ├── service/
        │   ├── test_Route53__AWS__Client.py
        │   ├── test_Route53__Propagation__Checker.py
        │   └── test_ACM__AWS__Client.py
        └── cli/
            ├── test_Cli__Aws_Dns.py
            └── test_Cli__Aws_Acm.py
```

### Class relationships (text diagram)

```
                          ┌────────────────────────────────────┐
                          │   Cli__Aws.py  (Typer parent)       │
                          │   ─ adds dns + acm sub-apps         │
                          └─────────┬──────────────┬───────────┘
                                    │              │
                ┌───────────────────┘              └────────────────────┐
                ▼                                                       ▼
   ┌────────────────────────────┐                       ┌──────────────────────────────┐
   │ Cli__Aws_Dns.py            │                       │ Cli__Aws_Acm.py              │
   │ ─ zones / records groups    │                       │ ─ list / show               │
   │ ─ rich + JSON renderers     │                       │ ─ dual-region default        │
   │ ─ sgraph.ai default lookup  │                       │                              │
   └───────┬────────────────────┘                       └──────┬───────────────────────┘
           │                                                   │
           ├──────────────────┐                                 │
           ▼                  ▼                                 ▼
  ┌────────────────────┐ ┌────────────────────────┐  ┌────────────────────────┐
  │ Route53__AWS__     │ │ Route53__Propagation__  │  │ ACM__AWS__Client       │
  │ Client             │ │ Checker                 │  │ ─ sole boto3 boundary  │
  │ ─ sole boto3       │ │ ─ uses dnspython        │  │ ─ list_certificates    │
  │   boundary R53     │ │ ─ uses subprocess(dig)  │  │ ─ describe_certificate │
  │ ─ default-zone     │ │ ─ quorum logic          │  │ ─ dual-region helper   │
  │   sgraph.ai cache  │ │                         │  │                        │
  └──────┬─────────────┘ └──────┬──────────────────┘  └──────┬─────────────────┘
         │                      │                            │
         ▼                      ▼                            ▼
  ┌────────────────────────────────────────────────────────────────────┐
  │ boto3 route53 / acm clients     +     dnspython     +     dig subprocess  │
  │  (documented narrow boto3 exception; dnspython is direct dep)       │
  └────────────────────────────────────────────────────────────────────┘
```

The CLI **never** touches boto3 directly. Only `Route53__AWS__Client` and
`ACM__AWS__Client` do. The propagation checker is allowed to call `dnspython`
and `subprocess` directly — it's the only DNS-on-the-wire / shell-out
boundary, and it's explicitly scoped to that role.

Tests substitute in-memory subclasses (`Route53__AWS__Client__In_Memory`,
`ACM__AWS__Client__In_Memory`, `Route53__Propagation__Checker__In_Memory`)
following the exact `Elastic__AWS__Client__In_Memory` precedent — no `mock`,
no `patch`.

### `Route53__AWS__Client` method surface

| Method | boto3 call | Notes |
|--------|------------|-------|
| `list_hosted_zones() -> List__Schema__Route53__Hosted_Zone` | `list_hosted_zones` (paginated) | Includes record-count per zone via separate `get_hosted_zone` for each (Q-followup: batch or cache?) |
| `find_hosted_zone_by_name(name)` | `list_hosted_zones_by_name` | Returns first exact match; raises if none |
| `resolve_default_zone() -> Schema__Route53__Hosted_Zone` | `list_hosted_zones_by_name` for `sgraph.ai` | Cached on first call; raises if absent |
| `get_hosted_zone(zone_id)` | `get_hosted_zone` | Includes nameservers, delegation set |
| `list_records(zone_id)` | `list_resource_record_sets` (paginated) | Includes alias records — alias payload populated when `AliasTarget` present |
| `get_record(zone_id, name, record_type)` | filtered `list_resource_record_sets` | Returns None if not found |
| `create_record(zone_id, record)` | `change_resource_record_sets` `Action=CREATE` | Errors if record exists |
| `upsert_record(zone_id, record)` | `change_resource_record_sets` `Action=UPSERT` | Used by `update` |
| `delete_record(zone_id, name, record_type)` | reads current via `get_record`, then `Action=DELETE` | DELETE requires the full current RR set |
| `upsert_a_alias_record(zone_id, name, alias_target)` | `Action=UPSERT` + `AliasTarget` block | Library-only helper — consumed by CF+R53 brief; no CLI command (Q5-A) |

### `Route53__Propagation__Checker` method surface

| Method | Implementation | Notes |
|--------|----------------|-------|
| `check_record(name, record_type, expected_value, min_resolvers=5, flush_local=False) -> Schema__Dns__Check__Result` | dnspython per-resolver query, parallel via `concurrent.futures.ThreadPoolExecutor`, ~3s per-resolver timeout | Quorum logic; returns per-resolver rows + summary |
| `check_local(name, record_type, expected_value, flush_local=False) -> Schema__Dns__Check__Result__Local` | `subprocess.run(['dig', '+short', '@<local>', name, type])` | Local resolver — OS-dependent cache flush if `flush_local=True` |
| `flush_local_cache() -> bool` | macOS: `dscacheutil -flushcache; sudo killall -HUP mDNSResponder`; Linux: `systemd-resolve --flush-caches` if available | Returns True if flush attempted; warns if neither path works |

### `ACM__AWS__Client` method surface

| Method | boto3 call | Notes |
|--------|------------|-------|
| `list_certificates(region) -> List__Schema__ACM__Certificate` | `acm:ListCertificates` (paginated) + `acm:DescribeCertificate` per ARN | Returns rich shape including SANs, status, in-use count |
| `list_certificates__dual_region() -> List__Schema__ACM__Certificate` | calls `list_certificates` for current region + us-east-1, dedupes if same | Default behaviour of `sg aws acm list` |
| `list_certificates__all_regions() -> List__Schema__ACM__Certificate` | loops all commercial regions with rate limiting | `--all-regions` flag |
| `describe_certificate(arn) -> Schema__ACM__Certificate` | `acm:DescribeCertificate` | Auto-detects region from ARN |

All methods are decorated `@type_safe` (osbot-utils) and accept/return
Type_Safe-validated values.

---

## 6. Component breakdown

### New files (proposed) — Route 53

**`sgraph_ai_service_playwright__cli/aws/dns/service/`**

| File | One-line purpose |
|------|-------------------|
| `Route53__AWS__Client.py` | Sole boto3 boundary for Route 53. Includes the `sgraph.ai` default-zone resolver with per-process cache. Header documents the narrow-exception rationale (same template as `Elastic__AWS__Client`). |
| `Route53__Propagation__Checker.py` | The whatsmydns.net-style multi-resolver checker. Uses `dnspython` for per-resolver UDP/TCP queries, `concurrent.futures` for parallelism, and `subprocess` for the local `dig` shell-out. Sole class allowed to call `dns.*` / `subprocess.*` for DNS-on-the-wire work. |

**`sgraph_ai_service_playwright__cli/aws/dns/schemas/`** (one class per file — rule #21)

| File | One-line purpose |
|------|-------------------|
| `Schema__Route53__Hosted_Zone.py` | `zone_id`, `name`, `private`, `record_count`, `comment`, `name_servers` (List). |
| `Schema__Route53__Record.py` | `name`, `type` (Enum), `ttl`, `values` (List), `set_identifier`, `alias` (Optional). |
| `Schema__Route53__Record__Alias.py` | `hosted_zone_id`, `dns_name`, `evaluate_target_health`. Library-only schema consumed by CF+R53 brief — no CLI command surfaces it. |
| `Schema__Route53__Change__Result.py` | `change_id`, `status`, `submitted_at` (Safe_Str__ISO datetime). |
| `Schema__Route53__Zone__List.py` | `account_id`, `zones` (List__Schema__Route53__Hosted_Zone). |
| `Schema__Dns__Check__Result.py` | `name`, `record_type`, `expected_value`, `resolvers` (List of per-resolver rows: resolver enum, IP, geo, answer, match-bool), `local_answer`, `local_match`, `quorum_required`, `quorum_met`, `exit_code`. |

**`sgraph_ai_service_playwright__cli/aws/dns/enums/`**

| File | One-line purpose |
|------|-------------------|
| `Enum__Route53__Record_Type.py` | `A`, `AAAA`, `CNAME`, `MX`, `TXT`, `NS`, `SOA`, `PTR`, `SRV`, `CAA` (alias-* members deferred — no CLI command; `Schema__Route53__Record__Alias` carries the alias data when needed). |
| `Enum__Dns__Resolver.py` | Curated public-resolver list. Each member: name + IP + geo. Members: `GOOGLE_PRIMARY` (8.8.8.8 US), `GOOGLE_SECONDARY` (8.8.4.4 US), `CLOUDFLARE_PRIMARY` (1.1.1.1 Any), `CLOUDFLARE_SECONDARY` (1.0.0.1 Any), `QUAD9` (9.9.9.9 CH), `OPENDNS` (208.67.222.222 US), `YANDEX` (77.88.8.8 RU), `ADGUARD` (94.140.14.14 CY). Default 8-resolver set; `--min-resolvers` defaults to 5. |

**`sgraph_ai_service_playwright__cli/aws/dns/primitives/`** (one class per file)

| File | One-line purpose |
|------|-------------------|
| `Safe_Str__Hosted_Zone_Id.py` | `Z` + 1..32 alphanumerics (Route 53 allocates uppercase alphanumeric). Regex-validated. |
| `Safe_Str__Domain_Name.py` | RFC-1035-ish: lowercase, dots, hyphens; trailing dot tolerated and normalised. Max length 255. |
| `Safe_Str__Record_Name.py` | Same shape as `Safe_Str__Domain_Name`; semantically the record's own FQDN. |
| `Safe_Str__Record_Value.py` | String, max length 4000 (TXT records hard cap); CLI splits on quotes for TXT. |
| `Safe_Str__Resolver_IP.py` | IPv4 dotted-quad or compressed IPv6, validated with `ipaddress` stdlib at construction time. Used by `Enum__Dns__Resolver` member payloads and as the `resolver_ip` field on per-resolver result rows. |
| `Safe_Int__TTL.py` | Range 0..2147483647 (Route 53 hard limit); validated 1..86400 in practice. |

**`sgraph_ai_service_playwright__cli/aws/dns/collections/`** (rule #21 — pure type defs, no methods)

| File | One-line purpose |
|------|-------------------|
| `List__Schema__Route53__Hosted_Zone.py` | `Type_Safe__List[Schema__Route53__Hosted_Zone]` |
| `List__Schema__Route53__Record.py` | `Type_Safe__List[Schema__Route53__Record]` |
| `List__Schema__Dns__Check__Resolver_Result.py` | `Type_Safe__List[Schema__Dns__Check__Resolver_Result]` (the inner per-resolver row schema; declared as its own class file alongside `Schema__Dns__Check__Result.py`). |

### New files (proposed) — ACM

**`sgraph_ai_service_playwright__cli/aws/acm/service/`**

| File | One-line purpose |
|------|-------------------|
| `ACM__AWS__Client.py` | Sole boto3 boundary for ACM. `list_certificates(region)`, `list_certificates__dual_region()`, `list_certificates__all_regions()`, `describe_certificate(arn)`. Header documents the narrow boto3 exception. |

**`sgraph_ai_service_playwright__cli/aws/acm/schemas/`**

| File | One-line purpose |
|------|-------------------|
| `Schema__ACM__Certificate.py` | `arn`, `region`, `domain_name`, `subject_alt_names` (List), `status` (Enum), `cert_type` (Enum), `in_use_by_count`, `renewal_eligibility`, `issued_at` (Optional Safe_Str__ISO), `not_after` (Optional Safe_Str__ISO). |
| `Schema__ACM__Certificate__List.py` | `account_id`, `regions_scanned` (List of region names), `certificates` (List__Schema__ACM__Certificate). |

**`sgraph_ai_service_playwright__cli/aws/acm/enums/`**

| File | One-line purpose |
|------|-------------------|
| `Enum__ACM__Cert_Status.py` | `PENDING_VALIDATION`, `ISSUED`, `INACTIVE`, `EXPIRED`, `VALIDATION_TIMED_OUT`, `REVOKED`, `FAILED`. Matches ACM's `Status` field exactly. |
| `Enum__ACM__Cert_Type.py` | `AMAZON_ISSUED`, `IMPORTED`, `PRIVATE`. Matches ACM's `Type` field. |

**`sgraph_ai_service_playwright__cli/aws/acm/collections/`**

| File | One-line purpose |
|------|-------------------|
| `List__Schema__ACM__Certificate.py` | `Type_Safe__List[Schema__ACM__Certificate]` |

### New files (proposed) — CLI

**`sgraph_ai_service_playwright__cli/aws/cli/`**

| File | One-line purpose |
|------|-------------------|
| `Cli__Aws.py` | Typer parent app for `sg aws`. Mounts `dns` and `acm` sub-apps. Imported from `scripts/provision_ec2.py` and wired via `app.add_typer(aws_app, name='aws')`. |
| `Cli__Aws_Dns.py` | Typer `dns` app with sub-groups `zones` and `records`. Imports `Route53__AWS__Client` and `Route53__Propagation__Checker`. Default-zone resolution lives here (calls `Route53__AWS__Client.resolve_default_zone()` when `--zone` unset). Renderers (`_render_zones_list`, `_render_records_list`, `_render_change_result`, `_render_check_result`) using `rich.Table` + Console — mirrors `Cli__Vault_App.py`'s `_render_vault_app_info` / `_render_vault_app_create` style. `--json` flag swaps the renderer for `console.print_json(data=schema.json())`. |
| `Cli__Aws_Acm.py` | Typer `acm` app with `list` and `show` subcommands. Imports `ACM__AWS__Client`. Dual-region default behaviour for `list`; ARN-derived region for `show`. Renderers (`_render_acm_list`, `_render_acm_show`) match the rich style. |

### New files (proposed) — tests

**`sgraph_ai_service_playwright__cli/aws/tests/`**

| File | One-line purpose |
|------|-------------------|
| `service/test_Route53__AWS__Client.py` | Composition tests against `Route53__AWS__Client__In_Memory` — method signatures, schema shapes, change-set construction, `resolve_default_zone()` caching, multi-page pagination. No boto3 hit. |
| `service/test_Route53__Propagation__Checker.py` | Tests against `Route53__Propagation__Checker__In_Memory` (in-memory fake resolver returning canned per-resolver answers). Assert: quorum-met when 5/8 match, quorum-failed when 4/8 match, exit-code = 0/1/2 mapping, `flush_local` is a no-op in the fake. |
| `service/test_ACM__AWS__Client.py` | Tests against `ACM__AWS__Client__In_Memory`. Dual-region scan dedupes when current = us-east-1, ARN-region auto-detection, `--all-regions` loop hits the expected region list. |
| `cli/test_Cli__Aws_Dns.py` | CliRunner-based tests of the Typer surface — help text, subcommand existence, renderer output, `--json` shape, default-zone behaviour when `--zone` omitted. |
| `cli/test_Cli__Aws_Acm.py` | CliRunner-based tests — `list`, `show`, `--json` round-trip, dual-region default in the rendered output. |

### Existing files — changes

| File | Change |
|------|--------|
| `scripts/provision_ec2.py` (the top-level `sg` Typer root, line 769) | Add a new sub-app: `from sgraph_ai_service_playwright__cli.aws.cli.Cli__Aws import app as _aws_app` followed by `app.add_typer(_aws_app, name='aws')`. **Confirmed location** — pre-Dev audit complete. |
| `pyproject.toml` | Add `dnspython = "^2.6"` (or current stable) under `[tool.poetry.dependencies]` — pending Q7 sign-off. |
| `sgraph_ai_service_playwright__cli/aws/__init__.py` | Stays empty (rule #22). |

### Files that **must not** change

- Anything under `sgraph_ai_service_playwright/` (the Playwright service)
- `Step__Executor`, `JS__Expression__Allowlist`, `Artefact__Writer`
- Any existing `sg_compute_specs/*` spec
- `sgraph_ai_service_playwright__cli/aws/Stack__Naming.py`

### §5 addendum — Option C layout (if user picks it)

If Q1 resolves to C instead of B, swap §5 / §6 paths from
`sgraph_ai_service_playwright__cli/aws/{dns,acm,cli}/…` to:

```
sg_compute_specs/
└── platform/                                  (NEW tier)
    ├── __init__.py                            (empty)
    └── aws/
        ├── __init__.py                        (empty)
        ├── naming/
        │   └── Stack__Naming.py               (migrated from sgraph_ai_service_playwright__cli/aws/)
        ├── cli/
        │   ├── Cli__Aws.py
        │   ├── Cli__Aws_Dns.py
        │   └── Cli__Aws_Acm.py
        ├── dns/                               (service / schemas / enums / primitives / collections — same shape as Option B)
        ├── acm/                               (same)
        └── tests/                             (same)
```

Migration cost: one move of `Stack__Naming.py` + import-path updates wherever
it's imported (currently a small footprint — verify before commit). The
`scripts/provision_ec2.py` registration changes from importing
`sgraph_ai_service_playwright__cli.aws.cli.Cli__Aws` to
`sg_compute_specs.platform.aws.cli.Cli__Aws`. All other §6 content is identical.

---

## 7. AWS resources & IAM

### boto3 operations called by `Route53__AWS__Client`

| Method | boto3 client call | Read/Write |
|--------|-------------------|------------|
| `list_hosted_zones` | `route53:ListHostedZones` | R |
| `find_hosted_zone_by_name` | `route53:ListHostedZonesByName` | R |
| `resolve_default_zone` (sgraph.ai) | `route53:ListHostedZonesByName` | R |
| `get_hosted_zone` | `route53:GetHostedZone` | R |
| `list_records` | `route53:ListResourceRecordSets` | R |
| `get_record` | `route53:ListResourceRecordSets` (filtered) | R |
| `create_record` | `route53:ChangeResourceRecordSets` | W |
| `upsert_record` | `route53:ChangeResourceRecordSets` | W |
| `delete_record` | `route53:ChangeResourceRecordSets` + `route53:ListResourceRecordSets` | W + R |
| `get_change` (P2 polling) | `route53:GetChange` | R |

STS for account-id resolution (used by the table header): `sts:GetCallerIdentity`.

### boto3 operations called by `ACM__AWS__Client`

| Method | boto3 client call | Read/Write |
|--------|-------------------|------------|
| `list_certificates` | `acm:ListCertificates` (paginated) | R |
| `describe_certificate` | `acm:DescribeCertificate` | R |
| `list_certificates__dual_region` | the two above, twice | R |
| `list_certificates__all_regions` | the two above, looped | R |

### Minimum IAM permissions

**Read-only (P0):**
- `route53:ListHostedZones`
- `route53:ListHostedZonesByName`
- `route53:GetHostedZone`
- `route53:ListResourceRecordSets`
- `acm:ListCertificates`
- `acm:DescribeCertificate`
- `sts:GetCallerIdentity`

**Read + write (P1):**
- All of the above, plus:
- `route53:ChangeResourceRecordSets` — **scope to specific hosted zone ARN(s)** in the IAM policy resource block to limit blast radius (e.g. `arn:aws:route53:::hostedzone/Z09876543...`)
- `route53:GetChange` — for the eventual `wait` / polling support (P2)

**No `ec2:*` / `iam:*` / `cloudfront:*` permissions required.**

### Region semantics (new — Q6 follow-up)

Several AWS surfaces this brief touches are region-special:

| Surface | Region rule | This brief's response |
|---------|-------------|------------------------|
| **Route 53** (hosted zones, records) | Global API — region is ignored by the service, but `--region` flag is forwarded to the boto3 client for endpoint selection (operators with SSO profiles tied to a region expect it). | `dns` commands accept `--region` (no-op for R53 logic; forwarded to boto3). |
| **ACM certs for CloudFront** | **MUST live in us-east-1.** CloudFront only attaches certs from `us-east-1`, regardless of the distribution's actual edge locations. | `acm list` defaults to **current region + us-east-1**, deduped. `--all-regions` available. |
| **ACM certs for ELB / API Gateway / direct service use** | Region of the consuming resource. | Surfaced by the dual-region default (covers ~95% of cases) and `--all-regions` for the rest. |
| **CloudFront** | Global resource, but **always reported from `us-east-1`** by the AWS APIs. | Out of scope for this brief (CF lifecycle is the CF+R53 brief). The us-east-1 quirk is documented here so the operator isn't surprised when `sg aws cloudfront list` (future) only works against us-east-1. |
| **IAM** | Global — all `iam:*` calls hit the global endpoint. | Out of scope. |
| **STS `GetCallerIdentity`** | Effectively global; safe in any region. | Used in renderers for account-id header. |

Bottom line: **`acm list` defaults to dual-region (current + us-east-1)** because
CloudFront-attached certs always live in us-east-1 and the operator usually
wants to see them alongside whatever's in their current region. The
`--all-regions` flag covers exotic cases (ELB certs in regions the operator
hasn't pinned).

### AWS resource naming

This brief introduces **no** persistent AWS resources of its own. Records,
zones, and certs it touches are operator-supplied. No tagging / naming
convention applies from this brief.

---

## 8. Phased rollout

### P0 — Read-only DNS center + ACM listing

**Scope:** zones + records list/show, ACM list/show, `sgraph.ai` default
zone resolution. No DNS mutations. No propagation checker.

1. `Route53__AWS__Client` ships with **read methods only**:
   `list_hosted_zones`, `find_hosted_zone_by_name`, `resolve_default_zone`
   (sgraph.ai caching), `get_hosted_zone`, `list_records`, `get_record`.
2. `ACM__AWS__Client` ships with full read surface:
   `list_certificates`, `list_certificates__dual_region`,
   `list_certificates__all_regions`, `describe_certificate`.
3. All schemas, enums, primitives, collections shipped (including
   `Schema__Dns__Check__Result` and `Enum__Dns__Resolver` — the checker uses
   these in P1 but their type-shape is stable and ships now).
4. CLI subcommands shipped: `dns zones list`, `dns zones show`,
   `dns records list`, `dns records get`, `acm list`, `acm show`.
5. `--json` works on all of the above.
6. `--zone` defaults to `sgraph.ai` everywhere it applies.
7. In-memory subclasses + tests shipped.
8. Reality doc entry filed under `team/roles/librarian/reality/` marking
   the read-only surface EXISTS.

**Acceptance:**
- `sg aws dns zones list` lists every zone in the dev account.
- `sg aws dns records list` (no `--zone`) returns `sgraph.ai` records;
  `--zone vault.sgraph.ai` returns vault records.
- `sg aws acm list` returns certs from current region + us-east-1.
- All commands work with `--json`.
- Read-only IAM role suffices.

### P1 — Record mutations + propagation checker (standalone)

**Scope:** make the CLI an editing surface; add the standalone `records check`.

1. `Route53__AWS__Client` gains `create_record`, `upsert_record`,
   `delete_record`, `upsert_a_alias_record` (library-only — no CLI command).
2. CLI subcommands shipped: `dns records add`, `dns records update`,
   `dns records delete`.
3. Confirmation prompts on `update` / `delete` (Q4-A).
4. `--yes` flag added.
5. `SG_AWS__DNS__ALLOW_MUTATIONS=1` env gate (Q4 safety net — locked in).
6. Diff preview in the confirmation prompt (show old → new).
7. `Route53__Propagation__Checker` shipped, `dnspython` added as a direct dep
   (pending Q7 sign-off).
8. CLI subcommand shipped: `dns records check` with `--expect`, `--min-resolvers`,
   `--flush-local`, `--json`.
9. Exit-code mapping: 0 = all match, 1 = quorum failed, 2 = local cache stale.

**Acceptance:**
- `sg aws dns records add ...` creates a record; fails cleanly if it exists.
- `sg aws dns records update ...` upserts.
- `sg aws dns records delete ...` requires `--yes` + env gate or interactive
  confirmation; fails cleanly without.
- `sg aws dns records check zen-darwin --expect 203.0.113.5` returns a table
  of 8 resolvers + local; exit code reflects quorum + local state.
- All mutations return a `Schema__Route53__Change__Result` printed by the
  renderer (change-id + status).
- Integration test against real Route 53 dev zone gated on
  `SG_AWS__DNS__INTEGRATION=1`.

### P2 — Verify chaining + ACM enumeration polish

**Scope:** convenience layers on top of P1; no new core primitives.

1. `--verify` flag on `records add` and `records update`: after submitting the
   change, automatically invoke the propagation checker with the just-applied
   `--expect <value>` and poll until quorum met or timeout (Q8).
2. `--all-regions` flag on `acm list` exercised in CI against a fixture (P0
   ships the method but `--all-regions` is unverified at scale until P2).
3. `get_change` polling for the eventual `--wait` flag on mutations.
4. (Possible — only if explicitly re-requested per Q5) `records alias` as a
   CLI command. **Currently not planned.**

**Acceptance:**
- `sg aws dns records add zen-mendel --type A --value 1.2.3.4 --verify --zone
  vault.sgraph.ai` submits, waits, runs `records check`, exits 0 only when
  quorum met.

---

## 9. Risks & mitigations

| # | Risk | Mitigation |
|---|------|------------|
| R1 | Fat-fingered `records delete` on prod DNS — site goes dark | (a) Confirmation prompt with diff preview (Q4-A). (b) `SG_AWS__DNS__ALLOW_MUTATIONS=1` env gate — **locked in (Q4 RESOLVED)**. (c) `--yes` is documented as "I have verified the diff". (d) IAM policy in production scoped to specific hosted-zone ARNs only. |
| R2 | `records update` on the wrong record (typo in name resolves to a different existing record) | Confirmation prompt shows the **resolved** FQDN (including the resolved default `sgraph.ai` zone) and the current values being replaced. Operator can abort. |
| R3 | Zone-name resolution silently picks the wrong zone in multi-zone accounts (`example.com` vs `example.com.eu`) | `find_hosted_zone_by_name` requires an **exact** name match. If `list_hosted_zones_by_name` returns >1 candidate, raise with the list. Never auto-pick. Same rule applies to the `sgraph.ai` default lookup — exact match only. |
| R4 | TTL set too low (1s) on a high-traffic record — DNS load explodes | `Safe_Int__TTL` validates 1..86400; CLI default 300s; **warn** if TTL < 60s and require `--yes` to proceed. |
| R5 | TXT record with embedded quotes broken by shell quoting | CLI's `--value` flag accepts the raw string; `Route53__AWS__Client` quotes it for the API. Document with examples in the help text. |
| R6 | Cross-account confusion — operator runs `sg aws dns records delete` thinking they're in dev, actually in prod | Default table-header line shows the resolved AWS account-id (from `sts:GetCallerIdentity`) and the profile. Mutations include account-id in the confirmation prompt. The `--zone` default of `sgraph.ai` magnifies this risk — the confirmation prompt **always** shows the resolved zone name + zone-id, even when defaulted. |
| R7 | boto3 pagination missed on `list_resource_record_sets` — partial record listings hide records from `records list`, then `add` later fails on duplicate | All `list_*` methods use the boto3 paginator (`get_paginator(...).paginate()`), never raw `list_*` calls. Unit-tested with multi-page in-memory fixture. |
| R8 | `delete_record` requires the full current RR-set body — race condition between read and write means a concurrent mutator's value is silently deleted | Document the race. P2 can add `IfMatch`-style ETag if Route 53 ever supports it (today it doesn't); P1 mitigation is the confirmation prompt + short window. |
| R9 | `sgraph.ai` is not in the operator's account → every command fails on default-zone lookup | Failure is clear: `"--zone unset and no 'sgraph.ai' hosted zone found in account 123456789012. Pass --zone explicitly or provision the zone in this account."` Documented in `--help`. |
| R10 | **`dig` not installed on operator's machine** (rare on macOS / Linux, common on minimal containers) | `Route53__Propagation__Checker.check_local` detects `FileNotFoundError` from `subprocess.run` and degrades cleanly: skip the local check, report `local_answer = null`, set `exit_code = 2` only when `--flush-local` was passed (i.e. operator explicitly cared). Help text notes the dependency. |
| R11 | **`--flush-local` requires sudo on macOS** (`sudo killall -HUP mDNSResponder`) | `--flush-local` documented as "may prompt for sudo on macOS". Default OFF. If sudo prompt fails, skip the flush + warn, don't abort the check. Linux path (`systemd-resolve --flush-caches`) only needs sudo on some distros. |
| R12 | `dnspython` not currently a dep — adding it widens the dependency surface (Q7) | Mature library, pure Python, MIT, transitive-dep-free for the features used. Vetted by adding it under `[tool.poetry.dependencies]` with an upper-bound `^2.6` and re-locking. If the user rejects (Q7), fall back to shelling out to `dig` for every resolver — loses parallelism + clean error semantics. |
| R13 | Quorum threshold (5/8 default) is wrong for the operator's network — false alarms or false reassurances | `--min-resolvers` is a flag; help text documents the trade-off; default chosen because Route 53 propagation is usually all-or-nothing within ~60s and 5/8 catches the in-progress case. Operators with weird ISPs can lower it. |
| R14 | The `sg aws` Typer group does not exist today; first attempt to wire it into `scripts/provision_ec2.py` could collide | **Pre-Dev audit complete** — top-level `sg` Typer root located at `scripts/provision_ec2.py:769`. No existing `add_typer(..., name='aws')` registration. Slot is free. |
| R15 | `osbot-aws` later adds Route 53 / ACM helpers; our direct-boto3 boundary becomes inconsistent | Document the upgrade path in each `*__AWS__Client.py` header (mirrors the `Elastic__AWS__Client` template). File the upstream-osbot-aws follow-up brief once this lands. |

---

## 10. Test plan sketch

The repo's pytest convention: **no mocks, no patches** (CLAUDE.md, testing
guidance). Two test tracks.

### Track A — unit / in-memory (mandatory, runs in CI)

| Test file | What it asserts |
|-----------|------------------|
| `tests/service/test_Route53__AWS__Client.py` | Construction; method signatures match §5; an `Route53__AWS__Client__In_Memory` subclass (in `tests/service/_in_memory.py`) implements the boto3-layer methods against a dict-backed fixture, no `mock` module; each public method returns the documented schema shape; pagination across multiple pages works; `find_hosted_zone_by_name` raises on ambiguous match; **`resolve_default_zone` returns the `sgraph.ai` entry on first call, returns the cached entry without a second boto3 call on the second invocation, and raises `Route53__Default_Zone_Not_Found` when no `sgraph.ai` entry exists**. |
| `tests/service/test_Route53__Propagation__Checker.py` | An in-memory fake resolver returns canned per-resolver answers. Assert: quorum-met when 5/8 match (default), quorum-failed when 4/8 match (and `--min-resolvers 5`), exit-code 0/1/2 mapping, local-check `subprocess.run` is replaced by a fake invokable returning canned dig output (no real `dig` spawn), `flush_local=True` triggers the OS-detection branch (returns False on Linux test runner without sudo — that's the documented "skip with warning" path). |
| `tests/service/test_ACM__AWS__Client.py` | Construction; an `ACM__AWS__Client__In_Memory` subclass with a `{region: [cert]}` fixture; `list_certificates(region)` returns the list; `list_certificates__dual_region()` dedupes when current = us-east-1; ARN-derived region in `describe_certificate(arn)` parses correctly for both standard and gov-cloud ARN shapes; `list_certificates__all_regions()` iterates over the expected region set. |
| `tests/cli/test_Cli__Aws_Dns.py` | Mirrors `test_Cli__Vault_App.py`: `runner.invoke(app, ['--help'])`, `[zones, --help]`, `[records, --help]`, every subcommand has `--help`. Help text contains expected flags (`--json`, `--type`, `--ttl`, `--yes`, `--zone`, `--expect`, `--min-resolvers`, `--flush-local`). Renderer output (with no-color console) contains expected zone names and record types. `--json` output parses as valid JSON and round-trips through the schema. **No-`--zone` invocations resolve to `sgraph.ai` in the renderer header.** |
| `tests/cli/test_Cli__Aws_Acm.py` | Mirrors above for ACM: list, show, JSON round-trip. Default invocation reports two regions in the header (current + us-east-1). |
| `tests/schemas/test_Schema__Route53__Record.py` | Type_Safe construction; raw primitives rejected; enum-based `type` field rejects unknown values; round-trips via `.json()` and reconstruction. |
| `tests/schemas/test_Schema__Dns__Check__Result.py` | Construction; per-resolver list shape; quorum + local fields present; round-trips. |
| `tests/schemas/test_Schema__ACM__Certificate.py` | Construction; enum-based `status` and `cert_type`; round-trips. |
| `tests/primitives/test_Safe_Str__Hosted_Zone_Id.py` | Accepts `Z01234567ABCDEFGHIJKL`; rejects lowercase, too-long, too-short. |
| `tests/primitives/test_Safe_Str__Resolver_IP.py` | Accepts IPv4 dotted-quad (`8.8.8.8`, `1.1.1.1`); accepts compressed IPv6; rejects hostnames; rejects malformed strings. Uses `ipaddress` stdlib at validation time. |
| `tests/primitives/test_Safe_Int__TTL.py` | 1..86400 accepted; 0 rejected (or accepted, depending on Q-followup); negative rejected. |

### Track B — integration / real AWS (gated)

Gate on `SG_AWS__DNS__INTEGRATION=1` (a real AWS profile pointed at a test
hosted zone) and `SG_AWS__ACM__INTEGRATION=1` for ACM. Numbered tests,
top-down (deploy-via-pytest style):

```
test_1__list_hosted_zones__returns_at_least_one_zone
test_2__resolve_default_zone__finds_sgraph_ai
test_3__find_hosted_zone_by_name__resolves_test_zone
test_4__list_records__returns_default_NS_and_SOA
test_5__create_record__a_record_in_test_zone
test_6__get_record__finds_the_created_record
test_7__check_record__propagation_passes_within_120s
test_8__upsert_record__changes_the_a_record_value
test_9__delete_record__removes_the_record
test_10__list_records__no_longer_contains_the_record
test_11__acm__list_certificates_dual_region__returns_results
test_12__acm__describe_certificate__round_trips_arn
```

Each test is independent of the *Track A* run; carries state via a tmp-path
fixture (e.g. the test record name is a uuid-derived FQDN so re-runs don't
collide). `test_7` is the only test that genuinely takes wall-clock time —
gated separately on `SG_AWS__DNS__INTEGRATION__SLOW=1`.

### Is an in-memory fake feasible?

**Yes for Track A.** Route 53's API surface is small (∼6 methods used here)
and its data model is a flat list of resource record sets per zone. ACM's
surface is even smaller (2 methods, paginated list). The propagation checker's
fake is a dict mapping resolver-IP → canned answer; `subprocess.run` is replaced
by a fake callable in-process (composition, not `mock.patch`). All deterministic,
all fast.

**No for Track B.** Pagination quirks, change-status polling timing, name
servers, real-world propagation latency, IAM permission edges, and ACM
in-use-by counts only show up against the real API. Gate on the env vars;
skip cleanly in normal CI.

### Not unit-testable

- Real Route 53 change-status propagation (`PENDING` → `INSYNC`) — Track B only.
- Real-world DNS propagation across global resolvers — Track B (or manual via
  `sg aws dns records check`).
- macOS sudo prompt for `--flush-local` — manual verification.
- IAM-permission-denied error shapes — manual / Track B with a restricted policy.
- Multi-account / multi-profile resolution — manual verification.

---

## 11. Next actions (decisions the user must make before Dev starts)

In order of blockingness:

1. **Q1** — confirm **Option B** (`sgraph_ai_service_playwright__cli/aws/{dns,acm}/`
   layout) is the right home, or escalate to **Option C**
   (`sg_compute_specs/platform/aws/{dns,acm}/` new tier). Architect
   recommendation: **B**, with the misconception-correction noted (the CLI
   namespace is NOT legacy per reality doc v0.1.31).
2. **Q7** — confirm `dnspython` as a direct dep, or require a `dig`-shell-out
   fallback. Architect recommendation: **add `dnspython`**.
3. **Q8** — confirm `--verify` chaining on `records add` / `records update` is
   P2 (not P1). Architect recommendation: **P2**.
4. **Scope** — confirm P0 (read-only DNS + ACM list + sgraph.ai default) is the
   first slice Dev picks up. Smallest, lowest-risk, unblocks the bigger CF+R53
   plan's read paths.
5. **`SG_AWS__DNS__ALLOW_MUTATIONS=1` env-var name** — bikeshed-safe but
   double-check the name is the one we want before P1 ships. (Q4 RESOLVED on
   *requiring* the gate; the *name* is editable.)

### RESOLVED items (no further user action)

- **Q2** — `add` is strict CREATE, `update` is UPSERT.
- **Q3** — No hosted-zone CRUD ever. List/show only.
- **Q4** — Confirm on `update` / `delete`; `--yes` skips; `SG_AWS__DNS__ALLOW_MUTATIONS=1`
  env gate required.
- **Q5** — No `records alias` CLI command. Library helper only.
- **Q6** — `--profile` + `--region` on every command. ACM defaults dual-region.

### Dev contract (when Q1 / Q7 / Q8 land)

- The files in §6 are the slice.
- §5's method tables are the boundaries.
- §10 Track A is the test bar.
- §7's "Region semantics" sub-section is the rationale for ACM's dual-region default.
- The reality doc must be updated when the slice lands, registering
  `sg aws dns` zones/records/check and `sg aws acm` list/show as EXISTS and
  removing the PROPOSED label at the top of this brief.
- The bigger CF+R53 brief (`05/15/03/architect__vault-app__cf-route53__plan.md`)
  can be updated to **consume** `Route53__AWS__Client` and `ACM__AWS__Client`
  rather than define its own — one Architect follow-up review entry.

---

*Filed by Architect (Claude), 2026-05-15. No code changed by this document — it
is a plan and a set of decisions for human ratification before Dev picks it up.
Rev 2 folds in user feedback: default zone `sgraph.ai`, propagation checker
(`records check` with 8 public resolvers + local dig), ACM list/show (dual-region
default), Q2/Q3/Q4/Q5/Q6 resolved, Q1 re-investigated against the proposed
`sg_compute_specs/platform/` tier with explicit recommendation. This brief
remains the simpler standalone subset of
`05/15/03/architect__vault-app__cf-route53__plan.md`; the bigger plan will
consume the `Route53__AWS__Client` + `ACM__AWS__Client` primitives this brief
defines, instead of introducing its own.*
