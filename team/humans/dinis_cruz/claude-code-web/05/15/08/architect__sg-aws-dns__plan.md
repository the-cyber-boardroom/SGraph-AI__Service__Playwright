---
title: "Architect Briefing — sg aws dns: Route 53 DNS Management Center"
file: architect__sg-aws-dns__plan.md
author: Architect (Claude)
date: 2026-05-15 (UTC hour 08)
repo: SGraph-AI__Service__Playwright @ dev (v0.1.140 line)
status: PLAN — no code, no commits. For human ratification before Dev picks up.
parent: team/humans/dinis_cruz/claude-code-web/05/15/03/architect__vault-app__cf-route53__plan.md
revision: "rev 6 (2026-05-15 hour 14) — adds `sg aws dns instance create-record` (P1) that resolves an instance-id / stack-name / `--latest` to a public IP and creates an A record under the matching hosted zone, default TTL 60s, with idempotent same-IP handling and a verbatim cert-warning info block printed after the success table; multi-label name support documented (§3 new sub-section + permissive `Safe_Str__Record_Name` regex) and backed by a new `Route53__Zone__Resolver` that walks labels to find the deepest owning hosted zone; new `Route53__Instance__Linker` consuming the per-spec `info` helpers from `sg_compute_specs/{vault_app,playwright,elastic,neko}/cli/`; new IAM action `ec2:DescribeInstances` (and `ec2:DescribeTags` already covered by it); new risk R17 — instance public IP changes on stop/start, P2 follow-up `dns instance refresh-record` or pinned EIP; new ADDENDUM §12 capturing two PROPOSED, NOT-IN-P1 cert-issuance paths (Path A — own cert sidecar reusing `sg_compute/platforms/tls/Cert__ACME__Client`; Path B — AWS Certificate Manager) plus new open Q9 on DNS-01 vs HTTP-01 for the future cert path. `Cert__ACME__Client` is **HTTP-01 only today** (verified by reading `sg_compute/platforms/tls/Cert__ACME__Client.py` — `select_http01` hard-codes the `challenges.HTTP01` filter, `ACME__Challenge__Server` binds :80 directly, no DNS-01 challenge type referenced); DNS-01 is documented as the preferred future challenge mode and is the subject of new Q9."
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
update / delete records on any zone, **verify records via three modes
(authoritative-NS direct query by default, public resolvers and local `dig`
as opt-in)**, and **list ACM certificates** — independent of whether a stack-creation
flow is in play. The same `Route53__Client` primitive that this brief
introduces is then *consumed* by the larger CF+R53 plan: the bigger plan stops
having to define one and instead orchestrates this one. Concretely:

- **This brief delivers:** `Route53__AWS__Client`, the three checker classes
  (`Route53__Authoritative__Checker`, `Route53__Public_Resolver__Checker`,
  `Route53__Local__Checker`) plus the `Route53__Check__Orchestrator` that
  composes them, `ACM__AWS__Client`, the DNS / ACM schemas, the `sg aws dns` +
  `sg aws acm` Typer surfaces, and the test scaffolding (in-memory +
  integration).
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
3. **Verify DNS records** for any zone across three modes, ordered by
   cache-pollution risk (lowest first):
   - **`--authoritative` (DEFAULT)** — query Route 53's own NS records directly
     with `+norecurse`. Source of truth, zero cache pollution anywhere. This
     is what the operator wants right after `records add` / `update`.
   - **`--public-resolvers` (OPT-IN)** — fan out across a curated 8-resolver
     public set (the whatsmydns.net pattern). Cache-polluting; warning banner
     printed before running.
   - **`--local` (OPT-IN)** — shell out to `dig`. Goes through the host's
     configured upstream resolver (often a corporate proxy); cache-polluting
     at that upstream. Warning banner printed before running.

   Authoritative-only is **P1**. Public-resolvers and local modes are
   **P1.5 / P2**. The `--verify` chaining flag on `records add` / `records
   update` is **P2** (Q8 RESOLVED).
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
10. **One-shot instance → DNS-record convenience (P1).** A new
    `sg aws dns instance create-record <instance>` command resolves an EC2
    instance (by instance-id, by stack-name via the per-spec `info` helpers,
    or via `--latest`), reads its public IPv4, derives a sensible default
    name from the stack / `Name` tag, and creates the A record under the
    matching hosted zone with `--ttl 60` by default. UX mirrors
    `sp playwright create` / `vault-app create`. Idempotent on same-IP;
    fails fast on different-IP unless `--force`. Smart auto-verify path is
    "new name" (authoritative + 6-resolver EU+US public-resolver fan-out).
11. **Multi-label name support.** Names with arbitrary depth (e.g.
    `my-ec2-1.dev.sgraph.ai`) are first-class — the `Safe_Str__Record_Name`
    primitive is a permissive RFC-1035 multi-label regex, and a new
    `Route53__Zone__Resolver` walks up labels to pick the deepest owning
    hosted zone when `--zone` is omitted. Sub-delegated zones (where
    `dev.sgraph.ai` is later promoted to its own zone) work automatically —
    the resolver picks the deepest match. See §3 "Multi-label name handling".

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
sg aws dns records check <name> [--zone <z>]      # verify a record (default: authoritative-NS direct query; opt-in: public resolvers, local dig)
sg aws dns instance                               # group help (NEW — rev 6)
sg aws dns instance create-record <instance>      # one-shot: resolve EC2 instance → public IP → create A record (defaults: ttl=60, name derived from stack/Name tag, zone derived by walking labels)
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
| `dns records add`  | `--zone <name\|id>` (optional, defaults sgraph.ai) `--type A` (required) `--value <ip\|val>` (required, repeatable for multi-value) `--ttl 300` (default) `--comment "..."` `--yes` (skip "create?" confirm) `--no-verify` (skip smart auto-verify entirely — scripting mode) `--verify-public` (force public-resolver check on the upsert path, with WARNING banner) `--json` |
| `dns records update` | `--zone <name\|id>` (optional, defaults sgraph.ai) `--type A` (required) `--value <ip\|val>` (required, repeatable) `--ttl <int>` `--comment "..."` `--yes` (skip "change?" confirm) `--no-verify` (skip smart auto-verify entirely) `--verify-public` (force public-resolver check with WARNING banner) `--json` |
| `dns records delete` | `--zone <name\|id>` (optional, defaults sgraph.ai) `--type A` (required) `--yes` (skip "delete?" confirm) `--no-verify` (skip smart auto-verify entirely) `--verify-public` (force public-resolver check with WARNING banner) `--json` |
| `dns records check`  | `--zone <name\|id>` (optional, defaults sgraph.ai) `--type A` (default) `--expect <value>` (the value the operator expects to see — required for ✓/✗ marking) `--authoritative` (DEFAULT — query Route 53 NS set directly, zero cache pollution) `--public-resolvers` (OPT-IN — fan out across 8 public resolvers; **prints cache-pollution WARNING banner**) `--local` (OPT-IN — shell out to `dig` via host upstream; **prints cache-pollution WARNING banner**) `--all` (= `--authoritative --public-resolvers --local`) `--min-resolvers 5` (quorum for public-resolvers mode) `--json`. Mode flags are stackable. Default invocation runs authoritative only. **`--flush-local` is NOT offered** — platform-native cache flushing is left to the operator. |
| `dns instance create-record` | **NEW (rev 6).** Positional `<instance>` (one of: EC2 instance-id `i-…`, stack name resolved via `sg_compute_specs/{vault_app,playwright,elastic,neko}/cli/` `info` helpers, or `--latest` for the most recently launched instance carrying the SG-AI tag). `--name <fqdn>` (optional — derived from stack name / `Name` tag when omitted). `--zone <name\|id>` (optional — defaults `sgraph.ai`; if `--name` is a multi-label FQDN, the deepest owning zone is auto-selected via `Route53__Zone__Resolver`). `--ttl 60` (**default 60s**, not 300). `--type A` (default). `--verify/--no-verify` (default verify-on — runs the smart-verify new-name path: authoritative + 6-resolver EU+US public-resolver fan-out, no WARNING banner since the name is brand-new by construction). `--force` (override the "exists, points at a different IP" guard). `--yes` (skip the create-confirmation prompt). `--json` |
| `acm list`           | `--region <name>` (override; defaults: current + us-east-1) `--all-regions` (loop with rate limiting) `--json` |
| `acm show`           | `--region <name>` (defaults: us-east-1 if `<arn>` is a us-east-1 ARN, else current; or auto-resolve from ARN region segment) `--json` |

### Multi-label name handling (NEW — rev 6)

Route 53 fully supports arbitrary-depth records inside a single hosted zone.
`my-ec2-1.dev.sgraph.ai` can live in the **`sgraph.ai`** zone as a single
record without `dev.sgraph.ai` ever being a separate hosted zone. There is
no schema or API constraint at the AWS side.

What this brief commits to:

- **`Safe_Str__Record_Name` is permissive.** The regex accepts arbitrary-
  depth RFC-1035 multi-label names:

  ```
  ^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$
  ```

  Total length capped at 253 (RFC 1035). Trailing-dot tolerated and
  normalised. Empty labels rejected. The single-label primitive form
  (`zen-darwin`) is still accepted — it falls under the optional left-hand
  group. See §6 for the primitive's full validation rules.

- **Zone resolution walks labels deepest-first.** When `--zone` is omitted
  and `--name` is a multi-label FQDN, a new helper
  `Route53__Zone__Resolver.resolve_zone_for_name(fqdn)` lists hosted zones
  once per process, then walks the FQDN's labels deepest-first and picks
  the longest suffix match. Worked examples:

  | FQDN passed | Hosted zones in account | Resolver picks |
  |-------------|--------------------------|-----------------|
  | `my-ec2-1.dev.sgraph.ai` | `sgraph.ai` only | `sgraph.ai` (record name `my-ec2-1.dev.sgraph.ai`) |
  | `my-ec2-1.dev.sgraph.ai` | `sgraph.ai` AND `dev.sgraph.ai` (future sub-delegation) | `dev.sgraph.ai` (record name `my-ec2-1.dev.sgraph.ai`) — deepest match |
  | `quiet-fermi.sgraph.ai` | `sgraph.ai` only | `sgraph.ai` |
  | `something.elsewhere.com` | `sgraph.ai` only | **error** — no owning zone in account |

- **Explicit `--zone` enforces containment.** If the operator passes
  `--zone vault.sgraph.ai --name my-ec2-1.dev.sgraph.ai`, the CLI fails
  with `name 'my-ec2-1.dev.sgraph.ai.' is not under zone 'vault.sgraph.ai.'`
  before any boto3 call is made.

- **Sub-delegation is automatic, no code change.** If `dev.sgraph.ai`
  is later promoted to a separate hosted zone with NS records in
  `sgraph.ai`, `Route53__Zone__Resolver.resolve_zone_for_name(...)`
  picks `dev.sgraph.ai` automatically because it is the longest suffix
  match. No code change required when sub-delegation is introduced.

Hosted-zone CRUD remains out of scope (Q3 RESOLVED → A) — sub-delegation
is set up by the operator via the AWS console; this CLI simply picks the
right zone afterwards.

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

**`sg aws dns records add zen-darwin --type A --value 203.0.113.5 --ttl 60 --zone vault.sgraph.ai`** (smart auto-verify, **new-name path** — public-resolver fan-out is safe):

```
  Pre-flight: zen-darwin.vault.sgraph.ai. A — not currently in zone (new name).

  About to create record:
    zone   : vault.sgraph.ai.  (Z09876543ZYXWVUTSRQPO)
    name   : zen-darwin.vault.sgraph.ai.
    type   : A
    ttl    : 60
    value  : 203.0.113.5
  Continue? [y/N]: y

  ✓  Record created  ·  change-id C0123456ABCDEF  ·  status PENDING

  Auto-verify: new name — no prior recursive cache to pollute, so the
  authoritative check AND a curated 6-resolver EU+US public-resolver check
  are both run. Safe by construction.

  Authoritative nameservers (Route 53 delegation set; +norecurse)
  Nameserver                          Answer            Match
  ──────────────────────────────────  ────────────────  ─────
  ns-123.awsdns-12.com.               203.0.113.5       ✓
  ns-456.awsdns-56.net.               203.0.113.5       ✓
  ns-789.awsdns-78.org.               203.0.113.5       ✓
  ns-1011.awsdns-10.co.uk.            203.0.113.5       ✓

  Authoritative agreement: 4 / 4   ✓

  Public resolvers (6 — curated EU + US set; safe on new name)
  Resolver         IP               Geo  Answer        Match
  ───────────────  ───────────────  ───  ────────────  ─────
  Cloudflare       1.1.1.1          US   203.0.113.5   ✓
  Cloudflare       1.0.0.1          EU   203.0.113.5   ✓
  Google           8.8.8.8          US   203.0.113.5   ✓
  Google           8.8.4.4          EU   203.0.113.5   ✓
  Quad9            9.9.9.9          Any  203.0.113.5   ✓
  AdGuard EU       94.140.14.14     EU   203.0.113.5   ✓

  Public-resolver agreement: 6 / 6   ✓  PASS

  Exit code: 0
```

**`sg aws dns records add zen-darwin --type A --value 203.0.113.99 --ttl 60 --zone vault.sgraph.ai`** (smart auto-verify, **upsert path** — name+type already exists; the existing TTL is 60s; public-resolver check is skipped):

```
  Pre-flight: zen-darwin.vault.sgraph.ai. A — already exists (current value 203.0.113.5, ttl 60s). This will be treated as an UPSERT.

  About to UPSERT record:
    zone   : vault.sgraph.ai.  (Z09876543ZYXWVUTSRQPO)
    name   : zen-darwin.vault.sgraph.ai.
    type   : A
    ttl    : 60      (was 60)
    value  : 203.0.113.99   (was 203.0.113.5)
  Continue? [y/N]: y

  ✓  Record upserted  ·  change-id C0123456ABCDEG  ·  status PENDING

  Auto-verify (authoritative only):

  Authoritative nameservers (Route 53 delegation set; +norecurse)
  Nameserver                          Answer            Match
  ──────────────────────────────────  ────────────────  ─────
  ns-123.awsdns-12.com.               203.0.113.99      ✓
  ns-456.awsdns-56.net.               203.0.113.99      ✓
  ns-789.awsdns-78.org.               203.0.113.99      ✓
  ns-1011.awsdns-10.co.uk.            203.0.113.99      ✓

  Authoritative agreement: 4 / 4   ✓  PASS

  Authoritative is consistent. Public-resolver check skipped — would risk
  locking in stale answers for the remaining ~60s of the prior record's
  TTL. Run `sg aws dns records check zen-darwin --zone vault.sgraph.ai
  --public-resolvers` once the old TTL has elapsed.

  Exit code: 0
```

**`sg aws dns records delete zen-darwin --type A --zone vault.sgraph.ai --yes`** (smart auto-verify, **delete path** — prior record had ttl 60s; public-resolver check is skipped):

```
  Pre-flight: zen-darwin.vault.sgraph.ai. A — exists (current value
  203.0.113.99, ttl 60s). This will be DELETED.

  About to DELETE record:
    zone   : vault.sgraph.ai.  (Z09876543ZYXWVUTSRQPO)
    name   : zen-darwin.vault.sgraph.ai.
    type   : A
    ttl    : 60
    value  : 203.0.113.99
  (--yes supplied; skipping interactive confirm)

  ✓  Record deleted  ·  change-id C0123456ABCDEH  ·  status PENDING

  Auto-verify (authoritative only):

  Authoritative nameservers (Route 53 delegation set; +norecurse)
  Nameserver                          Answer            Match
  ──────────────────────────────────  ────────────────  ─────
  ns-123.awsdns-12.com.               NXDOMAIN          ✓
  ns-456.awsdns-56.net.               NXDOMAIN          ✓
  ns-789.awsdns-78.org.               NXDOMAIN          ✓
  ns-1011.awsdns-10.co.uk.            NXDOMAIN          ✓

  Authoritative agreement: 4 / 4   ✓  PASS  (NXDOMAIN as expected)

  Authoritative confirms deletion. Public-resolver check skipped —
  recursives may still serve the cached positive answer for up to ~60s.
  Run `sg aws dns records check zen-darwin --zone vault.sgraph.ai
  --public-resolvers` after that to confirm propagation.

  Exit code: 0
```

**`sg aws dns records check zen-darwin --zone vault.sgraph.ai --expect 203.0.113.5`** (default — authoritative-only, zero cache pollution):

```
  Resolving zen-darwin.vault.sgraph.ai.  type A  expect 203.0.113.5
  Mode: authoritative (Route 53 NS set, +norecurse) — zero cache pollution

  Authoritative nameservers for vault.sgraph.ai. (Route 53 delegation set)
  Nameserver                          Answer            Match
  ──────────────────────────────────  ────────────────  ─────
  ns-123.awsdns-12.com.               203.0.113.5       ✓
  ns-456.awsdns-56.net.               203.0.113.5       ✓
  ns-789.awsdns-78.org.               203.0.113.5       ✓
  ns-1011.awsdns-10.co.uk.            203.0.113.5       ✓

  Authoritative agreement: 4 / 4   ✓  PASS

  Exit code: 0

  (Tip: re-run with --public-resolvers to verify global propagation after
   you're confident the value is final. That mode caches the answer at each
   public resolver for up to the record's TTL.)
```

**`sg aws dns records check zen-darwin --zone vault.sgraph.ai --expect 203.0.113.5 --public-resolvers`** (opt-in — fans out to public resolvers; warning banner shown first):

```
  WARNING: --public-resolvers will cache the answer at each of the 8 public
  resolvers below for up to this record's TTL. If you change this record
  again, those resolvers will return the OLD value until that TTL elapses,
  and there is NO way to flush a third-party recursive cache. Only run
  --public-resolvers once you are confident the value is final. Use the
  default --authoritative mode for iterative verification.

  Continue with --public-resolvers? [y/N]: y

  Resolving zen-darwin.vault.sgraph.ai.  type A  expect 203.0.113.5
  Mode: public-resolvers (8 resolvers; cache-polluting)

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

  Exit code: 0
```

**`sg aws dns records check zen-darwin --zone vault.sgraph.ai --expect 203.0.113.5 --local`** (opt-in — shells out to `dig`; warning banner shown first):

```
  WARNING: --local will shell out to `dig` on this host. That query goes
  through whatever upstream resolver this machine is configured to use
  (often a corporate proxy or VPN resolver), and that resolver WILL cache
  the answer for up to the record's TTL. If you change this record again,
  this host (and anyone else behind the same upstream) will see the OLD
  value until that TTL elapses. There is no portable way to flush a
  third-party upstream cache; flush your local OS cache with platform-native
  tooling if needed. Use the default --authoritative mode for iterative
  verification.

  Continue with --local? [y/N]: y

  Resolving zen-darwin.vault.sgraph.ai.  type A  expect 203.0.113.5
  Mode: local (`dig +short`; host upstream resolver; cache-polluting)

  Local resolver
  Source                            Answer            Match
  ────────────────────────────────  ────────────────  ─────
  dig (host upstream)               203.0.113.5       ✓

  Local: 1 / 1 match expected   ✓  PASS

  Exit code: 0
```

**Exit code mapping:**

- `0` — every selected check passed.
- `1` — **authoritative disagreement** (at least one Route 53 NS returned a
  different value — Route 53 itself has not converged; the bad case).
- `2` — **public-resolvers quorum failed** (propagation not yet global, but
  Route 53 is consistent — usually transient, retry after TTL).
- `3` — **local mismatch** (host's upstream resolver disagrees; almost
  always a stale upstream cache — flush manually with platform-native
  tooling if needed).
- `4` — **`dns instance create-record` conflict** (NEW — rev 6 — record
  with the derived / `--name`-supplied FQDN already exists pointing at a
  DIFFERENT IP from the resolved instance, and `--force` was not passed).

**`--all` combined banner.** When the operator passes `--all` (=
`--authoritative --public-resolvers --local`), a single combined warning is
printed once before any query runs:

```
  WARNING: --all enables BOTH cache-polluting modes (--public-resolvers
  and --local) in addition to the safe --authoritative check. The 8 public
  resolvers AND your host's upstream resolver will each cache the answer
  for up to the record's TTL. If you change this record again afterwards,
  those caches will return the OLD value until that TTL elapses, and
  there is NO way to flush a third-party recursive cache. Only run --all
  once you are confident the value is final. Prefer the default
  --authoritative mode for iterative verification.

  Continue with --all? [y/N]:
```

**`sg aws dns instance create-record i-0abc1234`** (NEW — rev 6 — happy path; instance has `Name=quiet-fermi`, `sg-ai=...`, IP `54.92.13.7`; zone defaults to `sgraph.ai`):

```
  Resolved instance i-0abc1234 → public IP 54.92.13.7 (stack: quiet-fermi)
  Creating A record quiet-fermi.sgraph.ai → 54.92.13.7 (TTL 60s)
  ✓ Route 53 change submitted (change-id /change/C12345)
  ✓ Authoritative: 4/4 NS agree on 54.92.13.7
  ✓ EU+US public resolvers: 6/6 agree on 54.92.13.7
  Done in 4.3s. DNS is live globally.

  ⚠ HTTPS cert
  This DNS name is now usable, but HTTPS clients will see a certificate
  warning until a cert is issued for `quiet-fermi.sgraph.ai`. Today, the
  vault-app / playwright stacks ship Let's Encrypt IP-anchored certs
  (valid for the EC2 public IP, not the DNS name).

  Options to fix:
    (a) `sg playwright vault re-cert --hostname quiet-fermi.sgraph.ai`
        — uses our own cert sidecar workflow. Fast. No AWS account
        pollution. ⚠ PROPOSED — see brief §addendum-cert. NOT IN P1.
    (b) `sg aws acm request --domain quiet-fermi.sgraph.ai` — issues an
        ACM cert. Useful only if you are terminating TLS on CloudFront /
        ELB. ⚠ Adds an entry to ACM that does NOT auto-delete when the
        stack is destroyed. PROPOSED — NOT IN P1.

  For now, accept the cert warning or use the IP-based vault_url
  surfaced by `sp pw v info`.

  Exit code: 0
```

**`sg aws dns instance create-record quiet-fermi`** (idempotent no-op — record already points at this instance's IP):

```
  Resolved instance i-0abc1234 → public IP 54.92.13.7 (stack: quiet-fermi)
  Already correct — record quiet-fermi.sgraph.ai already points at
  54.92.13.7 (TTL 60s). No change submitted.

  (Cert info still applies:)

  ⚠ HTTPS cert
  This DNS name is now usable, but HTTPS clients will see a certificate
  warning until a cert is issued for `quiet-fermi.sgraph.ai`. …  [cert-warning block as above, verbatim]

  Exit code: 0
```

**`sg aws dns instance create-record quiet-fermi`** (record exists pointing at a DIFFERENT IP — fails without `--force`):

```
  Resolved instance i-0abc1234 → public IP 54.92.13.7 (stack: quiet-fermi)
  ✗ Record quiet-fermi.sgraph.ai already exists pointing at 203.0.113.99
    (not 54.92.13.7). Use `sg aws dns records update quiet-fermi --type A
    --value 54.92.13.7 --zone sgraph.ai` or pass `--force` to overwrite.

  Exit code: 4
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

### Q7 — DNS transport: dnspython library vs `dig` shell-out

`records check` needs a DNS-on-the-wire transport for all three modes:

1. **`--authoritative`** — direct NS query with `+norecurse`. Default mode in P1.
2. **`--public-resolvers`** — per-resolver query across the curated set.
3. **`--local`** — host-upstream query.

| Opt | Position |
|-----|----------|
| **A** | Add `dnspython` as a direct dep. Structured results, clean per-query control. |
| **B** | Shell out to `dig` for every query. Zero new runtime deps. |

**[RESOLVED — user choice: B. Use `dig` shell-out; no `dnspython` dependency
added.]**

Rationale (one line): zero new runtime deps; `dig` is universally available
on Linux/macOS (and the Playwright Docker base image
`mcr.microsoft.com/playwright/python:v1.58.0-noble` already ships `dnsutils`);
`dig @<ns> +norecurse <name> <type>` cleanly handles the authoritative
direct-NS query, `dig @<resolver> <name> <type>` handles public-resolver mode,
and the line-oriented output of `dig +short` / `dig +noall +answer` is stable
and parseable. Trade-off: shell-out cost (~5-15ms per invocation) and
parsing fragility (locale-sensitive) versus a library API. Accepted —
mitigations are pinning `LC_ALL=C` in `subprocess.run` env, preferring
`+short` for value extraction, and a thin shared wrapper.

**Implementation note.** A thin helper `Dig__Runner` wraps
`subprocess.run(['dig', ...])`, captures stdout/stderr, surfaces non-zero exit
codes cleanly, and parses `+short` output. All three checkers consume this
helper; no library import on the DNS-on-the-wire boundary.

### Q8 — `--verify` chaining on `records add` / `records update`

After P1 ships the standalone `records check` command, should `records add`
and `records update` accept a `--verify` flag that automatically chains
`records check` after the change has been submitted? The Architect leans
**P2** — keep P1 simple, get the `records check` UX bedded in (especially
the new three-mode design), then add the chaining once the operator confirms
the check's defaults (authoritative-only, quorum, exit codes) match what they
want. Cheap to add later.

**[SUPERSEDED in rev 5 — replaced by smart auto-verify in P1.]** The original
plan deferred `--verify` chaining to P2. Rev 5 supersedes that: `records add`
/ `records update` / `records delete` get **always-on smart auto-verify**
in P1 (see §3 example outputs and §5 `Route53__Smart_Verify`). The smart
layer is cache-pollution-aware: it auto-runs a curated EU+US public-resolver
fan-out only on the safe case (a brand-new name with no prior recursive
cache), and silently skips public-resolver on upserts / deletes (where the
prior record's TTL would lock in stale answers), surfacing the wait time
in an info line. `--no-verify` opts out for scripted runs; `--verify-public`
forces the public-resolver check on the change/delete paths (with the
WARNING banner). The standalone `records check` command remains unchanged.

### Q9 — Future cert path: HTTP-01 (with downtime) vs DNS-01 (no downtime)? (NEW — rev 6)

The §12 ADDENDUM proposes a future per-instance cert workflow (Path A — own
cert sidecar reusing `sg_compute/platforms/tls/Cert__ACME__Client`). Today
that client is **HTTP-01 only** — verified by reading the file:

- `Cert__ACME__Client.select_http01(order)` hard-codes the
  `isinstance(challb.chall, challenges.HTTP01)` filter — no DNS-01 branch.
- `ACME__Challenge__Server` binds `:80` directly and serves the
  `/.well-known/acme-challenge/<token>` path — purely HTTP-01.
- `Schema__ACME__Config.challenge_port: int = 80` — the field name and
  default confirm an HTTP-only design.
- `cert_init._run_letsencrypt_ip(...)` resolves a *public IP* (not a
  hostname) and issues an IP-anchored cert with the LE `shortlived`
  profile — no concept of an FQDN target, no DNS provider plumbing.

That means a future hostname-anchored re-cert flow has two implementation
choices. The trade-off the user must resolve before Dev picks up §12:

| Opt | Position |
|-----|----------|
| **A** | **Keep HTTP-01.** Stop the main service container on :443, run the cert sidecar binding :80 (the sidecar runs the unchanged `ACME__Challenge__Server`), restart the main container with the new cert. Brief downtime (~10-20s per renewal). Smallest delta to existing code: `Cert__ACME__Client.build_csr` swaps `ipaddrs=[…]` for a hostname `domains=[…]` SAN; everything else stays. |
| **B** | **Add DNS-01 to `Cert__ACME__Client`.** New `select_dns01(order)` branch, new `Cert__ACME__Client.issue_for_hostname(hostname, ...)` method, new `Route53__AWS__Client.upsert_record(...)` call to publish the `_acme-challenge.<fqdn> TXT <key-auth>` record, poll for propagation against the authoritative NS set (we already have that helper — `Route53__Authoritative__Checker`), call `acme_client.answer_challenge`, then delete the TXT record. **Zero downtime** — the main service keeps serving on :443 the whole time. Adds the DNS-01 surface to `Cert__ACME__Client` (~50-80 LoC) and pulls `Route53__AWS__Client` into a TLS-pipeline dependency. |

**Architect recommendation: B** — DNS-01 — for these reasons:

1. **No downtime.** Vault-app HTTPS keeps serving the whole time. For an
   operator running these stacks regularly, even a 10-20s blackout per
   renewal is a foot-gun against "this is a live tool".
2. **Plays nicely with the rest of this brief.** The `Route53__AWS__Client`
   primitive that P1 ships already has `upsert_record` and `delete_record`;
   DNS-01 is the natural consumer. The `Route53__Authoritative__Checker`
   from P1 is exactly what's needed to confirm propagation before calling
   `answer_challenge` (avoids the LE-side validation flake mode).
3. **Wildcard becomes possible.** DNS-01 is the only challenge type that
   can issue `*.dev.sgraph.ai`-style wildcards. Not P1 / P2 but a real
   long-term option.
4. **Code surface is small.** ~50-80 LoC added to `Cert__ACME__Client`;
   nothing torn down. The HTTP-01 branch stays for the IP-cert path
   (the boot-time cert in vault-app today is happy with HTTP-01 + IP-anchored).

Trade-off (against the rec): pulls `Route53__AWS__Client` into the TLS pipeline,
which couples cert renewal to AWS account credentials being present in the
sidecar. The current HTTP-01 sidecar has no AWS credential requirement.
Mitigation: scope the IAM role attached to the sidecar to
`route53:ChangeResourceRecordSets` on **one specific hosted zone** + 
`route53:GetChange` — the same scope the rest of this brief already requires.

**Decision still pending user sign-off.** Both options live behind the §12
ADDENDUM (NOT in P1, NOT in P2) — Q9 resolves only when the cert workflow
slice is greenlit. Marked **PENDING** in §11.

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
    │   │   ├── Route53__AWS__Client.py            (sole boto3 boundary — NEW)
    │   │   ├── Dig__Runner.py                     (NEW — single subprocess transport: wraps `subprocess.run(['dig', …])`, pins `LC_ALL=C`, parses `+short` output; sole boundary to the `dig` binary; consumed by all three checkers; no library import on the DNS-on-the-wire path)
    │   │   ├── Route53__Authoritative__Checker.py     (NEW — DEFAULT mode; `Route53__AWS__Client.get_hosted_zone` for the NS set, then `Dig__Runner` invoked once per authoritative NS with `@<ns> +norecurse`; ZERO cache pollution)
    │   │   ├── Route53__Public_Resolver__Checker.py   (NEW — `--public-resolvers` opt-in; per-resolver `Dig__Runner` calls with `@<resolver-ip>`; cache-polluting)
    │   │   ├── Route53__Local__Checker.py             (NEW — `--local` opt-in; `Dig__Runner` with no `@<ns>` argument so the host's upstream resolver is used; cache-polluting)
    │   │   ├── Route53__Check__Orchestrator.py        (NEW — composes the three checkers per flags; emits one Schema__Dns__Check__Result)
    │   │   ├── Route53__Smart_Verify.py               (NEW — owns the new-vs-existing decision logic on `records add` / `update` / `delete`. Reads prior-record TTL via `Route53__AWS__Client.get_record(...)` BEFORE mutation; routes to authoritative-only (skip public-resolver) on upsert / delete with TTL-aware info line, or to authoritative + curated 6-resolver public-resolver fan-out on the safe new-name path. Consumes `Route53__Check__Orchestrator`.)
    │   │   ├── Route53__Zone__Resolver.py             (NEW — rev 6 — deepest-suffix-match resolver for `--name` when `--zone` is omitted. Lists hosted zones once per process via `Route53__AWS__Client.list_hosted_zones()`, caches them, and walks an FQDN's labels deepest-first to pick the longest-matching owning zone. Surfaces `Route53__Zone__Not_Found` when nothing matches.)
    │   │   └── Route53__Instance__Linker.py           (NEW — rev 6 — instance → public IP resolver for `dns instance create-record`. Accepts an EC2 instance-id (`i-…`), a stack name (resolved via the per-spec `info` helpers under `sg_compute_specs/{vault_app,playwright,elastic,neko}/cli/`), or the `--latest` sentinel (most recently launched EC2 instance carrying the SG-AI tag). Returns a `Schema__Instance__Resolution` with instance-id, public IPv4, stack-name (when known), and `Name`-tag (when set). Consumes a thin `EC2__AWS__Client` boto3 boundary scoped to `ec2:DescribeInstances` / `ec2:DescribeTags`.)
    │   ├── schemas/
    │   │   ├── __init__.py                    (empty)
    │   │   ├── Schema__Route53__Hosted_Zone.py
    │   │   ├── Schema__Route53__Record.py
    │   │   ├── Schema__Route53__Record__Alias.py   (lib-only — no CLI surface; consumed by CF+R53 brief)
    │   │   ├── Schema__Route53__Change__Result.py
    │   │   ├── Schema__Route53__Zone__List.py
    │   │   ├── Schema__Dns__Check__Result.py        (NEW — propagation-check output)
    │   │   ├── Schema__Dig__Result.py               (NEW — raw `Dig__Runner.run` result)
    │   │   ├── Schema__Smart_Verify__Decision.py    (NEW — pre-flight decision for `records add`/`update`/`delete`)
    │   │   ├── Schema__Smart_Verify__Result.py      (NEW — post-mutation verify result, including the skip info-line text)
    │   │   ├── Schema__Instance__Resolution.py      (NEW — rev 6 — output of `Route53__Instance__Linker.resolve(...)`; carries `instance_id`, `public_ipv4` (Safe_Str__IPv4), `stack_name` (Optional), `name_tag` (Optional), `resolution_source` (Enum: `INSTANCE_ID` / `STACK_NAME` / `LATEST`))
    │   │   └── Schema__Instance__Create_Record__Result.py  (NEW — rev 6 — composite result of the `instance create-record` flow; fields: `resolution` (Schema__Instance__Resolution), `derived_name` (Safe_Str__Record_Name), `zone` (Schema__Route53__Hosted_Zone), `change_result` (Schema__Route53__Change__Result, populated when an upsert ran), `was_idempotent_no_op` (bool — true when the name already pointed at the right IP), `smart_verify_result` (Schema__Smart_Verify__Result, populated when `--verify` was on))
    │   ├── enums/
    │   │   ├── __init__.py                    (empty)
    │   │   ├── Enum__Route53__Record_Type.py
    │   │   ├── Enum__Dns__Resolver.py             (NEW — curated public-resolver set; flags the 6-member smart-verify subset)
    │   │   ├── Enum__Dns__Check__Mode.py          (NEW — AUTHORITATIVE | PUBLIC_RESOLVERS | LOCAL)
    │   │   ├── Enum__Smart_Verify__Decision.py    (NEW — NEW_NAME | UPSERT | DELETE)
    │   │   └── Enum__Instance__Resolution__Source.py (NEW — rev 6 — INSTANCE_ID | STACK_NAME | LATEST)
    │   ├── primitives/
    │   │   ├── __init__.py                    (empty)
    │   │   ├── Safe_Str__Hosted_Zone_Id.py
    │   │   ├── Safe_Str__Domain_Name.py
    │   │   ├── Safe_Str__Record_Name.py
    │   │   ├── Safe_Str__Record_Value.py
    │   │   ├── Safe_Str__Resolver_IP.py            (NEW — IPv4/IPv6 of a public resolver)
    │   │   ├── Safe_Str__IPv4.py                    (NEW — rev 6 — IPv4 dotted-quad; validated with `ipaddress.IPv4Address` at construction. Used by `Schema__Instance__Resolution.public_ipv4` and on the A-record value path.)
    │   │   ├── Safe_Str__Instance_Id.py             (NEW — rev 6 — `i-` followed by 8 or 17 lowercase-hex chars — the two EC2 instance-id shapes AWS still emits)
    │   │   └── Safe_Int__TTL.py
    │   └── collections/
    │       ├── __init__.py                    (empty)
    │       ├── List__Schema__Route53__Hosted_Zone.py
    │       ├── List__Schema__Route53__Record.py
    │       └── List__Schema__Dns__Check__Resolver_Result.py  (NEW — per-resolver rows)
    │
    ├── ec2/                                   (NEW — rev 6)
    │   ├── __init__.py                        (empty)
    │   └── service/
    │       ├── __init__.py                    (empty)
    │       └── EC2__AWS__Client.py            (NEW — sole boto3 boundary for the narrow EC2 surface this brief needs: `describe_instances` for instance-id lookup, `describe_instances` filtered by `tag:Name` / `tag:sg-ai` for stack-name and `--latest` lookups, `describe_tags` for the Name-tag derivation path. Consumed by `Route53__Instance__Linker`. Same narrow-exception template as `Route53__AWS__Client` / `ACM__AWS__Client`. Note: a larger `sg aws ec2` CLI surface is OUT OF SCOPE for this brief — this client exists solely to feed `dns instance create-record`.)
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
        │   ├── test_Dig__Runner.py
        │   ├── test_Route53__Authoritative__Checker.py
        │   ├── test_Route53__Public_Resolver__Checker.py
        │   ├── test_Route53__Local__Checker.py
        │   ├── test_Route53__Check__Orchestrator.py
        │   ├── test_Route53__Smart_Verify.py
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
  ┌────────────────────┐ ┌────────────────────────────────┐  ┌────────────────────────┐
  │ Route53__AWS__     │ │ Route53__Check__Orchestrator    │  │ ACM__AWS__Client       │
  │ Client             │ │ ─ gates cache-polluting modes   │  │ ─ sole boto3 boundary  │
  │ ─ sole boto3       │ │   behind WARNING banner + y/N   │  │ ─ list_certificates    │
  │   boundary R53     │ │ ─ composes the three checkers   │  │ ─ describe_certificate │
  │ ─ default-zone     │ │ ─ unified exit-code mapping     │  │ ─ dual-region helper   │
  │   sgraph.ai cache  │ │                                 │  │                        │
  └──────┬─────────────┘ └─────┬────┬────────────┬──────────┘  └──────┬─────────────────┘
         │                     │    │            │                    │
         │           ┌─────────┘    │            └─────────┐          │
         │           ▼              ▼                      ▼          │
         │   ┌───────────────┐ ┌─────────────────────┐ ┌────────────┐ │
         │   │ Route53__     │ │ Route53__           │ │ Route53__  │ │
         │   │ Authoritative │ │ Public_Resolver__   │ │ Local__    │ │
         │   │ __Checker     │ │ Checker             │ │ Checker    │ │
         │   │ (DEFAULT)     │ │ (OPT-IN; warning)   │ │ (OPT-IN;   │ │
         │   │ ─ Dig__Runner │ │ ─ Dig__Runner per   │ │  warning)  │ │
         │   │   @<ns>       │ │   resolver IP       │ │ ─ Dig__    │ │
         │   │   +norecurse  │ │ ─ 6/8-resolver fan  │ │   Runner   │ │
         │   │ ─ zero cache  │ │ ─ thread pool       │ │   no @<ns> │ │
         │   │   pollution   │ │ ─ quorum logic      │ │ ─ host     │ │
         │   │               │ │ ─ CACHE-POLLUTING   │ │   upstream │ │
         │   │               │ │   at each resolver  │ │ ─ CACHE-   │ │
         │   │               │ │                     │ │   POLLUT.  │ │
         │   └───────┬───────┘ └─────────┬───────────┘ └─────┬──────┘ │
         ▼           ▼                   ▼                   ▼        ▼
  ┌────────────────────────────────────────────────────────────────────┐
  │ boto3 route53 / acm clients   +   Dig__Runner ─► `dig` subprocess  │
  │  (documented narrow boto3 exception; NO dnspython dependency       │
  │   per Q7 RESOLVED — `dig` shell-out via the shared Dig__Runner is  │
  │   the single DNS-on-the-wire transport for all three checkers)     │
  └────────────────────────────────────────────────────────────────────┘
```

The CLI **never** touches boto3 directly. Only `Route53__AWS__Client` and
`ACM__AWS__Client` do. The three checkers are the only DNS-on-the-wire /
shell-out boundary, each explicitly scoped to one mode. The orchestrator is
the only class allowed to compose them and the only class that owns the
WARNING-banner / y/N gate for the cache-polluting modes.

Tests substitute in-memory subclasses (`Route53__AWS__Client__In_Memory`,
`ACM__AWS__Client__In_Memory`, `Route53__Authoritative__Checker__In_Memory`,
`Route53__Public_Resolver__Checker__In_Memory`,
`Route53__Local__Checker__In_Memory`) following the exact
`Elastic__AWS__Client__In_Memory` precedent — no `mock`, no `patch`.

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

### Checker method surface (three classes + orchestrator)

**`Route53__Authoritative__Checker`** (P1 — DEFAULT):

| Method | Implementation | Notes |
|--------|----------------|-------|
| `check(zone_id, name, record_type, expected_value) -> Schema__Dns__Check__Result` | `Route53__AWS__Client.get_hosted_zone(zone_id)` to fetch the NS set, then `Dig__Runner.run(args=['@<ns>', '+norecurse', '+short', name, record_type])` once per authoritative NS. Parallel via `concurrent.futures.ThreadPoolExecutor`. No library import on the DNS-on-the-wire path. | **Zero cache pollution.** Returns one row per Route 53 NS (typically 4). PASS iff every NS matches `expected_value`. Exit-code 0 on pass, 1 on any disagreement. |

**`Route53__Public_Resolver__Checker`** (P1.5 / P2 — OPT-IN):

| Method | Implementation | Notes |
|--------|----------------|-------|
| `check(name, record_type, expected_value, min_resolvers=5) -> Schema__Dns__Check__Result` | `Dig__Runner.run(args=['@<resolver-ip>', '+short', name, record_type])` per resolver over the 8-resolver `Enum__Dns__Resolver` set (full standalone mode) or the 6-resolver curated EU+US subset (smart auto-verify new-name mode); parallel via `concurrent.futures.ThreadPoolExecutor`; ~3s per-resolver timeout (enforced via `Dig__Runner` subprocess timeout). | **Cache-polluting.** Quorum logic; returns per-resolver rows + summary. Orchestrator MUST have printed the WARNING banner before calling (standalone path). Smart-verify new-name path skips the banner because the safety argument holds by construction. |

**`Route53__Local__Checker`** (P1.5 / P2 — OPT-IN):

| Method | Implementation | Notes |
|--------|----------------|-------|
| `check(name, record_type, expected_value) -> Schema__Dns__Check__Result` | `Dig__Runner.run(args=['+short', name, record_type])` — no `@<ns>` (uses host's configured upstream). | **Cache-polluting** at the host's upstream. No `--flush-local` sub-option — operator flushes manually with platform-native tooling. `Dig__Runner` surfaces `FileNotFoundError` for missing `dig` cleanly (returns `local_answer=null`, exit 3 only if `--local` was explicitly requested). |

**`Route53__Check__Orchestrator`** (P1; gains `--public-resolvers` and `--local` wiring in P1.5 / P2):

| Method | Implementation | Notes |
|--------|----------------|-------|
| `run(zone_id, name, record_type, expected_value, modes: Set[Enum__Dns__Check__Mode], min_resolvers=5, yes=False) -> Schema__Dns__Check__Result` | For each mode in the input set, prints the WARNING banner + y/N (unless `yes=True`) for cache-polluting modes, then invokes the relevant checker. Merges per-row results into a single `Schema__Dns__Check__Result`. | Owns the unified exit-code mapping (0 / 1 / 2 / 3). First-failing-mode wins for the exit-code report (authoritative-fail trumps public-quorum-fail trumps local-mismatch). |

### `Route53__Smart_Verify` method surface (P1 — owns the new-vs-existing decision)

| Method | Implementation | Notes |
|--------|----------------|-------|
| `decide_before_add(zone_id, name, record_type) -> Schema__Smart_Verify__Decision` | Calls `Route53__AWS__Client.get_record(zone_id, name, record_type)` BEFORE the mutation. If the record does not exist → returns `decision=NEW_NAME`, `prior_ttl=None`, `prior_values=[]`. If it exists → returns `decision=UPSERT`, `prior_ttl=<ttl>`, `prior_values=[…]`. | Pure pre-flight read; no mutation. Surfaces the pre-flight line shown in §3 examples. |
| `decide_before_update(zone_id, name, record_type) -> Schema__Smart_Verify__Decision` | Reads prior record; always returns `decision=UPSERT` (an update with no prior is treated as an error and rejected earlier in the CLI flow). | TTL value populated for the skip info line. |
| `decide_before_delete(zone_id, name, record_type) -> Schema__Smart_Verify__Decision` | Reads prior record; always returns `decision=DELETE` with `prior_ttl` populated; error if record does not exist. | TTL drives the "recursives may still serve cached answer for up to ~Ns" info line. |
| `verify_after_mutation(decision: Schema__Smart_Verify__Decision, zone_id, name, record_type, expected_value, force_public=False, no_verify=False) -> Schema__Smart_Verify__Result` | Dispatches on `decision`. **NEW_NAME** → invokes orchestrator with `{AUTHORITATIVE, PUBLIC_RESOLVERS}` and the curated 6-resolver EU+US subset (no WARNING banner — safety is structural). **UPSERT** → invokes orchestrator with `{AUTHORITATIVE}` only; emits the upsert skip info line quoting `decision.prior_ttl`; if `force_public=True`, also runs the standalone public-resolver path WITH the WARNING banner. **DELETE** → invokes orchestrator with `{AUTHORITATIVE}` only (expecting NXDOMAIN); emits the delete skip info line quoting `decision.prior_ttl`; `force_public=True` honoured the same way. `no_verify=True` skips all verification entirely (scripted-mode opt-out). | Consumes `Route53__Check__Orchestrator`. The curated 6-resolver set is a property of `Enum__Dns__Resolver` (members tagged `IN_SMART_VERIFY_NEW_NAME = True`). |

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
| `Dig__Runner.py` | **Single subprocess transport for every DNS-on-the-wire query in this brief.** Wraps `subprocess.run(['dig', …])` with `env={'LC_ALL': 'C', …}`, captures stdout / stderr, surfaces non-zero exit codes cleanly, and parses `+short` output (one value per line; empty stdout → NXDOMAIN / no-answer). Methods: `run(args: List[str], timeout: int = 3) -> Schema__Dig__Result` (raw), `query_short(server: Optional[str], name: str, record_type: str, no_recurse: bool = False, timeout: int = 3) -> List[Safe_Str__Record_Value]` (convenience). All three checkers consume this helper — no other class is allowed to invoke `dig`. No library import. `FileNotFoundError` for missing `dig` is surfaced cleanly so callers can degrade gracefully. **P1.** |
| `Route53__Authoritative__Checker.py` | **DEFAULT mode of `records check`.** Given a zone id, fetches the NS set via `Route53__AWS__Client.get_hosted_zone(...)`, then invokes `Dig__Runner` once per authoritative NS with `@<ns> +norecurse` to issue the A / AAAA / etc query directly. No library import, no cache layer. Returns one row per Route 53 NS (typically 4 rows). **Zero cache pollution anywhere** — these nameservers are the source of truth and have no upstream cache. Fails (exit 1) if any NS disagrees. **P1.** |
| `Route53__Public_Resolver__Checker.py` | **`--public-resolvers` mode.** The whatsmydns.net-style fan-out across either the curated 8-resolver public set (`Enum__Dns__Resolver`, full standalone mode) or the 6-resolver smart-verify subset (new-name auto-verify mode). Per-resolver `Dig__Runner` calls with `@<resolver-ip>`, `concurrent.futures.ThreadPoolExecutor` for parallelism, ~3s per-resolver timeout (enforced via subprocess timeout). Quorum logic via `--min-resolvers`. **Cache-polluting** at each public resolver — the orchestrator MUST print the WARNING banner (and consume y/N confirmation unless `--yes`) before invoking this checker on the standalone path. The smart-verify new-name path is exempt (no banner) because no prior recursive cache exists for the name. **P1 (new-name auto-verify path) / P1.5 (standalone `--public-resolvers` flag).** |
| `Route53__Local__Checker.py` | **`--local` mode.** Calls `Dig__Runner` with no `@<ns>` argument so the host's configured upstream resolver is used. Sole class allowed to call into `Dig__Runner` for the local path. **Cache-polluting** at the host's upstream (often a corporate proxy / VPN resolver). The orchestrator MUST print the WARNING banner before invoking. No `--flush-local` sub-option — platform-native cache flushing is left to the operator. **P1.5 / P2.** |
| `Route53__Check__Orchestrator.py` | Thin composer. Reads the three mode flags (`--authoritative` default-on, `--public-resolvers`, `--local`, `--all`), gates each cache-polluting mode behind its WARNING banner + y/N confirmation, then invokes the relevant checker(s) and merges their per-row results into a single `Schema__Dns__Check__Result`. Computes the unified exit code (0 = all selected passed, 1 = authoritative disagreement, 2 = public-resolvers quorum failed, 3 = local mismatch — first-failing-mode wins for the exit-code report). |
| `Route53__Smart_Verify.py` | **Owns the new-vs-existing decision logic on `records add` / `update` / `delete`.** Calls `Route53__AWS__Client.get_record(...)` BEFORE the mutation to detect whether the name + type is currently in the zone, and (when present) reads the existing TTL so the skip info line can quote a wait time. After mutation, dispatches to `Route53__Check__Orchestrator`: new-name path runs `{AUTHORITATIVE, PUBLIC_RESOLVERS}` with the curated 6-resolver subset (safe by construction, no banner); upsert / delete paths run `{AUTHORITATIVE}` only and emit the appropriate TTL-aware skip info line. Honours `--no-verify` (skip everything) and `--verify-public` (force public-resolver check on the change/delete paths WITH the WARNING banner). **P1.** |
| `Route53__Zone__Resolver.py` | **NEW — rev 6.** Deepest-suffix-match resolver. Lists hosted zones once via `Route53__AWS__Client.list_hosted_zones()`, caches them on the instance, then resolves an FQDN by walking labels deepest-first: for `my-ec2-1.dev.sgraph.ai`, tries `my-ec2-1.dev.sgraph.ai` (full match — rare; happens only when an apex matches), then `dev.sgraph.ai`, then `sgraph.ai`, then `ai`, returning the first match found. Method surface: `resolve_zone_for_name(fqdn: Safe_Str__Record_Name) -> Schema__Route53__Hosted_Zone` (raises `Route53__Zone__Not_Found` on no match), `enforce_containment(fqdn, explicit_zone) -> None` (used when `--zone` is passed — raises `Route53__Zone__Containment_Error` if the FQDN does not end with the zone name). Trailing-dot normalisation is applied to both sides. **P1.** |
| `Route53__Instance__Linker.py` | **NEW — rev 6.** EC2 instance → public IPv4 resolver consumed by `dns instance create-record`. Method surface: `resolve(instance_token: str, latest: bool = False) -> Schema__Instance__Resolution`. Branches: (a) `latest=True` → `EC2__AWS__Client.list_instances_by_tag('sg-ai', '*')`, sorts by `LaunchTime` descending, picks the most recent `running` instance, source=`LATEST`. (b) `instance_token` matches `Safe_Str__Instance_Id` regex (`^i-[0-9a-f]{8,17}$`) → `EC2__AWS__Client.describe_instance(instance_id)`, source=`INSTANCE_ID`. (c) otherwise treat as stack-name → call the per-spec `info` helper (`from sg_compute_specs.vault_app.cli.Cli__Vault_App import resolve_instance_for_stack` and the three siblings; tried in order vault_app → playwright → elastic → neko, first match wins; ambiguous match across specs raises with the list), source=`STACK_NAME`. Public IPv4 is always read from `Instance.PublicIpAddress`; raises `Route53__Instance__No_Public_IP` when the field is empty (instance is stopped / has no EIP). Name-tag is read from `Instance.Tags[Name]` for the `derive_record_name(...)` helper that backs the `--name` default. **P1.** |
| `EC2__AWS__Client.py` | **NEW — rev 6 — under `sgraph_ai_service_playwright__cli/aws/ec2/service/`.** Sole boto3 boundary for the narrow EC2 surface this brief needs. Methods: `describe_instance(instance_id) -> Schema__EC2__Instance` (single-instance `describe_instances` call with `InstanceIds=[...]`), `list_instances_by_tag(tag_key, tag_value, only_running=True) -> List[Schema__EC2__Instance]` (`describe_instances` paginator with `Filters=[{Name: tag:<k>, Values: [<v>]}]` + state filter), `describe_tags_for_instance(instance_id) -> Dict[Safe_Str, Safe_Str]` (used for the Name-tag derivation). Same narrow-exception template as `Route53__AWS__Client` / `ACM__AWS__Client`. `Schema__EC2__Instance` carries `instance_id`, `state`, `public_ipv4` (Optional Safe_Str__IPv4), `launch_time` (Safe_Str__ISO), `tags` (Dict). **P1.** |

**`sgraph_ai_service_playwright__cli/aws/dns/schemas/`** (one class per file — rule #21)

| File | One-line purpose |
|------|-------------------|
| `Schema__Route53__Hosted_Zone.py` | `zone_id`, `name`, `private`, `record_count`, `comment`, `name_servers` (List). |
| `Schema__Route53__Record.py` | `name`, `type` (Enum), `ttl`, `values` (List), `set_identifier`, `alias` (Optional). |
| `Schema__Route53__Record__Alias.py` | `hosted_zone_id`, `dns_name`, `evaluate_target_health`. Library-only schema consumed by CF+R53 brief — no CLI command surfaces it. |
| `Schema__Route53__Change__Result.py` | `change_id`, `status`, `submitted_at` (Safe_Str__ISO datetime). |
| `Schema__Route53__Zone__List.py` | `account_id`, `zones` (List__Schema__Route53__Hosted_Zone). |
| `Schema__Dns__Check__Result.py` | `name`, `record_type`, `expected_value`, `resolvers` (List of per-resolver rows: resolver enum, IP, geo, answer, match-bool), `local_answer`, `local_match`, `quorum_required`, `quorum_met`, `exit_code`. |
| `Schema__Dig__Result.py` | Raw `Dig__Runner.run` output. Fields: `argv` (List[str]), `exit_code` (int), `stdout_lines` (List[str]), `stderr` (str), `duration_ms` (int). Pure data — no methods. |
| `Schema__Smart_Verify__Decision.py` | Pre-flight read result from `Route53__Smart_Verify.decide_before_*`. Fields: `decision` (Enum: `NEW_NAME` / `UPSERT` / `DELETE`), `prior_ttl` (Optional Safe_Int__TTL_Seconds), `prior_values` (List[Safe_Str__Record_Value]). |
| `Schema__Smart_Verify__Result.py` | Post-mutation verify result. Fields: `decision` (Enum, copied from `Schema__Smart_Verify__Decision`), `check_result` (Schema__Dns__Check__Result), `skip_info_line` (Optional Safe_Str — the upsert / delete skip line text, empty on the new-name path), `forced_public` (bool, true when `--verify-public` was passed). |
| `Schema__Instance__Resolution.py` | **NEW — rev 6.** Output of `Route53__Instance__Linker.resolve(...)`. Fields: `instance_id` (Safe_Str__Instance_Id), `public_ipv4` (Safe_Str__IPv4), `stack_name` (Optional Safe_Str — populated only when source=STACK_NAME or when a stack-tag is found on the instance), `name_tag` (Optional Safe_Str — verbatim `Name` tag if set), `resolution_source` (Enum__Instance__Resolution__Source — INSTANCE_ID / STACK_NAME / LATEST), `launch_time` (Safe_Str__ISO). |
| `Schema__Instance__Create_Record__Result.py` | **NEW — rev 6.** Composite result of `dns instance create-record`. Fields: `resolution` (Schema__Instance__Resolution), `derived_name` (Safe_Str__Record_Name), `zone` (Schema__Route53__Hosted_Zone), `change_result` (Optional Schema__Route53__Change__Result — None on the idempotent no-op path), `was_idempotent_no_op` (bool — true when the name already pointed at the right IP and no upsert ran), `smart_verify_result` (Optional Schema__Smart_Verify__Result — populated when `--verify` was on), `cert_warning_emitted` (bool — true when the post-success cert-warning block was printed). |

**`sgraph_ai_service_playwright__cli/aws/dns/enums/`**

| File | One-line purpose |
|------|-------------------|
| `Enum__Route53__Record_Type.py` | `A`, `AAAA`, `CNAME`, `MX`, `TXT`, `NS`, `SOA`, `PTR`, `SRV`, `CAA` (alias-* members deferred — no CLI command; `Schema__Route53__Record__Alias` carries the alias data when needed). |
| `Enum__Dns__Resolver.py` | Curated public-resolver list. Each member carries: name, IP, geo, AND `in_smart_verify_new_name` (bool). Full 8-resolver set used by the standalone `--public-resolvers` flag: `GOOGLE_PRIMARY` (8.8.8.8 US, smart=true), `GOOGLE_SECONDARY` (8.8.4.4 EU, smart=true), `CLOUDFLARE_PRIMARY` (1.1.1.1 US-anycast, smart=true), `CLOUDFLARE_SECONDARY` (1.0.0.1 EU-anycast, smart=true), `QUAD9` (9.9.9.9 global anycast, smart=true), `OPENDNS` (208.67.222.222 US, smart=false), `YANDEX` (77.88.8.8 RU, smart=false), `ADGUARD_EU` (94.140.14.14 EU, smart=true). The smart-verify subset is the 6 members with `smart=true`. `--min-resolvers` defaults to 5 (standalone path); smart-verify new-name path uses 6/6 for the displayed quorum but does not fail on a single drop (info-line only). |
| `Enum__Dns__Check__Mode.py` | The three `records check` modes. Members: `AUTHORITATIVE` (default), `PUBLIC_RESOLVERS`, `LOCAL`. Used as a set (not a Literal) on the orchestrator's input shape and on `Schema__Dns__Check__Result.modes_run` so the rendered table can show which modes actually ran. |
| `Enum__Smart_Verify__Decision.py` | The decision computed by `Route53__Smart_Verify.decide_before_*`. Members: `NEW_NAME` (record did not exist before this `records add` — public-resolver fan-out is safe), `UPSERT` (`records add` / `update` with a prior record — skip public-resolver), `DELETE` (`records delete` — skip public-resolver, expect NXDOMAIN). |
| `Enum__Instance__Resolution__Source.py` | **NEW — rev 6.** How `Route53__Instance__Linker.resolve(...)` arrived at the instance. Members: `INSTANCE_ID` (token matched `Safe_Str__Instance_Id`), `STACK_NAME` (token matched a known per-spec stack-name via one of the `info` helpers), `LATEST` (`--latest` sentinel — most recently launched `running` instance with the SG-AI tag). |

**`sgraph_ai_service_playwright__cli/aws/dns/primitives/`** (one class per file)

| File | One-line purpose |
|------|-------------------|
| `Safe_Str__Hosted_Zone_Id.py` | `Z` + 1..32 alphanumerics (Route 53 allocates uppercase alphanumeric). Regex-validated. |
| `Safe_Str__Domain_Name.py` | RFC-1035-ish: lowercase, dots, hyphens; trailing dot tolerated and normalised. Max length 255. |
| `Safe_Str__Record_Name.py` | **Updated for rev 6: permissive multi-label RFC-1035 regex.** Accepts arbitrary-depth FQDNs (e.g. `my-ec2-1.dev.sgraph.ai`) — the regex `^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$` matches a sequence of RFC-1035 labels joined by dots. Total length capped at 253 (RFC 1035). Trailing dot tolerated and normalised. Empty labels rejected. The single-label form (`zen-darwin`) is still accepted — falls under the optional left-hand group. Semantically the record's own FQDN; consumed by every CLI flag, by `Route53__Zone__Resolver.resolve_zone_for_name`, and by the `instance create-record` derived-name helper. |
| `Safe_Str__Record_Value.py` | String, max length 4000 (TXT records hard cap); CLI splits on quotes for TXT. |
| `Safe_Str__Resolver_IP.py` | IPv4 dotted-quad or compressed IPv6, validated with `ipaddress` stdlib at construction time. Used by `Enum__Dns__Resolver` member payloads and as the `resolver_ip` field on per-resolver result rows. |
| `Safe_Str__IPv4.py` | **NEW — rev 6.** IPv4 dotted-quad only (no IPv6), validated with `ipaddress.IPv4Address(value)` at construction. Used by `Schema__Instance__Resolution.public_ipv4` and reused as the A-record value type when an A-record is being created. Narrower than `Safe_Str__Resolver_IP` (which also accepts IPv6) because the EC2 `PublicIpAddress` field is IPv4-only and A records are IPv4-only by RFC. |
| `Safe_Str__Instance_Id.py` | **NEW — rev 6.** EC2 instance-id regex `^i-[0-9a-f]{8,17}$` — covers both the legacy 8-char shape and the modern 17-char shape AWS still emits. Used by `Route53__Instance__Linker.resolve(...)` to decide whether a positional token is an instance-id (regex match) or a stack name (no match). |
| `Safe_Int__TTL.py` | Range 0..2147483647 (Route 53 hard limit); validated 1..86400 in practice. Also used as the `prior_ttl` type on `Schema__Smart_Verify__Decision` so the upsert / delete skip info lines can quote a TTL-aware wait time. Alias-name `Safe_Int__TTL_Seconds` is not introduced — the existing `Safe_Int__TTL` primitive covers the same semantic space and reusing it avoids duplication. |

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
| `Cli__Aws_Dns.py` | Typer `dns` app with sub-groups `zones`, `records`, AND (rev 6) `instance`. Imports `Route53__AWS__Client`, `Route53__Check__Orchestrator` (which in turn composes the three checker classes), `Route53__Zone__Resolver`, and `Route53__Instance__Linker`. Default-zone resolution lives here (calls `Route53__AWS__Client.resolve_default_zone()` when `--zone` unset; when `--name` is a multi-label FQDN the resolver picks the deepest owning zone). The `records check` command parses the mode flags into a `Set[Enum__Dns__Check__Mode]` and hands them to the orchestrator; the orchestrator is responsible for printing the cache-pollution WARNING banners and prompting y/N before invoking any cache-polluting checker. The `instance create-record` command (rev 6) wires together `Route53__Instance__Linker.resolve(...)` → `derive_record_name(...)` → `Route53__Zone__Resolver.resolve_zone_for_name(...)` → idempotency check (compare against `Route53__AWS__Client.get_record(...)`; same-IP → exit 0 no-op, different-IP without `--force` → fail) → `Route53__AWS__Client.create_record(...)` → `Route53__Smart_Verify.verify_after_mutation(...)` (new-name path) → cert-warning info block. Renderers (`_render_zones_list`, `_render_records_list`, `_render_change_result`, `_render_check_result`, `_render_instance_create_record_result`) using `rich.Table` + Console — mirrors `Cli__Vault_App.py`'s `_render_vault_app_info` / `_render_vault_app_create` style. `--json` flag swaps the renderer for `console.print_json(data=schema.json())`. |
| `Cli__Aws_Acm.py` | Typer `acm` app with `list` and `show` subcommands. Imports `ACM__AWS__Client`. Dual-region default behaviour for `list`; ARN-derived region for `show`. Renderers (`_render_acm_list`, `_render_acm_show`) match the rich style. |

### New files (proposed) — tests

**`sgraph_ai_service_playwright__cli/aws/tests/`**

| File | One-line purpose |
|------|-------------------|
| `service/test_Route53__AWS__Client.py` | Composition tests against `Route53__AWS__Client__In_Memory` — method signatures, schema shapes, change-set construction, `resolve_default_zone()` caching, multi-page pagination. No boto3 hit. |
| `service/test_Route53__Authoritative__Checker.py` | Tests against `Route53__Authoritative__Checker__In_Memory` (in-memory fake fetching a canned NS set + canned per-NS answers). Assert: returns one row per Route 53 NS; all-agree → PASS (exit 0); one disagreement → FAIL (exit 1); zero cache pollution claim is structural (no public-resolver IPs ever touched). |
| `service/test_Route53__Public_Resolver__Checker.py` | Tests against `Route53__Public_Resolver__Checker__In_Memory`. Assert: quorum-met when 5/8 match (default), quorum-failed when 4/8 match (and `--min-resolvers 5`), per-resolver row shape stable. |
| `service/test_Route53__Local__Checker.py` | Tests against `Route53__Local__Checker__In_Memory` (`subprocess.run` replaced by a fake invokable returning canned `dig` output — composition, no `mock.patch`). Assert: match → PASS, mismatch → exit 3, `FileNotFoundError` from missing `dig` degrades cleanly. |
| `service/test_Route53__Check__Orchestrator.py` | Tests against an orchestrator wired to the three `__In_Memory` checkers. Assert: default mode-set is `{AUTHORITATIVE}`; `--public-resolvers` and `--local` cause the WARNING banner to be emitted (captured via injected `Console`) before the checker runs; `yes=True` skips the prompt; unified exit-code mapping is correct (auth-fail trumps public-quorum-fail trumps local-mismatch). |
| `service/test_ACM__AWS__Client.py` | Tests against `ACM__AWS__Client__In_Memory`. Dual-region scan dedupes when current = us-east-1, ARN-region auto-detection, `--all-regions` loop hits the expected region list. |
| `cli/test_Cli__Aws_Dns.py` | CliRunner-based tests of the Typer surface — help text, subcommand existence, renderer output, `--json` shape, default-zone behaviour when `--zone` omitted. |
| `cli/test_Cli__Aws_Acm.py` | CliRunner-based tests — `list`, `show`, `--json` round-trip, dual-region default in the rendered output. |

### Existing files — changes

| File | Change |
|------|--------|
| `scripts/provision_ec2.py` (the top-level `sg` Typer root, line 769) | Add a new sub-app: `from sgraph_ai_service_playwright__cli.aws.cli.Cli__Aws import app as _aws_app` followed by `app.add_typer(_aws_app, name='aws')`. **Confirmed location** — pre-Dev audit complete. |
| `pyproject.toml` | **No change** (Q7 RESOLVED — no `dnspython` dependency added; `dig` shell-out via the shared `Dig__Runner` is the single DNS-on-the-wire transport). |
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

### boto3 operations called by `EC2__AWS__Client` (NEW — rev 6)

| Method | boto3 client call | Read/Write |
|--------|-------------------|------------|
| `describe_instance(instance_id)` | `ec2:DescribeInstances` | R |
| `list_instances_by_tag(tag_key, tag_value)` | `ec2:DescribeInstances` (paginator + `Filters`) | R |
| `describe_tags_for_instance(instance_id)` | `ec2:DescribeTags` | R |

`ec2:DescribeTags` is covered by `ec2:DescribeInstances` for the common case
(the `Tags` field is on the instance shape) but the explicit `describe_tags`
call is retained for the Name-tag-only lookup so it can be IAM-scoped down if
desired. **`ec2:DescribeInstances` is the only net-new IAM action this rev
adds.**

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
- **`ec2:DescribeInstances`** (NEW — rev 6) — required by `dns instance create-record` for instance-id / stack-name / `--latest` resolution and to read the `PublicIpAddress` + `Tags[Name]` fields. Cannot be scoped to a single instance (the API is account-wide read-only); operators with stricter blast-radius requirements can attach an SCP / OU-level deny on EC2 mutations.
- **`ec2:DescribeTags`** (NEW — rev 6) — used by the Name-tag-only derivation path. Covered de facto by `ec2:DescribeInstances` but listed explicitly so the IAM policy can be split if desired.

**No `iam:*` / `cloudfront:*` permissions required. `ec2:*` is read-only and
narrow — exactly two actions (`DescribeInstances`, `DescribeTags`).**

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

### Host-side prerequisites (Q7 follow-up)

`Dig__Runner` shells out to `dig`. Every host that runs the CLI must therefore
have `dig` on `$PATH`. Coverage today:

- **Playwright Docker base image** (`mcr.microsoft.com/playwright/python:v1.58.0-noble`) — already ships `dnsutils` (which contains `dig`). No image change required.
- **Bare macOS / Linux dev hosts** — `dig` is almost always present (BIND tooling is a long-standing default on Debian/Ubuntu via `dnsutils`; on macOS it ships with the system). Operators on minimal Alpine containers or stripped-down environments are the only ones likely to hit a gap.
- **CI runners (GitHub Actions ubuntu-latest)** — ships `dig` by default.

**Failure mode.** `Dig__Runner` surfaces `FileNotFoundError` cleanly. The CLI
exits with a clear `dig not found on PATH — install dnsutils (Debian/Ubuntu) /
bind-tools (Alpine) or run from the Playwright Docker image` error. This is
asserted in `test_Dig__Runner.py`.

`route53:ListResourceRecordSets` is **already required** for `records list` /
`records get` and is therefore reused by `Route53__Smart_Verify.decide_before_*`
without any IAM-policy change (verified — see the boto3 operations table above).

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

### P1 — Record mutations + authoritative-mode `records check` + smart auto-verify

**Scope:** make the CLI an editing surface; add the standalone `records check`
limited to the **safe default mode** (authoritative-NS direct query); and ship
**smart auto-verify** on every mutation so the operator gets the right level of
verification by default without ever risking cache pollution.

1. `Route53__AWS__Client` gains `create_record`, `upsert_record`,
   `delete_record`, `upsert_a_alias_record` (library-only — no CLI command).
2. CLI subcommands shipped: `dns records add`, `dns records update`,
   `dns records delete`.
3. Confirmation prompts on `update` / `delete` (Q4-A).
4. `--yes` flag added.
5. `SG_AWS__DNS__ALLOW_MUTATIONS=1` env gate (Q4 safety net — locked in).
6. Diff preview in the confirmation prompt (show old → new).
7. `Dig__Runner` shipped (the single subprocess transport for every DNS query).
8. `Route53__Authoritative__Checker` shipped (DEFAULT mode), consuming `Dig__Runner`. **No `dnspython` dependency added** (Q7 RESOLVED).
9. `Route53__Public_Resolver__Checker` shipped (consuming `Dig__Runner`), but **only wired into the smart auto-verify new-name path** in P1 — the standalone `--public-resolvers` flag on `records check` remains gated until P1.5 (see point 12).
10. `Route53__Check__Orchestrator` shipped, wired to the authoritative checker
    AND to the public-resolver checker for the smart-verify path only. The orchestrator's mode-set input accepts `LOCAL` at the type level, but invoking it raises
    `NotImplementedError` until P1.5 lands the local checker.
11. **`Route53__Smart_Verify` shipped.** Pre-flight read on `records add` (decides `NEW_NAME` vs `UPSERT`). Always-on by default; opt out with `--no-verify`; force public-resolver check on the upsert / delete path with `--verify-public` (WARNING banner shown). New-name path runs authoritative + 6-resolver curated EU+US public-resolver fan-out, no banner. Upsert / delete path runs authoritative only, emits TTL-aware skip info line.
12. CLI subcommand shipped: `dns records check` accepts `--authoritative`
    (default-on), `--expect`, `--zone`, `--type`, `--json`. The `--public-resolvers`,
    `--local`, `--all`, `--min-resolvers` flags are **declared on the Typer
    surface but explicitly fail with a clear "shipping in P1.5" message** for the standalone command (the smart-verify wiring uses the public-resolver checker internally — that is shipped).
13. Exit-code mapping for P1: 0 = authoritative passed, 1 = authoritative
    disagreement.
14. **`dns instance create-record` shipped (NEW — rev 6).** Wires together
    `EC2__AWS__Client`, `Route53__Instance__Linker` (with the four per-spec
    `info` helper imports — vault_app, playwright, elastic, neko),
    `Route53__Zone__Resolver`, the idempotency / `--force` gate, and the
    new-name smart-verify path. Default `--ttl 60`. Default `--verify` on
    (runs authoritative + 6-resolver new-name path, no banner). The
    cert-warning info block (§11 verbatim) is printed after every successful
    create AND after every idempotent no-op (in the no-op case prefixed with
    "Already correct — record already points at this instance. Cert info still
    applies:"). `--json` mode emits `Schema__Instance__Create_Record__Result`;
    the cert-warning text is included as a `cert_warning_text` field so
    scripts can re-print it or suppress it. The cert-warning block is NOT a
    cert-issuance flow — it is purely informational; the two cert paths
    referenced in it are PROPOSED (§12) and not implemented.

**Acceptance:**
- `sg aws dns records add ...` creates a record; fails cleanly if it exists.
- `sg aws dns records update ...` upserts.
- `sg aws dns records delete ...` requires `--yes` + env gate or interactive
  confirmation; fails cleanly without.
- `sg aws dns records check zen-darwin --expect 203.0.113.5` (no mode flags
  — defaults to authoritative) returns a table of Route 53 NS rows; exit code
  0 on full agreement, 1 on any NS disagreement. **Zero cache pollution.**
- `sg aws dns records check ... --public-resolvers` exits with the "shipping
  in P1.5" message until that slice lands.
- All mutations return a `Schema__Route53__Change__Result` printed by the
  renderer (change-id + status).
- **Smart auto-verify acceptance:** `records add` on a new name runs authoritative + 6-resolver public-resolver fan-out automatically, with no WARNING banner. `records add` on an existing name (upsert), `records update`, and `records delete` each run authoritative only and emit the TTL-aware skip info line verbatim from §3. `--no-verify` skips all verification. `--verify-public` on the upsert / delete paths runs the standalone public-resolver check WITH the WARNING banner.
- **`instance create-record` acceptance (rev 6):** `sg aws dns instance create-record i-0abc…` resolves the instance, derives a sensible name, picks the deepest owning hosted zone, creates the A record with `--ttl 60`, runs the new-name smart-verify path, and prints the cert-warning info block. `sg aws dns instance create-record <stack-name>` resolves the stack via the per-spec `info` helpers (vault_app → playwright → elastic → neko, first match wins). `sg aws dns instance create-record --latest` picks the most recently launched SG-AI-tagged instance. Same-IP idempotency exits 0 with "already correct" + the cert-warning block. Different-IP without `--force` fails with the documented error message. Multi-label name (`--name my-ec2-1.dev.sgraph.ai`) lands in the `sgraph.ai` zone as a single record. `--zone vault.sgraph.ai --name my-ec2-1.dev.sgraph.ai` fails fast on containment violation.
- Integration test against real Route 53 dev zone gated on
  `SG_AWS__DNS__INTEGRATION=1`.

### P1.5 — Cache-polluting check modes (operator-paced opt-in)

**Scope:** light a candle the user has to choose to light. Lands when the
operator confirms (a) the authoritative-only default has bedded in and (b)
the WARNING-banner copy has been signed off.

1. `Route53__Public_Resolver__Checker` shipped behind `--public-resolvers`.
2. `Route53__Local__Checker` shipped behind `--local`.
3. `--all` convenience flag wired (= authoritative + public + local).
4. WARNING banner copy from §3 lands verbatim. Each cache-polluting mode
   prints its banner and prompts y/N (skipped with `--yes`).
5. Exit-code mapping extended: 2 = public-resolvers quorum failed, 3 = local
   mismatch.
6. `--min-resolvers` flag wired (defaults 5/8).

**Acceptance:**
- `sg aws dns records check ... --public-resolvers` prints the WARNING banner
  verbatim, prompts y/N, then fans out across 8 resolvers and reports quorum.
- `sg aws dns records check ... --local` prints the WARNING banner verbatim,
  prompts y/N, then shells out to `dig`.
- `sg aws dns records check ... --all` prints the combined WARNING banner
  verbatim once, prompts y/N, then runs all three modes.

### P2 — ACM enumeration polish + change polling

**Scope:** convenience layers on top of P1 / P1.5; no new core primitives.

1. ~~`--verify` flag on `records add` and `records update`~~ — **SUPERSEDED in rev 5** by always-on smart auto-verify in P1 (`Route53__Smart_Verify`). No separate `--verify` flag — the verification is the default behaviour, gated only by `--no-verify` and `--verify-public`.
2. `--all-regions` flag on `acm list` exercised in CI against a fixture (P0
   ships the method but `--all-regions` is unverified at scale until P2).
3. `get_change` polling for the eventual `--wait` flag on mutations.
4. (Possible — only if explicitly re-requested per Q5) `records alias` as a
   CLI command. **Currently not planned.**

**Acceptance:**
- `sg aws acm list --all-regions` returns results from every commercial region
  with rate limiting; verified against a CI fixture.

---

## 9. Risks & mitigations

| # | Risk | Mitigation |
|---|------|------------|
| **R0** | **DNS cache pollution from verification queries.** Any recursive resolver — public (8.8.8.8, 1.1.1.1, …) or corporate / VPN upstream — caches the answer it receives for up to the record's TTL (Route 53 default 300s; corporate proxies often pin or extend TTLs). If the operator runs `records check --public-resolvers` or `records check --local` and then changes the record (retry, fix, second deployment), those caches will return the OLD value until the TTL elapses. **There is NO way to flush a third-party recursive cache.** This is a real foot-gun that has bitten real teams. | (a) **Default mode of `records check` is `--authoritative`** — queries Route 53's own NS set directly with `+norecurse`. Zero cache pollution anywhere. This is what an operator wants after `records add` / `update`. (b) `--public-resolvers` is OPT-IN and prints a WARNING banner (§3, verbatim) plus a y/N prompt before running. (c) `--local` is OPT-IN and prints its own WARNING banner (§3, verbatim) plus a y/N prompt. (d) `--all` prints a combined WARNING banner (§3, verbatim) once. (e) Authoritative-mode is **P1**; the cache-polluting modes are **P1.5 / P2**, so P1 ships with zero foot-gun risk. (f) Public-resolvers and local mode warnings reference the safe default in their copy ("Use the default --authoritative mode for iterative verification") so the operator always knows the way out. (g) P2's `--verify` chained mode on `records add` / `records update` defaults to `--authoritative`, keeping the convenience layer cache-pollution-free. |
| R1 | Fat-fingered `records delete` on prod DNS — site goes dark | (a) Confirmation prompt with diff preview (Q4-A). (b) `SG_AWS__DNS__ALLOW_MUTATIONS=1` env gate — **locked in (Q4 RESOLVED)**. (c) `--yes` is documented as "I have verified the diff". (d) IAM policy in production scoped to specific hosted-zone ARNs only. |
| R2 | `records update` on the wrong record (typo in name resolves to a different existing record) | Confirmation prompt shows the **resolved** FQDN (including the resolved default `sgraph.ai` zone) and the current values being replaced. Operator can abort. |
| R3 | Zone-name resolution silently picks the wrong zone in multi-zone accounts (`example.com` vs `example.com.eu`) | `find_hosted_zone_by_name` requires an **exact** name match. If `list_hosted_zones_by_name` returns >1 candidate, raise with the list. Never auto-pick. Same rule applies to the `sgraph.ai` default lookup — exact match only. |
| R4 | TTL set too low (1s) on a high-traffic record — DNS load explodes | `Safe_Int__TTL` validates 1..86400; CLI default 300s; **warn** if TTL < 60s and require `--yes` to proceed. |
| R5 | TXT record with embedded quotes broken by shell quoting | CLI's `--value` flag accepts the raw string; `Route53__AWS__Client` quotes it for the API. Document with examples in the help text. |
| R6 | Cross-account confusion — operator runs `sg aws dns records delete` thinking they're in dev, actually in prod | Default table-header line shows the resolved AWS account-id (from `sts:GetCallerIdentity`) and the profile. Mutations include account-id in the confirmation prompt. The `--zone` default of `sgraph.ai` magnifies this risk — the confirmation prompt **always** shows the resolved zone name + zone-id, even when defaulted. |
| R7 | boto3 pagination missed on `list_resource_record_sets` — partial record listings hide records from `records list`, then `add` later fails on duplicate | All `list_*` methods use the boto3 paginator (`get_paginator(...).paginate()`), never raw `list_*` calls. Unit-tested with multi-page in-memory fixture. |
| R8 | `delete_record` requires the full current RR-set body — race condition between read and write means a concurrent mutator's value is silently deleted | Document the race. P2 can add `IfMatch`-style ETag if Route 53 ever supports it (today it doesn't); P1 mitigation is the confirmation prompt + short window. |
| R9 | `sgraph.ai` is not in the operator's account → every command fails on default-zone lookup | Failure is clear: `"--zone unset and no 'sgraph.ai' hosted zone found in account 123456789012. Pass --zone explicitly or provision the zone in this account."` Documented in `--help`. |
| R10 | **`dig` not installed on operator's machine** (rare on macOS / Linux, common on minimal containers). Now load-bearing on EVERY mode (Q7 RESOLVED — `dig` is the single transport via `Dig__Runner`) — so a missing `dig` breaks `--authoritative`, the smart-verify public-resolver fan-out, the standalone `--public-resolvers`, AND `--local`. | (a) Playwright Docker base image already ships `dnsutils` (verified — see §7 host-side prerequisites). (b) `Dig__Runner` surfaces `FileNotFoundError` cleanly; the CLI exits with a clear `dig not found on PATH — install dnsutils (Debian/Ubuntu) / bind-tools (Alpine) or run from the Playwright Docker image` error. (c) `test_Dig__Runner.py` asserts the failure shape. (d) Help text for `records check` notes the dependency. |
| R11 | ~~`--flush-local` requires sudo on macOS~~ | **REMOVED in rev 4.** The `--flush-local` sub-option was dropped. Platform-native cache flushing is left to the operator (`dscacheutil -flushcache; sudo killall -HUP mDNSResponder` on macOS; `systemd-resolve --flush-caches` on Linux). Pretending to abstract sudo / mDNSResponder fiddling was not worth the surface-area cost. |
| R12 | ~~`dnspython` not currently a dep — adding it widens the dependency surface (Q7)~~ | **REMOVED in rev 5.** Q7 RESOLVED — `dnspython` is NOT added; `dig` shell-out via `Dig__Runner` covers every command all three checkers need. Zero new runtime deps. The trade-off (shell-out cost ~5-15ms, locale-sensitive parsing) is recorded under R15a / R15b below. |
| R15a | **`dig` output parsing fragility** — output format is stable across major `dig` versions but locale-sensitive (date formats, whitespace, `;` comment positioning). Smart-verify's safety argument leans on being able to detect "NXDOMAIN vs answer" reliably. | (a) `Dig__Runner` pins `LC_ALL=C` in `subprocess.run`'s env block. (b) Prefer `+short` for value extraction (one value per line, no comments, no header). (c) NXDOMAIN detection uses the empty-stdout + non-zero exit-code signal from `dig +short` (this is well-defined across `dig` 9.x). (d) `test_Dig__Runner.py` runs canned stdout fixtures covering: positive answer (single + multi-value), NXDOMAIN, NODATA, timeout, missing-`dig` `FileNotFoundError`. |
| R15b | `Dig__Runner` adds per-invocation subprocess cost (~5-15ms × N resolvers). The 6-resolver smart-verify fan-out runs 6 subprocesses; the authoritative path runs 4. | Per-mode `ThreadPoolExecutor` keeps wall-clock dominated by the slowest single query (~50ms typical), not the sum. Acceptable for an operator CLI that already takes seconds to set up boto3 clients. |
| R16 | **Stale-TTL window after `records update` / `records delete`.** If a user runs the standalone `records check --public-resolvers` immediately after an upsert or delete, the public recursives will cache the answer for up to the *old* TTL — locking in either a stale positive or (on delete) a stale negative for the remainder of that window. There is NO way to flush a third-party recursive cache. | (a) **Smart auto-verify auto-skips the public-resolver path on upsert / delete** (always-on default in P1). (b) The skip info line surfaces the remaining wait time using the prior record's TTL ("for up to ~Ns of the prior record's TTL"). (c) `--verify-public` is required to force the public-resolver check in that window, AND it prints the WARNING banner first. (d) The standalone `records check --public-resolvers` keeps the same WARNING banner. A user who follows the on-screen guidance cannot accidentally cache-lock. |
| R13 | Quorum threshold (5/8 default) is wrong for the operator's network — false alarms or false reassurances | `--min-resolvers` is a flag; help text documents the trade-off; default chosen because Route 53 propagation is usually all-or-nothing within ~60s and 5/8 catches the in-progress case. Operators with weird ISPs can lower it. |
| R14 | The `sg aws` Typer group does not exist today; first attempt to wire it into `scripts/provision_ec2.py` could collide | **Pre-Dev audit complete** — top-level `sg` Typer root located at `scripts/provision_ec2.py:769`. No existing `add_typer(..., name='aws')` registration. Slot is free. |
| R15 | `osbot-aws` later adds Route 53 / ACM helpers; our direct-boto3 boundary becomes inconsistent | Document the upgrade path in each `*__AWS__Client.py` header (mirrors the `Elastic__AWS__Client` template). File the upstream-osbot-aws follow-up brief once this lands. |
| **R17** | **Instance public IP changes after `dns instance create-record`.** EC2 public IPv4 addresses are released when an instance is stopped and a new one is assigned when it next starts (unless an Elastic IP is attached). After a stop-start cycle, the A record this command created still points at the **OLD** IP — and because the default TTL is 60s, anyone who resolved the name in that window also caches the stale value for up to 60s. The user-visible failure is "DNS works, but the connection goes to the wrong host (or to nothing)". | (a) **Document the risk in the cert-warning block and in `--help`** — explicitly note that this command does not track IP changes and the operator must re-run it after a reboot, OR attach an EIP to the instance to pin the IP. (b) **P2 follow-up: `sg aws dns instance refresh-record <stack>`** — re-resolves the current public IP and upserts the existing record; idempotent if the IP has not changed. **Not in this brief.** (c) **P2 follow-up: `--attach-eip` flag** on `instance create-record` that allocates an EIP, associates it with the instance, and uses the EIP as the A-record target. Permanently stable. **Not in this brief.** (d) **Documentation-only mitigation in P1.** The TTL-60s default means the stale window after a stop-start is bounded at ~60s for downstream caches — acceptable for the ephemeral-stack use case the user has in mind. |

---

## 10. Test plan sketch

The repo's pytest convention: **no mocks, no patches** (CLAUDE.md, testing
guidance). Two test tracks.

### Track A — unit / in-memory (mandatory, runs in CI)

| Test file | What it asserts |
|-----------|------------------|
| `tests/service/test_Route53__AWS__Client.py` | Construction; method signatures match §5; an `Route53__AWS__Client__In_Memory` subclass (in `tests/service/_in_memory.py`) implements the boto3-layer methods against a dict-backed fixture, no `mock` module; each public method returns the documented schema shape; pagination across multiple pages works; `find_hosted_zone_by_name` raises on ambiguous match; **`resolve_default_zone` returns the `sgraph.ai` entry on first call, returns the cached entry without a second boto3 call on the second invocation, and raises `Route53__Default_Zone_Not_Found` when no `sgraph.ai` entry exists**. |
| `tests/service/test_Dig__Runner.py` | A `Dig__Runner__In_Memory` subclass overrides `run(...)` to return a canned `Schema__Dig__Result` based on `(argv,)` key lookup — composition, no `mock.patch`. Assert: positive answer (single value + multi-value), NXDOMAIN (empty stdout + non-zero exit), NODATA, subprocess timeout surfaces cleanly, missing-`dig` `FileNotFoundError` surfaces cleanly, `LC_ALL=C` is set in the env passed to `subprocess.run` (verified via a sentinel-collecting fake). |
| `tests/service/test_Route53__Authoritative__Checker.py` | Tests against `Route53__Authoritative__Checker__In_Memory` seeded with a `Dig__Runner` fake. Fixture: one NS-set response (the `get_hosted_zone` call returns 4 NS) and 4 `dig +short` outputs (one per NS). Assert: returns one row per Route 53 NS; all-agree → PASS (exit 0); one disagreement → FAIL (exit 1); the four `Dig__Runner` invocations carry `@<ns>` + `+norecurse`. Simpler than the rev 4 library-mock plan. |
| `tests/service/test_Route53__Public_Resolver__Checker.py` | `Dig__Runner` fake seeded with per-resolver canned outputs. Assert: quorum-met when 5/8 match (default standalone), quorum-failed when 4/8 match (and `--min-resolvers 5`), smart-verify subset of 6 members is correctly selected when invoked via the new-name path. |
| `tests/service/test_Route53__Local__Checker.py` | `Dig__Runner` fake returns canned local `dig +short` output. Assert: match → PASS, mismatch → exit 3, missing-`dig` `FileNotFoundError` degrades cleanly. |
| `tests/service/test_Route53__Check__Orchestrator.py` | Orchestrator wired to the three `__In_Memory` checkers (each in turn fed a `Dig__Runner` fake). Assert: default mode-set runs only authoritative; cache-polluting modes emit the WARNING banner before running; unified exit-code mapping (0 / 1 / 2 / 3). |
| `tests/service/test_Route53__Smart_Verify.py` | Wired to an `Route53__AWS__Client__In_Memory` (the existing `_Fake_R53` helper) plus the orchestrator + `Dig__Runner` fakes from above. Three test cases: **(a) new-name path** — `decide_before_add` returns `NEW_NAME` when `get_record` returns None; `verify_after_mutation` invokes the orchestrator with `{AUTHORITATIVE, PUBLIC_RESOLVERS}` and the 6-resolver smart subset; no WARNING banner printed (captured Console buffer is empty of WARNING strings). **(b) upsert path** — `decide_before_add` returns `UPSERT` with `prior_ttl=60` when `get_record` returns a hit; `verify_after_mutation` invokes orchestrator with `{AUTHORITATIVE}` only AND emits the upsert skip info line containing the literal substring `~60s of the prior record's TTL`. **(c) delete path** — `decide_before_delete` returns `DELETE` with `prior_ttl=60`; `verify_after_mutation` invokes orchestrator with `{AUTHORITATIVE}` (expecting NXDOMAIN per-NS) AND emits the delete skip info line containing `recursives may still serve the cached positive answer for up to ~60s`. Also asserts `no_verify=True` skips all verification, and `force_public=True` on upsert / delete invokes the standalone public-resolver path with the WARNING banner printed. |
| `tests/service/test_ACM__AWS__Client.py` | Construction; an `ACM__AWS__Client__In_Memory` subclass with a `{region: [cert]}` fixture; `list_certificates(region)` returns the list; `list_certificates__dual_region()` dedupes when current = us-east-1; ARN-derived region in `describe_certificate(arn)` parses correctly for both standard and gov-cloud ARN shapes; `list_certificates__all_regions()` iterates over the expected region set. |
| `tests/cli/test_Cli__Aws_Dns.py` | Mirrors `test_Cli__Vault_App.py`: `runner.invoke(app, ['--help'])`, `[zones, --help]`, `[records, --help]`, every subcommand has `--help`. Help text contains expected flags (`--json`, `--type`, `--ttl`, `--yes`, `--zone`, `--expect`, `--authoritative`, `--public-resolvers`, `--local`, `--all`, `--min-resolvers`). Renderer output (with no-color console) contains expected zone names and record types. `--json` output parses as valid JSON and round-trips through the schema. **No-`--zone` invocations resolve to `sgraph.ai` in the renderer header.** `records check` with no mode flags defaults to `--authoritative` and prints no WARNING banner. `records check --public-resolvers` and `records check --local` each emit the verbatim WARNING banner string from §3. `records check --all` emits the combined banner. |
| `tests/cli/test_Cli__Aws_Acm.py` | Mirrors above for ACM: list, show, JSON round-trip. Default invocation reports two regions in the header (current + us-east-1). |
| `tests/schemas/test_Schema__Route53__Record.py` | Type_Safe construction; raw primitives rejected; enum-based `type` field rejects unknown values; round-trips via `.json()` and reconstruction. |
| `tests/schemas/test_Schema__Dns__Check__Result.py` | Construction; per-resolver list shape; quorum + local fields present; round-trips. |
| `tests/schemas/test_Schema__ACM__Certificate.py` | Construction; enum-based `status` and `cert_type`; round-trips. |
| `tests/primitives/test_Safe_Str__Hosted_Zone_Id.py` | Accepts `Z01234567ABCDEFGHIJKL`; rejects lowercase, too-long, too-short. |
| `tests/primitives/test_Safe_Str__Resolver_IP.py` | Accepts IPv4 dotted-quad (`8.8.8.8`, `1.1.1.1`); accepts compressed IPv6; rejects hostnames; rejects malformed strings. Uses `ipaddress` stdlib at validation time. |
| `tests/primitives/test_Safe_Int__TTL.py` | 1..86400 accepted; 0 rejected (or accepted, depending on Q-followup); negative rejected. |
| `tests/primitives/test_Safe_Str__Record_Name.py` | **NEW — rev 6.** Single-label (`zen-darwin`) accepted; two-label (`zen-darwin.sgraph.ai`) accepted; deep multi-label (`my-ec2-1.dev.sgraph.ai`, `a.b.c.d.e.f.example.com`) accepted; trailing dot tolerated and normalised; empty labels (`..`, `a..b`) rejected; label > 63 chars rejected; total length > 253 chars rejected; leading hyphen rejected; underscore rejected. Asserts the permissive multi-label regex. |
| `tests/primitives/test_Safe_Str__IPv4.py` | **NEW — rev 6.** `8.8.8.8` accepted; `0.0.0.0` accepted; `255.255.255.255` accepted; `256.0.0.0` rejected; `8.8.8` rejected; IPv6 (`::1`) rejected. |
| `tests/primitives/test_Safe_Str__Instance_Id.py` | **NEW — rev 6.** `i-0abc1234` (8 chars) accepted; `i-0abc1234567890abc` (17 chars) accepted; `I-0abc1234` (uppercase prefix) rejected; uppercase hex in body rejected; missing `i-` prefix rejected; `i-` alone rejected. |
| `tests/service/test_Route53__Zone__Resolver.py` | **NEW — rev 6.** Backed by an in-memory `Route53__AWS__Client__In_Memory` seeded with various zone-list fixtures. **(a) single-zone case** — `resolve_zone_for_name('my-ec2-1.dev.sgraph.ai')` returns `sgraph.ai` when only `sgraph.ai` exists; **(b) deepest-match case** — same call returns `dev.sgraph.ai` when both zones exist (simulates future sub-delegation); **(c) apex case** — `resolve_zone_for_name('sgraph.ai')` returns the `sgraph.ai` zone; **(d) no-match case** — raises `Route53__Zone__Not_Found`; **(e) trailing-dot normalisation** — `my-ec2-1.dev.sgraph.ai.` matches the same way as the non-dot form; **(f) caching** — the list-hosted-zones call happens once across N resolutions; **(g) containment enforcement** — `enforce_containment('my-ec2-1.dev.sgraph.ai', 'vault.sgraph.ai')` raises `Route53__Zone__Containment_Error`; `enforce_containment('zen-darwin.vault.sgraph.ai', 'vault.sgraph.ai')` passes. |
| `tests/service/test_Route53__Instance__Linker.py` | **NEW — rev 6.** Backed by `EC2__AWS__Client__In_Memory` (a `_Fake_EC2` dict-backed fixture) plus stub per-spec `info` helpers in `tests/service/_fake_specs.py`. **(a) instance-id path** — `resolve('i-0abc1234')` calls `describe_instance` once, returns `Schema__Instance__Resolution(source=INSTANCE_ID, ...)`. **(b) stack-name path** — `resolve('quiet-fermi')` tries vault_app first; on match returns `source=STACK_NAME, stack_name='quiet-fermi'`. **(c) stack-name fallthrough** — when not in vault_app, tries playwright, then elastic, then neko. **(d) `--latest` path** — `resolve('', latest=True)` lists by `tag:sg-ai=*`, sorts by `LaunchTime`, returns the most recent `running` instance, `source=LATEST`. **(e) no-public-IP** — raises `Route53__Instance__No_Public_IP` when `PublicIpAddress` is empty (stopped instance). **(f) ambiguous stack-name** — when the same stack-name appears in two specs (artificial but possible in tests), raises with the list. **(g) name-tag derivation** — `derive_record_name(resolution, zone)` returns `<name-tag>.<zone>` when `Name` tag is set; falls back to `<stack-name>.<zone>` otherwise; falls back to `<instance-id>.<zone>` when neither is known. |
| `tests/service/test_EC2__AWS__Client.py` | **NEW — rev 6.** `EC2__AWS__Client__In_Memory` with a `{instance_id: instance-shape}` fixture; assert `describe_instance` round-trips a single instance; `list_instances_by_tag('sg-ai', '*')` paginator handles multi-page; `describe_tags_for_instance` reads the `Tags` block. Asserts the boto3 client never touches the network in unit tests (the in-memory client is the only implementation called). |
| `tests/cli/test_Cli__Aws_Dns__instance_create_record.py` | **NEW — rev 6.** CliRunner-based tests of `dns instance create-record`. **(a) happy path** — `sg aws dns instance create-record i-0abc1234` resolves through the in-memory EC2 client + the in-memory Route 53 client + a fake `Route53__Zone__Resolver`, prints the success table, prints the cert-warning info block verbatim, exits 0. **(b) idempotent no-op** — same command run twice in a row: second run sees the existing record pointing at the same IP, exits 0 with "Already correct — record already points at this instance." AND prints the cert-warning block. **(c) different-IP without `--force`** — the existing record points at a different IP, exits non-zero with `"name exists pointing at <other-ip>; use sg aws dns records update or pass --force"`. **(d) `--force` overrides** — runs an upsert, exits 0. **(e) multi-label name** — `--name my-ec2-1.dev.sgraph.ai` lands in the `sgraph.ai` zone (single-zone fixture). **(f) `--zone` containment violation** — `--zone vault.sgraph.ai --name my-ec2-1.dev.sgraph.ai` fails fast before any boto3 call. **(g) `--latest`** — picks the most recently launched fixture instance. **(h) `--json`** — output parses as `Schema__Instance__Create_Record__Result`; `cert_warning_text` field is present and non-empty. (i) **`--no-verify`** — skips the smart-verify block in the rendered output. |

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
surface is even smaller (2 methods, paginated list). Each of the three
checker classes has its own in-memory fake: the authoritative checker maps
NS-IP → canned answer (over a canned NS set), the public-resolver checker
maps resolver-enum → canned answer, the local checker replaces
`subprocess.run` with a fake callable in-process (composition, not
`mock.patch`). The orchestrator composes them in the same way the
production class does. All deterministic, all fast.

**No for Track B.** Pagination quirks, change-status polling timing, name
servers, real-world propagation latency, IAM permission edges, and ACM
in-use-by counts only show up against the real API. Gate on the env vars;
skip cleanly in normal CI.

### Not unit-testable

- Real Route 53 change-status propagation (`PENDING` → `INSYNC`) — Track B only.
- Real-world DNS propagation across global resolvers — Track B (or manual via
  `sg aws dns records check`).
- ~~macOS sudo prompt for `--flush-local`~~ — REMOVED (rev 4); `--flush-local` was dropped, operator flushes manually.
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
2. **Smart-verify info-line wordings** — sign off the three verbatim info lines below before P1 ships. These are printed by `Route53__Smart_Verify` on every `records add` (new-name and upsert paths) and `records delete`. The three lines, **verbatim from §3**:
   - **(a) New-name auto-verify summary line** (printed before the combined authoritative + 6-resolver table on `records add` for a name+type that did NOT previously exist):
     > `Auto-verify: new name — no prior recursive cache to pollute, so the authoritative check AND a curated 6-resolver EU+US public-resolver check are both run. Safe by construction.`
   - **(b) Upsert "public-resolver skipped" info line** (printed after the authoritative-only verify on `records add` for an existing name+type, or on `records update`; `<T>` is filled with the prior record's TTL in seconds):
     > `Authoritative is consistent. Public-resolver check skipped — would risk locking in stale answers for the remaining ~<T>s of the prior record's TTL. Run `sg aws dns records check <name> --public-resolvers` once the old TTL has elapsed.`
   - **(c) Delete "public-resolver skipped" info line** (printed after the authoritative-only verify on `records delete`; `<T>` is the prior record's TTL):
     > `Authoritative confirms deletion. Public-resolver check skipped — recursives may still serve the cached positive answer for up to ~<T>s. Run `sg aws dns records check <name> --public-resolvers` after that to confirm propagation.`
3. **WARNING banner copy** — sign off the three verbatim banner strings in §3
   (the `--public-resolvers` banner, the `--local` banner, and the combined
   `--all` banner) before P1.5 ships. The default `--authoritative` mode is
   silent (no warning needed — zero cache pollution). **[Already signed off in rev 4 — listed here for completeness.]**
4. **Scope** — confirm P0 (read-only DNS + ACM list + sgraph.ai default) is the
   first slice Dev picks up. Smallest, lowest-risk, unblocks the bigger CF+R53
   plan's read paths.
5. **`SG_AWS__DNS__ALLOW_MUTATIONS=1` env-var name** — bikeshed-safe but
   double-check the name is the one we want before P1 ships. (Q4 RESOLVED on
   *requiring* the gate; the *name* is editable.)
6. **6th smart-verify resolver — AdGuard EU (`94.140.14.14`)** — Architect picked AdGuard EU over Yandex EU on neutrality grounds (Yandex's geopolitical association would surprise some operators; AdGuard is a privacy-focused commercial resolver with no comparable political baggage and a stable EU anycast presence). **Revisitable in rev 6** — flag if Yandex EU (`77.88.8.8`) or a different 6th member is preferred.
7. **Cert-warning text block — sign off the verbatim copy (NEW — rev 6).** This block is printed by `sg aws dns instance create-record` after every successful create AND after every idempotent no-op (in the no-op case prefixed by "Already correct — record already points at this instance. Cert info still applies:"). It is **informational only** — the two cert paths it references are PROPOSED (§12), NOT in P1, NOT in P2. The verbatim copy below must be confirmed before P1 ships:

   ```
   ⚠ HTTPS cert
   This DNS name is now usable, but HTTPS clients will see a certificate
   warning until a cert is issued for `quiet-fermi.sgraph.ai`. Today, the
   vault-app / playwright stacks ship Let's Encrypt IP-anchored certs
   (valid for the EC2 public IP, not the DNS name).

   Options to fix:
     (a) `sg playwright vault re-cert --hostname quiet-fermi.sgraph.ai`
         — uses our own cert sidecar workflow. Fast. No AWS account
         pollution. ⚠ PROPOSED — see brief §addendum-cert. NOT IN P1.
     (b) `sg aws acm request --domain quiet-fermi.sgraph.ai` — issues an
         ACM cert. Useful only if you are terminating TLS on CloudFront /
         ELB. ⚠ Adds an entry to ACM that does NOT auto-delete when the
         stack is destroyed. PROPOSED — NOT IN P1.

   For now, accept the cert warning or use the IP-based vault_url
   surfaced by `sp pw v info`.
   ```

   The `quiet-fermi.sgraph.ai` substring is interpolated with the actual
   derived FQDN at runtime. Everything else is fixed copy.
8. **Q9 — HTTP-01 (downtime) vs DNS-01 (no downtime) for the future cert path (NEW — rev 6).** See §4 Q9 for the full breakdown. Architect recommendation: **B (DNS-01)**. Decision pending and **not blocking P1** — Q9 only resolves when the §12 cert workflow slice is greenlit.

### RESOLVED items (no further user action)

- **Q2** — `add` is strict CREATE, `update` is UPSERT.
- **Q3** — No hosted-zone CRUD ever. List/show only.
- **Q4** — Confirm on `update` / `delete`; `--yes` skips; `SG_AWS__DNS__ALLOW_MUTATIONS=1`
  env gate required.
- **Q5** — No `records alias` CLI command. Library helper only.
- **Q6** — `--profile` + `--region` on every command. ACM defaults dual-region.
- **Q7** — Use `dig` shell-out via the shared `Dig__Runner` helper; no `dnspython` dependency added.
- **Q8** — ~~`--verify` chaining on `records add` / `records update` lives in **P2**~~ **SUPERSEDED in rev 5.** Replaced by always-on smart auto-verify in P1 (`Route53__Smart_Verify`). `--no-verify` opts out for scripted runs; `--verify-public` forces the public-resolver check on the upsert / delete paths (with the WARNING banner). The standalone `records check` command is unchanged.

### Dev contract (when Q1 / Q7 land)

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

## 12. Addendum — per-instance HTTPS cert workflows (PROPOSED, NOT in P1) {#addendum-cert}

**Scope of this addendum.** `sg aws dns instance create-record` (P1, §3, §6,
§8) lands a DNS A record pointing at an EC2 instance, but the instance is
still serving HTTPS with whatever cert it booted with — today that's an
IP-anchored Let's Encrypt cert from the `letsencrypt-ip` mode of
`sg_compute/platforms/tls/cert_init.py` (the boot-time mode landed in commit
`8aad135`; verified by reading `cert_init.py:83`+`Cert__ACME__Client.py`).
That cert is valid for the **IP address**, not for the FQDN the user just
created — so HTTPS clients hitting `https://quiet-fermi.sgraph.ai` will get
a CN-mismatch warning. This addendum captures two **future** paths to fix
that, both marked **PROPOSED** and explicitly **NOT in P1, NOT in P2**.

### Existing cert infrastructure (read first)

The repo already ships an ACME client for Let's Encrypt. **Verified by
reading the source on 2026-05-15:**

- `sg_compute/platforms/tls/Cert__ACME__Client.py` — issues a publicly-trusted
  cert via the ACME protocol (RFC 8555). `issue(ip, cert_path, key_path,
  config)` is the one-shot entry. Builds a CSR with `crypto_util.make_csr(
  cert_key_pem, ipaddrs=[ip])` — **IP-anchored only today**; no `domains=[...]`
  branch. Default directory is LE staging.
- `sg_compute/platforms/tls/cert_init.py` — entry point for the one-shot
  sidecar; modes are `self-signed` (default, offline) and `letsencrypt-ip`
  (calls `Cert__ACME__Client.issue(...)`). The CN / IP resolution path is
  `SG__CERT_INIT__COMMON_NAME` env → IMDSv2 public IPv4 → `localhost` (the
  `letsencrypt-ip` mode hard-fails if it cannot resolve a real public IP).
- `sg_compute/platforms/tls/ACME__Challenge__Server.py` — the throwaway
  HTTP server that serves the `.well-known/acme-challenge/<token>` path on
  port 80 during issuance. Binds `0.0.0.0:80` directly — there is no DNS-01
  pathway here.
- `sg_compute/platforms/tls/Schema__ACME__Config.py` — config schema;
  `challenge_port: int = 80` confirms the HTTP-only design.

**Is DNS-01 supported today? NO.** `Cert__ACME__Client.select_http01(order)`
hard-codes `isinstance(challb.chall, challenges.HTTP01)` and raises
`RuntimeError('ACME order offered no http-01 challenge')` if no HTTP-01 is
present. No `select_dns01` method exists; no `dns_*` helper anywhere in the
file; no `Route53__*` import. Q9 (§4) asks the user to decide whether to
add DNS-01 alongside HTTP-01 (Architect rec: add it).

### Path A — own cert sidecar (preferred long-term)

**Workflow (HTTP-01 variant — Q9-A).**

1. The host runs the main service container (vault-app, playwright) on :443
   with the LE-IP cert.
2. Operator runs `sg playwright vault re-cert --hostname quiet-fermi.sgraph.ai`
   (PROPOSED command — no implementation today).
3. CLI resolves the instance (reuses `Route53__Instance__Linker` from this
   brief), connects via SSH / SSM, runs a re-cert script that:
   - Stops the main service container (vault-app or playwright). Brief
     downtime begins.
   - Starts the cert sidecar (`python -m sg_compute.platforms.tls.cert_init`)
     with `SG__CERT_INIT__MODE=letsencrypt-hostname` (new mode — does not
     exist today) and `SG__CERT_INIT__COMMON_NAME=quiet-fermi.sgraph.ai`.
   - The sidecar binds :80, runs HTTP-01 (relies on the DNS A record
     already pointing at this IP — that's what `dns instance create-record`
     just ensured, and the new-name auto-verify path already confirmed
     global propagation across the 6-resolver fan-out).
   - On success, new `fullchain.pem` + `privkey.pem` land on the shared
     `/certs` volume.
   - Stops the sidecar.
   - Restarts the main service container with the new cert mounted.
4. Operator now has working HTTPS at `https://quiet-fermi.sgraph.ai`.

**Workflow (DNS-01 variant — Q9-B, recommended).**

1. Main service stays up on :443 — no downtime.
2. Operator runs `sg playwright vault re-cert --hostname quiet-fermi.sgraph.ai
   --dns-01`.
3. CLI calls a new `Cert__ACME__Client.issue_for_hostname(hostname, ...)`
   method (PROPOSED — see Q9), which:
   - Builds a CSR with `domains=[hostname]` instead of `ipaddrs=[...]`.
   - Selects the DNS-01 challenge from the ACME order
     (`select_dns01(order)` — new method).
   - Reads the key-authorization value and publishes it as a TXT record
     `_acme-challenge.quiet-fermi.sgraph.ai` via
     `Route53__AWS__Client.upsert_record(...)` (already exists in P1).
   - Polls the authoritative NS set via `Route53__Authoritative__Checker`
     (already exists in P1) until the TXT record is propagated — zero
     cache pollution.
   - Calls `acme_client.answer_challenge(...)` and
     `acme_client.poll_and_finalize(...)`.
   - Deletes the TXT record via `Route53__AWS__Client.delete_record(...)`.
4. New cert lands in `/certs`; the main service is signalled to reload
   (Nginx-style `kill -HUP`, or container restart if reload-on-cert-change
   is not wired).
5. Operator has working HTTPS at `https://quiet-fermi.sgraph.ai` with **zero
   downtime**.

**Trade-offs (both variants share most of these; differences flagged):**

- ✓ **No AWS Certificate Manager entries created.** Zero ACM-account
  pollution even with hundreds of ephemeral stacks.
- ✓ **Faster than ACM end-to-end.** LE issuance is typically ~10-30s for
  HTTP-01 and ~30-90s for DNS-01 (validation propagation is the slow part);
  ACM DNS-01 validation for the first cert in an account can take 5+ min.
- ✓ **Reuses existing in-repo code** (`Cert__ACME__Client`, `cert_init.py`).
- ✗ **HTTP-01 variant: brief service downtime (~10-20s)** while the sidecar
  binds :80 and the main container is stopped. **DNS-01 variant: ZERO
  downtime.** This is the single biggest argument for Q9-B.
- ✗ **Let's Encrypt rate limits.** 50 certs / registered-domain (`sgraph.ai`)
  per week. Could bite at scale. Mitigation: use LE **staging** (no rate
  limit, untrusted-CA cert) for ephemeral dev stacks, and only use LE
  **production** for stacks the operator explicitly marks for trusted-cert
  provisioning. The `prod` flag in `Cert__ACME__Client.config(prod=False)`
  already exists for exactly this.
- ✗ **HTTP-01 variant: 60s-TTL interaction.** LE's validation server resolves
  the FQDN → this IP at validation time. With a 60s TTL on a freshly-created
  record, the new-name auto-verify (P1, §3) already proves the record is
  live globally before re-cert runs, so this is fine in practice. DNS-01
  variant does not have this dependency (LE just checks the TXT record).
- ✗ **DNS-01 variant pulls `Route53__AWS__Client` into the TLS pipeline.**
  The sidecar needs an AWS IAM role scoped to
  `route53:ChangeResourceRecordSets` on the relevant hosted zone +
  `route53:GetChange`. Same scope this brief already establishes.
- ✗ **DNS-01 variant pulls in DNS-01 ACME plumbing** (~50-80 LoC in
  `Cert__ACME__Client`). The HTTP-01 path stays unchanged for the
  boot-time IP cert.

### Path B — AWS Certificate Manager (documented for completeness; not recommended for ephemeral stacks)

**Workflow.**

1. Operator runs `sg aws acm request --domain quiet-fermi.sgraph.ai`
   (PROPOSED — see §2 non-goal "No ACM cert issuance"; this would lift the
   non-goal).
2. CLI calls a new `ACM__AWS__Client.request_certificate(domain,
   validation_method='DNS')` (PROPOSED — not in this brief; would be added
   as a sibling to the existing read-only methods).
3. ACM creates a pending cert; the response includes a DNS validation
   record (`_xyz.quiet-fermi.sgraph.ai CNAME _abc.acm-validations.aws`).
4. CLI auto-creates that CNAME via `Route53__AWS__Client.upsert_record(...)`
   (already exists in P1).
5. CLI polls `acm:DescribeCertificate` (already exists in P0) until
   `Status == 'ISSUED'`. Typical 2-5 min; can be much longer for first cert
   in a new account.
6. Cert ARN returned. To use it on the actual instance you have to either
   import it into the host (defeating the point of ACM), front the
   instance with CloudFront / ELB (heavy lift, separate brief), or accept
   that the ACM cert lives unused.

**Trade-offs.**

- ✓ **AWS-managed renewal** (60 days before expiry).
- ✓ **Useful if terminating TLS on CloudFront / ELB.** For those cases ACM
  is mandatory — CloudFront refuses to attach non-ACM certs.
- ✗ **Pollutes the AWS account.** Every ephemeral stack adds an ACM entry
  that does NOT auto-delete when the EC2 stack is destroyed. The user
  specifically flagged this as the disqualifier for routine use.
- ✗ **Slower than LE.** Validation propagation + ACM polling (5-15 min for
  first cert in a new account; 2-5 min subsequent).
- ✗ **Cert lifecycle is decoupled from the EC2 stack lifecycle.** Orphaned
  certs accumulate. Cleanup is a separate operator chore.
- ✗ **No short-lived option.** ACM-issued *public* certs are 13 months. LE
  has a `shortlived` profile (~6 days for IP certs); there's no comparable
  knob in ACM.

### Recommendation

**Path A (DNS-01 variant — Q9-B) is the right primary path.** Reasons:

1. Zero downtime for the operator.
2. Zero AWS-account pollution.
3. Reuses every primitive this brief already ships (`Route53__AWS__Client`,
   `Route53__Authoritative__Checker`).
4. Small code delta in the cert pipeline (~50-80 LoC).
5. Aligns with the "ephemeral stacks, short-lived certs" model the user
   has already endorsed for the boot-time cert path.

**Path B is the right escape hatch** for the CloudFront-termination case
only — where ACM is mandatory and there is no choice.

### Out-of-scope clarifications

- This addendum does **not** implement either path. P1 / P2 of this brief
  do **not** include any cert-issuance code beyond what already exists in
  `sg_compute/platforms/tls/`.
- The cert-warning text block (§11 §11.7) is **informational only** — it
  points operators at the two paths above but does not promise either is
  available today.
- Q9 (§4) is the decision the user must make before the cert workflow
  slice is greenlit. Until then, the cert-warning block remains "accept
  the cert warning or use the IP-based vault_url".

---

*Filed by Architect (Claude), 2026-05-15. No code changed by this document — it
is a plan and a set of decisions for human ratification before Dev picks it up.
Rev 2 folded in user feedback: default zone `sgraph.ai`, propagation checker
(`records check`), ACM list/show (dual-region default), Q2/Q3/Q4/Q5/Q6
resolved, Q1 re-investigated against the proposed
`sg_compute_specs/platform/` tier with explicit recommendation. Rev 4
(this revision, 2026-05-15 hour 11) redesigns `records check` around three
checker classes + an orchestrator to eliminate the DNS-cache-pollution
foot-gun the user identified: the default mode (`--authoritative`) queries
Route 53's own NS set directly with `+norecurse`, has zero cache pollution
anywhere, and is the only mode shipped in P1. The two cache-polluting modes
(`--public-resolvers`, `--local`) are P1.5 / P2, each gated behind a verbatim
WARNING banner + y/N prompt. The `--flush-local` sub-option is dropped.
Q8 RESOLVED (verify chaining is P2, defaults to `--authoritative`).
Q7 (`dnspython` as direct dep) is now load-bearing on P1; `dig`-only
fallback noted as viable. Rev 5 (2026-05-15 hour 12) folds in two further user
refinements: (1) Q7 RESOLVED to use `dig` shell-out — no `dnspython` dependency
is added; a new `Dig__Runner` helper is the single subprocess transport for all
three checkers. (2) Smart auto-verify lands on every `records add` / `update` /
`delete` in P1 via a new `Route53__Smart_Verify` class: new-name `records add`
auto-runs a curated 6-resolver EU+US public-resolver check (safe, no prior
cache); upserts and deletes auto-skip the public-resolver path and emit a
TTL-aware skip info line; `--no-verify` opts out for scripting and
`--verify-public` forces the public-resolver check on the change / delete
paths WITH the WARNING banner. The 6th EU resolver is AdGuard EU
(`94.140.14.14`) on neutrality grounds. Three new info-line wordings are listed
verbatim in §11 for sign-off. Q8 is SUPERSEDED. New risk R16 covers the
stale-TTL window. Rev 6 (this revision, 2026-05-15 hour 14) folds in three
further user-driven additions: (1) **`sg aws dns instance create-record`**
(P1) — a single command that resolves an EC2 instance (instance-id, stack
name via the per-spec `info` helpers under `sg_compute_specs/{vault_app,
playwright,elastic,neko}/cli/`, or the `--latest` sentinel) to its public
IPv4, derives a sensible record name (Name-tag → stack-name → instance-id),
picks the deepest owning hosted zone via the new `Route53__Zone__Resolver`,
runs the new-name smart-verify path, and prints a verbatim cert-warning info
block. Default TTL 60s. Idempotent on same-IP; fails-fast on different-IP
without `--force`. (2) **Multi-label name support** — `Safe_Str__Record_Name`
becomes a permissive RFC-1035 multi-label regex; the new
`Route53__Zone__Resolver.resolve_zone_for_name(fqdn)` walks labels deepest-
first to pick the longest-matching owning zone, so sub-delegation (when
`dev.sgraph.ai` is later promoted to its own zone) works with zero code
change. (3) **§12 ADDENDUM — per-instance cert workflows** (PROPOSED, NOT in
P1, NOT in P2) capturing Path A (own cert sidecar reusing
`sg_compute/platforms/tls/Cert__ACME__Client`; HTTP-01 today, DNS-01
proposed) and Path B (AWS Certificate Manager, documented as the
account-polluting escape hatch). `Cert__ACME__Client` verified **HTTP-01
only** today; new **Q9** (DNS-01 vs HTTP-01) added for the future cert path.
New file `Route53__Instance__Linker`, new boto3 boundary `EC2__AWS__Client`
under `sgraph_ai_service_playwright__cli/aws/ec2/`, new IAM action
`ec2:DescribeInstances` (+ `ec2:DescribeTags`). New risk **R17** — instance
public IP changes after stop-start; P2 follow-ups are
`dns instance refresh-record` and `--attach-eip`. This brief remains the
simpler standalone subset of
`05/15/03/architect__vault-app__cf-route53__plan.md`; the bigger plan will
consume the `Route53__AWS__Client` + `ACM__AWS__Client` primitives this brief
defines, instead of introducing its own.*
