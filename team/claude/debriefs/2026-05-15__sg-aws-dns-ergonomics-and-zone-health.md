# Debrief — `sg aws dns` post-P1.5 ergonomics + zone health + purge

| Field    | Value |
|----------|-------|
| Date     | 2026-05-15 |
| Branch   | claude/add-cf-route53-support-sqeck |
| Commits  | `e4de7848` → `652bbabe` → `685427d6` → `65a85fba` → `820fb96b` → `de9cf2e7` |
| Scope    | smart `records add` dispatch; default zone change; env-gate drop; CLI restructure (`zone` singular); `zone check` + `zone purge`; alias-record support; ACM cross-reference for CNAMEs |
| Tests    | 112 → 136 passing (+24 across the six commits) |
| Verified | `sg aws dns records add i-0717a38ecf7f86411 --wait` end-to-end: instance resolution → derived `warm-bohr.sg-compute.sgraph.ai` → INSYNC in ~20s → 4/4 NS + 6/6 public resolvers agree → cert-warning printed. `zone check sgraph.ai` correctly classifies CloudFront alias A records as IGNORED and identifies ACM validation CNAMEs via cross-reference. |

## What got built

A series of live-use feedback fixes after P1.5 shipped. The first iteration was driven by the user trying the CLI against a real account; each subsequent commit responded to a specific friction point.

### `e4de7848` — Ergonomic `records add`
- Default zone moved from `sgraph.ai` → `sg-compute.sgraph.ai` (env-overridable via `SG_AWS__DNS__DEFAULT_ZONE`). Reasoning: ephemeral compute stacks live in the sub-zone; the apex is reserved for stable records.
- Two optional positional args replacing the old `<name> --value <ip>` mandatory form. Dispatch heuristics:
  - `records add` → latest running instance + derived `<stack>.<default-zone>`
  - `records add <fqdn>` → latest instance + given FQDN
  - `records add <i-id|stack-name>` → that instance + derived name
  - `records add <i-id|stack-name> <fqdn>` → both pinned
  - `records add <fqdn> --value <ip>` → explicit-value path (existing)
- Cert-warning info block prints whenever the IP was instance-resolved.
- Idempotency: same-IP exits 0 ("Already correct"); different-IP fails with exit 4 unless `--force`.

### `652bbabe` — Env-gate drop, inline progress, timings, `--latest` fix
- Dropped `SG_AWS__DNS__ALLOW_MUTATIONS=1` requirement from `records add` (user: "we don't need this — confirm is enough; stacks are ephemeral; extra records are cheap"). `update` and `delete` still require the env gate.
- INSYNC poll progress now overwrites a single line with `\r` instead of one row per 2s tick.
- Per-phase timings block printed at the end of `records add` (Instance lookup, Zone resolution, Submit, Wait, Auth check, etc.) — same data in `--json` under a `timings` key.
- **Bug fix**: `--latest` was matching only legacy `sg:*` prefixed tags. Vault-app and other `sg_compute_specs/*` stacks use the new platform tag `Purpose=ephemeral-ec2` (see `sg_compute/platforms/ec2/helpers/EC2__Tags__Builder.py`). The user reported "`sg aws dns records add --wait`" failing with "No running SG-AI instance found" while `warm-bohr` was clearly running. Linker now matches both tag styles.

### `685427d6` — Short aliases + smart i-id+`--value` + friendly errors
- `r`/`z`/`i` sub-typer aliases (matches existing `pw`/`el`/`os`/`va` convention).
- Smart dispatch: `records add i-0717... --value abc.sg-compute.sgraph.ai` now treats `--value` as the FQDN (not the literal record value), since the instance is providing the IP. Previously created `i-0717... A → abc.sg-compute.sgraph.ai.`, which boto3 rejected with `InvalidChangeBatch`.
- `@spec_cli_errors` decorator (the shared `sg_compute` one) wired across all 11 dns + acm commands. Future unhandled boto3 errors render as `✗ InvalidChangeBatch: ...` instead of a 60-line Rich traceback.

### `65a85fba` — `zone` (singular) vs `zones` (plural) + `zone check`
User feedback: "the command should be `zone` since that's what all the actions operate on". Restructure:

```
sg aws dns zones list                       # account-wide: all hosted zones (Name column moved first)
sg aws dns zone show [<zone>]               # zone metadata (default zone)
sg aws dns zone list [<zone>]               # records in zone (replaces records list)
sg aws dns zone check [<zone>]              # NEW: health-check all A records
```

`records list` becomes a hidden alias of `zone list` for backward compat. `zone check` classifies each record:

- `OK` — A record's leftmost label matches a running EC2 Name tag, and the public IP matches
- `STALE` — Name tag matches but IP differs (instance was restarted)
- `ORPHANED` — no running instance has this Name tag
- `UNMATCHED` — multi-label leaf (`api.staging.<zone>`) — never auto-purged
- `IGNORED` — SOA / NS / apex / non-A

### `820fb96b` — `zone purge`
Companion to `zone check`. Reuses the shared `_compute_zone_health` helper; filters to ORPHANED + STALE; shows the preview table; confirms; submits **one** `change_resource_record_sets` ChangeBatch with all `DELETE` actions (Route 53 caps at 1000 changes/batch — well beyond `zone purge`'s practical scale). Flags: `--only orphaned|stale`, `--dry-run`, `--yes`, `--wait`, `--wait-timeout`, `--json`.

New `Route53__AWS__Client.batch_delete_records()` method. Three tests cover the batch path (empty-list error, all-DELETE actions, exact TTL+values preservation).

### `de9cf2e7` — Smarter zone-check classification
User feedback on a real `zone check sgraph.ai` run:

1. **Alias A records (CloudFront / ELB / S3 / API Gateway)** were showing empty value column and being flagged ORPHANED. Wrong on both counts — they route to AWS services, not EC2 instances. Fix: read `alias_target` from the schema (was already there, just not displayed); classify as IGNORED with `alias → CloudFront distribution` / etc. notes.
2. **ACM validation CNAMEs** (the `_<hex>.<zone>` ones) were all `CNAME — not checked` with no way to tell which were active vs orphaned. New `ACM__AWS__Client.get_validation_record_names()` walks both regions, calls `describe_certificate` on every cert, collects every DNS-01 validation record name. `zone check` cross-references; orphaned validation records (cert deleted but CNAME left behind) now become purge candidates.
3. Bonus: pattern-detection for `_domainkey`, `_amazonses`, `_acme-challenge`, TXT `v=DMARC1/v=spf1/v=DKIM1`, `google-site-verification`, MX. All stay IGNORED but the operator sees what each record is for instead of a wall of "CNAME — not checked".

ACM lookup is lazy — only fires when an ACM-shaped CNAME is actually seen in the zone, so a clean sub-zone like `sg-compute.sgraph.ai` doesn't pay for it.

## Good failures

- **Fast iteration loop with the user.** Each commit closed a friction point reported in the prior session. The user pasted real terminal output; I diagnosed → patched → pushed → user re-ran. Six commits in one session, each ≤90 minutes.
- **The cache-pollution math was load-bearing across multiple commits.** `--wait` polls INSYNC (zero pollution); after INSYNC the smart-verify runs the 6-resolver public check (safe for NEW_NAME because the recursive caches are empty for a brand-new record); the verbatim skip-info line for UPSERT/DELETE paths is what tells the operator when it's safe to manually run `--public-resolvers`. No accidental cache-locking shipped.
- **Bug 2 in the zone resolver** (apex-of-child-zone case) caught the user's `--type NS` query within minutes of the Bug 1 fix. The follow-up diagnosis was immediate because the resolver test fixture made the lookup pattern obvious.

## Bad failures

- **Initial dispatch heuristic was too narrow.** First version of `records add i-... --value abc.sg-compute.sgraph.ai`: arg1 = instance-id was correctly detected, but `--value` was still being treated as the record value (an IP). The user got `InvalidChangeBatch` from boto3. Fix in `685427d6` added a special-case: when arg1 is an instance ref AND `--value` is given, `--value` becomes the FQDN. Should have been caught in the original `e4de7848` design.
- **Unhandled exceptions in the wild.** Even after the dispatch fix above, the boto3 error message bubbled up as a Rich traceback (instead of the friendly `✗ InvalidChangeBatch: ...`). The `@spec_cli_errors` decorator existed in `sg_compute/cli/base/` the whole time. Wired in across all 11 commands in `685427d6`. Should have been the default from P0.
- **Default zone change broke 2 unit tests.** When `DEFAULT_ZONE_NAME` flipped from `sgraph.ai` to `sg-compute.sgraph.ai`, the existing tests for `resolve_default_zone` and `_resolve_zone_id` started failing (the fake zones include `sgraph.ai` but not the new default). Fix: tests now set `SG_AWS__DNS__DEFAULT_ZONE=sgraph.ai` in `setUp` to pin the legacy default; a new test class covers the new default + env-override behaviour. Should have been a single global env-var override at the conftest level; instead it's scattered in setUp methods. Minor tech debt.

## Follow-ups

- **`instance create-record` is now redundant** with smart `records add`. Both work; neither has been removed. Decide: hide as a deprecated alias, or remove entirely.
- **§12 ADDENDUM (cert workflow)** unchanged — Q9 (DNS-01 vs HTTP-01) still PENDING. The cert-warning info block printed by `records add` points users at `sg playwright vault re-cert --hostname <fqdn>`, which does not exist yet. This is the highest-value remaining work.
- **`--all-regions` ACM scan** still stubs "not implemented in P0".
- **The bigger CF+R53 brief** (`team/humans/dinis_cruz/claude-code-web/05/15/03/architect__vault-app__cf-route53__plan.md`) still says PROPOSED for primitives that now exist. Update needed.
- **Per-zone reverse lookup** ("which records does instance `i-...` have?") — not in scope today, would be a useful addition for stack-teardown workflows.
