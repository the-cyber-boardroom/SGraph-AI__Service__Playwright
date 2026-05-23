---
title: "SG/Sentinel MVP — Testing Manual (`sg sentinel *`)"
date: 2026-05-23
status: DRAFT
audience: "Anyone testing the SG/Sentinel MVP locally or on AWS"
scope: "How to exercise every `sg sentinel` command across the three targets"
---

# SG/Sentinel MVP — Testing Manual

This manual shows how to test the SG/Sentinel MVP end to end using the `sg sentinel`
(alias `sn`) CLI. It covers all three targets: **local-direct** (node), **local-docker**
(CloudFront-environment simulation), and **live AWS** (CloudFront Function + Lambda@Edge).

The MVP is **CLI-first** — there is **no TUI** (deferred by design). Every command
supports `--json` so a TUI or script can sit on top later.

## 0. Prerequisites

| Need | For which target | Check |
|------|------------------|-------|
| Python 3.12 venv with deps installed | all | `pip install -r requirements.txt` |
| `node` on PATH | local-direct, docker build, all parity | `node --version` |
| `docker` daemon running | local-docker only | `docker info` |
| AWS creds + mutation gate | live AWS only | `aws sts get-caller-identity` |

```bash
# one-time local setup
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt pytest
```

The local sink location is overridable (keeps `$HOME` clean during tests):

```bash
export SG_SENTINEL__LOCAL_SINK_DIR=$(mktemp -d)      # where logs/blocks read & write
```

## 1. The command surface

```
sg sentinel rules   list | show <id> | test          # the six tiny-core rules
sg sentinel local   up [--docker] | hit <m> <path> [--ip] [--docker] | down [--docker]
sg sentinel logs    ls | tail [-n N] | trace <request-id>      # use case 1 (read the sink)
sg sentinel blocks  list | why <request-id|ip>                 # use case 2
sg sentinel deploy  create | destroy <id> | teardown <id>      # live AWS (mutation-gated)
sg sentinel status                                             # what's deployed
```
Every command accepts `--json`. Mutating deploy commands accept `--yes` / `--dry-run`.

## 2. Rules — see the engine without running it

```bash
sg sentinel rules list                 # table of the 6 MVP rules (id, name, action, MITRE tag)
sg sentinel rules show 0012            # one rule's metadata
sg sentinel rules test                 # runs the real node L1 engine over the canonical set
sg sentinel rules test --json          # same, machine-readable
```

Expected `rules test` decisions (the canonical request set):

| Method | Path | Source IP | Verdict | Rule | Action |
|--------|------|-----------|---------|------|--------|
| GET | `/index.html`   | 198.51.100.2 | allow | 0001 | pass |
| GET | `/etc/passwd`   | 185.10.10.10 | block | 0012 | drop_403 |
| GET | `/wp-login.php` | 91.20.20.20  | block | 0018 | deflect_404 |
| GET | `/.env`         | 77.30.30.30  | block | 0014 | deflect_404 |
| GET | `/index.html`   | 10.0.0.6     | block | 0003 | drop_403 |
| GET | `` (empty)      | 203.0.113.5  | block | 0007 | drop_403 |

## 3. Target B — local-direct (offline, no AWS)

This runs the **real** L1 JS engine (via node) + the **real** Python L2 actor in-process,
writing to a local-FS sink. Both MVP use cases work fully offline.

```bash
sg sentinel local up                                  # checks node + ensures the sink dir

# use case 2 — blocking (obvious-bad)
sg sentinel local hit GET /etc/passwd   --ip 185.10.10.10   # → block, rule 0012, HTTP 403
sg sentinel local hit GET /wp-login.php --ip 91.20.20.20    # → block, rule 0018, HTTP 404
sg sentinel local hit GET /.env         --ip 77.30.30.30    # → block, rule 0014, HTTP 404
sg sentinel local hit GET /index.html   --ip 10.0.0.6       # → block, rule 0003 (banned ip)

# use case 1 — logging (real-time visibility)
sg sentinel local hit GET /index.html   --ip 198.51.100.2   # → allow, rule 0001, pass to origin

# read the sink
sg sentinel logs ls                                   # every record
sg sentinel logs tail -n 5
sg sentinel logs trace <request-id>                   # the full replayable record (from `hit` output)
sg sentinel blocks list                               # only the blocked requests + reason
sg sentinel blocks why 185.10.10.10                   # look up by the raw IP you used (matches the hashed store)

sg sentinel local down                                # clears the local sink
```

Notes:
- `local hit` prints the `request_id`, verdict, rule, reason, and enforcement.
- Source IP is **hashed** in the stored record by default (privacy mode). `blocks why <ip>`
  understands both the raw IP and its hashed form.

## 4. Target C — local-docker (CloudFront-environment simulation)

Requires a running Docker daemon. Builds a Node container that runs the **same**
`sentinel_l1.js` behind a tiny HTTP listener; the harness POSTs requests at it and runs
the same Python L2 on the result.

```bash
sg sentinel local up   --docker        # builds image + starts the container (CF-env sim)
sg sentinel local hit  --docker GET /etc/passwd --ip 185.10.10.10   # routed via the container
sg sentinel logs ls                    # same sink as direct mode
sg sentinel local down --docker        # stops the container
```

If `docker info` fails, these commands tell you the daemon isn't reachable and exit.

## 5. Target A — live AWS (ephemeral CloudFront + Lambda@Edge)

Mutation-gated. **Costs money and creates real AWS resources** — use an ephemeral test
distribution and always `teardown`.

```bash
export SG_AWS__SENTINEL__ALLOW_MUTATIONS=1            # required for create/destroy/teardown
eval $(sg aws credentials switch <role>)              # real creds in this shell

# preview first (no AWS calls)
sg sentinel deploy create --dry-run --region us-east-1

# provision: S3 log bucket + CF Function (L1, viewer-request) + Lambda@Edge (L2, origin-request),
# on a cache-disabled distribution so every request reaches L2.
sg sentinel deploy create --region us-east-1 --yes

sg sentinel status                                    # L1 present? L2 present?

# the distribution takes ~15 min to deploy globally; then curl it (domain from `status`/the create output):
curl -sI https://<dXXXX>.cloudfront.net/etc/passwd    # → HTTP/2 403
curl -sI https://<dXXXX>.cloudfront.net/.env          # → HTTP/2 404
curl -sI https://<dXXXX>.cloudfront.net/index.html    # → 200 / origin

# logs land in S3 — read them with the same sink layout as local (one object per request)
sg aws s3 ls s3://<log-bucket>/sentinel/

# tear everything down — no orphans (empties + deletes the bucket too)
sg sentinel deploy teardown <distribution-id> --bucket <log-bucket> --yes
```

Live gotchas the deployer handles for you: Lambda@Edge must be authored in **us-east-1**,
deployed as a **numbered version** (not `$LATEST`), with an execution role trusted by both
`lambda.amazonaws.com` and `edgelambda.amazonaws.com`; teardown **polls** for the async
replica deletion before removing the function.

## 6. The automated test suite

```bash
. .venv/bin/activate

# everything (local-direct + in-memory AWS lifecycle); docker/live legs skip cleanly
python -m pytest tests/unit/sgraph_ai_service_playwright__cli/sentinel/ -q -rs

# the three-target parity matrix (local-direct baseline always runs)
python -m pytest tests/unit/sgraph_ai_service_playwright__cli/sentinel/parity/ -q -rs
```

Opt-in legs:

| Leg | Enable with |
|-----|-------------|
| B↔C docker parity | a running docker daemon |
| AWS parity | `SG_SENTINEL__LIVE_TESTS=1` + `SENTINEL_TEST_DISTRIBUTION=<cf-domain>` |
| Live smoke (deploy→curl→teardown) | `SG_SENTINEL__LIVE_TESTS=1` + `SG_AWS__SENTINEL__ALLOW_MUTATIONS=1` |

## 7. What is NOT in the MVP (don't look for it)

Fingerprint/fast-track; any rule evaluation at L2; Layer 3 / LLM; fractal-graph traversal;
rules-as-vault; evidence/compliance graphs; threat-intel; multi-CDN; cache-hit logging;
log batching; IP-escrow privacy mode; and **the TUI** (CLI-first for the MVP).
