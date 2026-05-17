# Debrief — `sg aws dns` + `sg aws acm` P0 (read-only)

| Field    | Value |
|----------|-------|
| Date     | 2026-05-15 |
| Branch   | claude/add-cf-route53-support-sqeck |
| Commits  | `4f3fc81b` (P0) → `8a4ad6d9` (wire into Cli__SG post-merge) |
| Scope    | new `sgraph_ai_service_playwright__cli/aws/dns/` + `aws/acm/` + `aws/cli/`; one-line wiring in `sg_compute/cli/Cli__SG.py` |
| Tests    | 52 / 52 passing |
| Verified | `python -m sg_compute.cli.Cli__SG --help` lists `aws`; `sg aws dns zones list` lists every Route 53 hosted zone in the dev account; `sg aws acm list` returns certs from current + us-east-1. |

## Scope

P0 is the read-only carve-out from architect brief `team/humans/dinis_cruz/claude-code-web/05/15/08/architect__sg-aws-dns__plan.md`. Six commands shipped:

```
sg aws dns zones list                       # all hosted zones in the account
sg aws dns zones show [<zone>]              # one zone's metadata
sg aws dns records list [<zone>]            # all records in a zone (default sgraph.ai at this stage)
sg aws dns records get <name> [--type A]    # one record
sg aws acm list                             # certs in current region + us-east-1 (dual-region)
sg aws acm show <arn>                       # full cert detail
```

`--json` on every command. `--zone` defaults to `sgraph.ai` (changed later — see post-P1.5 debrief).

## What was built

39 new files, all under `sgraph_ai_service_playwright__cli/aws/`:

| Layer | File count | Notes |
|-------|-----------:|-------|
| Service clients | 2 | `Route53__AWS__Client`, `ACM__AWS__Client`. Raw boto3 with documented exception headers (matches `Elastic__AWS__Client` precedent — no osbot-aws Route53 wrapper exists). |
| Schemas         | 3 | `Schema__Route53__Hosted_Zone`, `Schema__Route53__Record`, `Schema__ACM__Certificate`. All `Type_Safe`. |
| Enums           | 3 | `Enum__Route53__Record_Type`, `Enum__ACM__Cert_Status`, `Enum__ACM__Cert_Type`. |
| Primitives      | 4 | `Safe_Str__Hosted_Zone_Id`, `Safe_Str__Domain_Name` (incl. wildcard `*.`), `Safe_Str__Record_Name` (multi-label RFC 1035), `Safe_Int__TTL`. |
| Collections     | 3 | `List__Schema__Route53__Hosted_Zone`, `List__Schema__Route53__Record`, `List__Schema__ACM__Certificate`. |
| CLI surfaces    | 3 | `Cli__Dns`, `Cli__Acm`, parent `Cli__Aws`. |
| Tests           | 2 | 22 + 21 cases. In-memory `_Fake_*_Boto3_Client` subclasses — no mocks, no patches. |

Naming follows Option B (CLI-side `__cli/aws/{dns,acm}/`) — see Q1 in the brief. The misconception "is `sgraph_ai_service_playwright__cli/` legacy?" is addressed in the brief itself: it is NOT — see `team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md`.

## Good failures

- **Caught the entry-point shift mid-flight.** During P0 implementation I wired the `aws` Typer sub-app into `scripts/provision_ec2.py:854`. While I was working, `origin/dev` shipped `sg_compute/cli/Cli__SG.py` as the new aggregator and `pyproject.toml` moved every `sg` / `sgc` / `sg-compute` / `sp` console script to `sg_compute.cli.Cli__SG:app`. Detected on `git merge origin/dev` by spotting the new file and verifying with `python -m sg_compute.cli.Cli__SG --help` — `aws` was absent. Fixed in `8a4ad6d9` by moving the `add_typer` to `Cli__SG.py` and dropping the dead line from `provision_ec2.py`. Without that catch, `sg aws` would have shown nothing despite the code being correct.
- **`Safe_Str__Domain_Name` permissive on the first test failure.** Initial regex rejected wildcard certs like `*.sgraph.ai`. Test caught it; regex extended with optional leading `(\*\.)?`. ACM enumeration would otherwise have crashed on the first wildcard cert.

## Bad failures

- **Three minor spec deviations decided unilaterally** (all defensible, but should have been flagged for ratification):
  1. `Schema__Route53__Record.ttl` is plain `int` (not `Safe_Int__TTL`) — alias records have `ttl=0`, which a `min_value=1` primitive would reject. `Safe_Int__TTL` is still used in P1 mutation method signatures.
  2. `Safe_Str__Domain_Name` accepts wildcard prefix.
  3. `_default_zone` cache attribute uses an underscore prefix. CLAUDE.md rule #9 covers methods, not attributes — but worth a re-read if someone is strict on it.

## Follow-ups

- **Brief still says PROPOSED** at the top. Updated in this catch-up pass — see post-P1.5-ergonomics debrief.
- **Reality doc entry filed** — `team/roles/librarian/reality/v0.1.31/16__sg-aws-dns-and-acm.md` (this catch-up pass).
- **Mutations + verification + cert flow** — see P1, P1.5, post-P1.5 debriefs.
