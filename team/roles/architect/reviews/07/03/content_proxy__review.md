---
title: "Review — content_proxy spec (correctness, security, docs freshness)"
file: content_proxy__review.md
author: Reviewer (Claude Fable 5)
date: 2026-07-03
repo: SGraph-AI__Service__Playwright @ claude/trusting-franklin-fza33n (v0.2.65 line)
scope: sg_compute_specs/content_proxy/ — full package (service, cli, schemas, enums, interceptors, traffic, tui, docker, manifest) + reality doc
status: REVIEW — 183 unit tests green. Two quick fixes applied this pass; the rest are flagged for a decision.
---

# Review — content_proxy spec

## Verdict

**Structurally sound and unusually well-tested for pure logic; the one systemic weakness is a local-vs-EC2 credential asymmetry.** The diagnose parsers, `sg_rules`, `realize_secrets`, the mapper, and the compose/user-data/edge renders all have focused unit coverage (183 tests, no mocks). Type_Safe / no-Literal / one-class-per-file conventions hold; enum values line up with the interceptor's action strings; the SG name (`cp-<stack>`) correctly avoids the reserved `sg-` prefix (rule 14). No data-loss or RCE-class defects.

The recurring theme: **the CLI's `realize_secrets` is the only thing that couples the access-token pair and fills proxy-auth, and none of it runs on the EC2 `create` path.** That gap produced two of the most field-relevant findings (a "stack is up but auth is broken" class of incident).

## Correctness findings (verified)

| # | Sev | Finding | Status |
|---|-----|---------|--------|
| 1 | MED | **EC2 `create` shipped `proxyauth=:`** (empty) on the internet-facing ext proxy unless `--proxyauth-*` was passed — no `realize_secrets` on the EC2 path. | **FIXED** — `resolve_proxyauth()` defaults user `demo` + generates a GUID pass; surfaced once in the create banner. |
| 2 | MED | **`--env-file` bypasses the access-token coupling guard.** A shipped `.env` with divergent `FAST_API__AUTH__API_KEY__VALUE` / `SGRAPH_SEND__ACCESS_TOKEN` deploys as-is → `/pw` "Invalid API key value", unguarded server-side. Also, the create response/`cp:access-token` tag can show a random uuid that doesn't match the box when the env-file defines neither. | **FLAGGED** — needs the coupling/realize logic run over `env_inline` before shipping, and the response token derived from the shipped env. |
| 3 | MED | **`--proxy-ca-cert` / `--proxy-ca-key` are no-ops.** Only `--ca-from-local` (→ `proxy_ca_pem`) ships a CA; a supplied `--proxy-ca-cert <path>` just emits a comment, `--proxy-ca-key` is never read. Operator gets an untrusted self-generated CA instead of their file. | **FLAGGED** — read+ship the cert/key (mitmproxy wants cert+key in one PEM), or remove the misleading flags. |
| 4 | MED (sec) | **`cp:access-token` tag holds the live bearer token** in plaintext EC2 metadata (readable via `ec2:DescribeTags`, CloudTrail, cost exports). By-design parity with `sg va`, but still a secret in metadata. | **FLAGGED** — decide: keep (documented) or recover `info`'s token from the box `.env` over SSM instead of tagging. |
| 5 | LOW | ~~No drift guard for `docker-compose.caddy.yml`~~ | **DISMISSED (false positive)** — the guard exists: `test_Content_Proxy__Edge.py::test_committed_caddy_files_no_drift`. |
| 6 | LOW | Dead `acme_email` computation in `_caddy_block` (computed, then `render(acme_email='')`). | **FIXED** — removed. |
| 7 | LOW | `boot_log_failed` markers (`'failed to'`, `'cannot '`) can match benign docker-pull noise → `check`/`wait` can spuriously fail during the in-progress boot window (cleared once `[content-proxy] boot complete` lands). | **FLAGGED** — tighten markers, or only treat as failure once boot has stalled. |

## Documentation freshness — was stale, now refreshed

The reality doc (`team/roles/librarian/reality/content-proxy/index.md`) was materially out of date: header dated 2026-06-18, claimed the code was *"not yet merged to dev"*, cited *118 tests*, undercounted the enum/primitive lists, and never mentioned this session's surface (`diagnose`/`check`/`wait`, `logs`, `block_global`, always-set `AWS_ACCOUNT_ID`, scripts-bucket inheritance, the `SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS` + `realize_secrets` fixes). **Refreshed this pass** — header, enum/primitive/schema/CLI corrections, new "Boot diagnostics" + "Credential / env plumbing" + "Known gaps / open bugs" sections, and a corrected PROPOSED (SELF_SIGNED/LETSENCRYPT are wired; only ACM remains).

Still owed (not done here):
- **Spec doc `v0.2.63__content-transformation-proxy-stack.md`** status line still reads *"No code here yet"* — flatly false; needs a status bump to as-built.
- **No debrief** exists for this session's content_proxy work (rule 26). One is owed under `team/claude/debriefs/`.
- **`manifest.create_endpoint_path='/api/specs/content_proxy/stack'`** advertises a route that doesn't exist (`api/routes/` is empty) — a claim-vs-reality gap to either build or drop.

## Recommended next steps (ranked)

1. **Fix #2 (env-file coupling)** — highest field risk after #1; the guard that prevents "up but auth broken" must also run server-side.
2. **Resolve #3** — either wire `--proxy-ca-cert/--key` or delete them; a flag that silently does nothing is worse than no flag.
3. **Decide #4** — token-in-tag is a deliberate trade-off; make it an explicit, documented decision (or move to SSM read).
4. **The integration tier** (still the standing P1 from the prior architect review) — all 183 tests are pure unit; every live bug this cycle (auth chain, `block_global`, cert trust) fell into the no-integration blind spot. A gated `docker compose up` smoke + numbered deploy-via-pytest is the highest-leverage remaining work.
5. **Doc hygiene** — bump the spec-doc status, write the session debrief, resolve the manifest route claim.
