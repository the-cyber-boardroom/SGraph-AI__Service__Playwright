# Debrief — `sg aws dns` P1 (mutations + dig-based verify + instance create-record)

| Field    | Value |
|----------|-------|
| Date     | 2026-05-15 |
| Branch   | claude/add-cf-route53-support-sqeck |
| Commits  | `8ec54817` (P1 core) → `b25b5b89` (zone-resolver FQDN fix) → `a52b392b` (apex-of-child-zone fix) → `db1b7148` (`--wait`) |
| Scope    | extends `Route53__AWS__Client` + adds 7 service classes + `dns records {add,update,delete,check}` + `dns instance create-record` |
| Tests    | 52 → 102 → 122 → 128 passing across the four commits |
| Verified | End-to-end against the real `sgraph.ai` zone: `records add warm-bohr.sg-compute.sgraph.ai --wait` submits, polls INSYNC, runs the authoritative + 6-resolver public-resolver fan-out, prints the cert-warning. |

## Scope

Three layers shipped in one branch:

### Part A — Record mutations
- `Route53__AWS__Client.create_record / upsert_record / delete_record / upsert_a_alias_record`. Built on a shared `_change_rrset` helper that constructs the `ChangeBatch` and maps the response.
- `Schema__Route53__Change__Result` (change-id, status, submitted-at).
- CLI `records add` / `update` (with diff preview + confirm) / `delete` (with confirm).
- All three originally gated on `SG_AWS__DNS__ALLOW_MUTATIONS=1` env var (Q4 — belt-and-braces). Later **dropped from `records add`** in post-P1.5 ergonomics; kept on `update` + `delete` since those are genuinely destructive.

### Part B — Dig-based verification (no new runtime deps)
- `Dig__Runner` — thin `subprocess.run(['dig', ...])` wrapper, `LC_ALL=C` for parse stability, `Schema__Dig__Result` shape.
- `Route53__Authoritative__Checker` — fetches NS for the zone via `route53:GetHostedZone.DelegationSet`, then `dig @<ns> +short +norecurse <name> <type>` against each. Zero cache pollution.
- `Route53__Public_Resolver__Checker` — 6-resolver curated EU+US fan-out (Cloudflare 1.1.1.1/1.0.0.1, Google 8.8.8.8/8.8.4.4, Quad9 9.9.9.9, AdGuard EU 94.140.14.14). Used internally by smart-verify for the NEW_NAME path only; the standalone `--public-resolvers` flag stubs "ships in P1.5".
- `Route53__Check__Orchestrator` — composes the checkers behind a single surface.
- `Route53__Smart_Verify` — pre-flight `get_record` decides NEW_NAME vs UPSERT vs DELETE. After mutation: runs authoritative + (NEW_NAME only) public resolvers. Three verbatim info lines from the brief are emitted as documented.
- CLI `records check` — authoritative-only by default (safe, zero-cache-pollution); cache-polluting flags stub for P1.5.
- **Q7 RESOLVED**: `dig` shell-out is the single transport. `dnspython` was not added.
- **Q8 RESOLVED**: `--verify` chained flag superseded by always-on smart auto-verify; `--no-verify` opts out.

### Part C — Instance create-record (later subsumed by smart `records add`)
- `Route53__Zone__Resolver` — walks FQDN labels deepest-first to find the owning hosted zone.
- `Route53__Instance__Linker` — resolves an EC2 instance ref (i-id / Name tag / `--latest`) to a public IP via direct boto3 EC2 (documented exception).
- CLI `dns instance create-record` — idempotent same-IP; `--force` upsert; default TTL 60s; cert-warning info block printed after success.

23 files changed in the P1 commit, +1,643 lines; 6 new test files (Dig__Runner, Authoritative__Checker, Smart_Verify, Zone__Resolver, Instance__Linker), plus extended `Route53__AWS__Client` tests (+8 mutation cases).

## Good failures

- **The `Route53__Authoritative__Checker` lookup pattern was right by design.** Querying Route 53's own NS via `+norecurse` does not pollute any recursive cache anywhere — the answer never sees a recursive resolver. This was the explicit user requirement and the auth-only default mode preserves it. The cache-pollution math was sketched and signed off in the brief (rev 4 WARNING banners) before P1.5 wired the cache-polluting modes.
- **`--wait` UX validated end-to-end** with a real `records add`. Submit → poll `GetChange` every 2s → INSYNC in ~20s on the dev zone → authoritative check → 6/6 public resolvers agree → cert-warning. Exit 0. Suitable for chaining into a cert-issuance step.
- **Two FQDN-resolution bugs caught fast in live use**, fixed in `b25b5b89` and `a52b392b` (see "Bad failures" below). Both had targeted regression tests added before push.

## Bad failures

- **Zone resolver was incomplete on first ship.** Two distinct misses, reported by the user on consecutive runs:

  - **Bug 1 — `records check test.sg-compute.sgraph.ai`** returned "0/4 authoritative nameservers agree" with "(no answer)" rows. Root cause: when no `--zone` was passed, the CLI defaulted to `sgraph.ai` blindly, but `sg-compute.sgraph.ai` is a delegated sub-zone. The parent's NS only hold the delegation NS-records, not the leaf A record. `Route53__Zone__Resolver` (shipped in Part C) existed and was correct, but `records check / get / add / update / delete` never called it — they used the older `_resolve_zone_id` helper. Fixed in `b25b5b89` by introducing `_resolve_zone_id_for_record(client, zone, name)` that walks labels when `--zone` is empty. Five record commands switched to it.

  - **Bug 2 — `records check sg-compute.sgraph.ai --type NS`** still returned "0/4 NS agree" after Bug 1 was fixed. Root cause: `Route53__Zone__Resolver.resolve_zone_for_fqdn` walked from `parts[i+1:]` (parents), so for a 3-part FQDN that IS itself a child-zone apex (`sg-compute.sgraph.ai`), the first candidate was already `sgraph.ai` (parent). The "exact match" fallback at the bottom of the function was dead code. Fixed in `a52b392b` by walking `parts[i:]` (the FQDN itself first) and dropping the dead fallback. Two regression tests pin this case.

  Both bugs would have been caught earlier by a single end-to-end test against a real delegated sub-zone. The unit-test fake data had `dev.sgraph.ai` and `stage.sgraph.ai` flat under `sgraph.ai` but never exercised a true delegation pattern.

- **The P1 agent ran in a worktree** (`isolation: "worktree"`) which initially confused me — the working tree on `main` showed 52/52 (the P0 state) while the worktree had 102/102. A quick `git pull` fixed it but it's a footgun worth remembering for future worktree-based slices.

## Follow-ups

- **`dns instance create-record` is now redundant** with the smart `records add` shipped in post-P1.5 ergonomics. Both paths work today; the duplication is documented but not resolved.
- **Q9 still PENDING** — DNS-01 vs HTTP-01 for the cert sidecar workflow (§12 ADDENDUM). DNS-01 would let the cert path skip the brief service downtime that HTTP-01 needs and reuse the Route53 primitives shipped here.
