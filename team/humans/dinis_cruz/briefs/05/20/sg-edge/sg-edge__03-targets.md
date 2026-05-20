---
title: SG/Edge — vault targets & Vault Waker
date: 2026-05-20
status: design / pre-MVP
audience: implementing engineer (or next Claude thread) picking up the work
scope: the target tier — vault backends (EC2 / Fargate) and the Vault Waker
related:
  - sg-edge__01-solution-overview.md
  - sg-edge__02-edge-fleet.md
  - sg-edge__05-mvp-test-and-acceptance.md
---

# Scope

This document covers the vault target tier — the actual EC2 instances or Fargate tasks that run the vault application — and the changes needed in the Vault Waker (existing `sg va` / `sg vp`) for them to work behind SG/Edge.

```
       (SG/Edge fleet)               (this document)
              |                              |
              v                              v
   +------------------+         +-----------------------+
   |   OpenResty      |  ----->  |   Vault target        |
   |   proxy          |  HTTP   |   EC2 or Fargate      |
   |                  |  :8080  |   plain HTTP :8080    |
   +------------------+         +-----------------------+
                                          ^
                                          |  provisions
                                          |
                                +-----------------------+
                                |    Vault Waker        |
                                |   (sg va / sg vp,     |
                                |    existing + diffs)  |
                                +-----------------------+
```

Two components: the vault backend (mostly unchanged from today) and the Vault Waker (small additive changes).

# What changes from current state

The good news: the vault target itself barely changes. The Vault Waker gets small additions, not a rewrite.

| Aspect | Today | Behind SG/Edge |
|---|---|---|
| TLS on vault | `letsencrypt-ip` / `letsencrypt-hostname` / `self-signed` cert via cert-init | None. Plain HTTP `:8080`. cert-init container removed from boot path |
| DNS records | A record only: `<slug>.<parent>` -> EC2 public IP | A + TXT: `<slug>.<parent>` -> CloudFront (registration receipt), `_sg.<slug>.<parent>` -> backend runtime metadata |
| Boot time | ~30-90s (EC2) or ~20-30s (Fargate) | Same, minus cert-init overhead (~10-20s saved on EC2) |
| LE rate limits | 50/week per registered domain — the constraint that started this | Gone. No LE involvement at all |
| Vault encryption | Browser AES-GCM, requires HTTPS (secure context) | Same. HTTPS terminates at CF, browser still sees HTTPS |
| Per-vault config | TLS mode + cert-init env | TLS mode dropped from spec; everything else identical |

The cert-init container is the biggest single deletion. `Vault_App__User_Data__Builder` no longer needs to inject ACME credentials, cert paths, FQDN hints, or LE staging flags. The vault simply binds nginx (or whatever serves the vault SPA) to plain HTTP on `:8080`.

# Vault backend internals — EC2 variant

```
+-----------------------------------------------------------------------+
|                      EC2 instance (t3.medium)                         |
|                       <slug>.<parent>.<domain>                        |
|                                                                       |
|   +-----------------------------+   +-----------------------------+   |
|   |       Vault app             |   |     (removed) cert-init     |   |
|   |       nginx :8080           |   |     (removed) cert-renew    |   |
|   |       plain HTTP            |   |     (removed) Vault         |   |
|   |                             |   |       Heartbeat             |   |
|   |   Serves the vault SPA      |   |                             |   |
|   |   browser AES-GCM crypto    |   |  No more ACME. No more LE.  |   |
|   |   happens in the browser    |   |  No more :443 binding.      |   |
|   |   over HTTPS (terminated    |   |  No SSM heartbeat - the     |   |
|   |   at CF), so secure context |   |  edge proxies track         |   |
|   |   guarantee holds           |   |  liveness in memory         |   |
|   |                             |   |  (see doc 02).              |   |
|   |   Serverless_Fast_API mware |   +-----------------------------+   |
|   |   validates X-API-Key on    |                                     |
|   |   every inbound request    |                                     |
|   |   (rejects without key)     |                                     |
|   +-----------------------------+                                     |
|              ^                                                        |
|              |                                                        |
|              | inbound only from proxy IPs (security group)           |
|              | AND with valid X-API-Key header                        |
|              |                                                        |
|   +-----------------------------+                                     |
|   |  IAM instance role          |                                     |
|   |  - logs:PutLogEvents        |                                     |
|   |  - cloudwatch:PutMetricData |                                     |
|   |                             |                                     |
|   |  NO ssm:* permissions       |                                     |
|   |  (no heartbeat to write)    |                                     |
|   +-----------------------------+                                     |
+-----------------------------------------------------------------------+
                                |
                                | inbound from proxy IPs only
                                | (security group rule)
                                | + X-API-Key validated by
                                |   Serverless_Fast_API middleware
```

Security group note: the vault's `:8080` should NOT be open to `0.0.0.0/0`. It accepts traffic only from the SG/Edge proxy security group. The Vault Waker writes this rule when provisioning; the Edge Waker maintains the proxy SG. This means even if someone learns a vault's public IP, they can't bypass the edge — connections from outside the proxy SG are dropped at the network layer.

API key note: in addition to the network-layer restriction, the vault target validates an `X-API-Key` header using the existing `Serverless_Fast_API` middleware. The proxy injects this header on every upstream proxy_pass (the key value comes from a `SERVERLESS_FAST_API_KEY` env var set at proxy boot). This is defense-in-depth — the SG rule and the API key check are independent layers, and the API key check works identically when running locally (no security group), so local Phase 1 testing uses the same auth path as production.

# Vault backend internals — Fargate variant

Functionally identical to EC2:

```
+-----------------------------------------------------------------------+
|                       Fargate task (0.5 vCPU)                         |
|                                                                       |
|   +-----------------------------+                                     |
|   |       Vault app             |                                     |
|   |       nginx :8080           |                                     |
|   |       plain HTTP            |                                     |
|   |                             |                                     |
|   |   Serverless_Fast_API mware |                                     |
|   |   validates X-API-Key       |                                     |
|   +-----------------------------+                                     |
|                                                                       |
|   Task role: same minimal IAM as EC2 variant (no SSM)                 |
|   Networking: awsvpc mode, security group from sg edge proxies only   |
+-----------------------------------------------------------------------+
```

The Fargate path was the original motivator (no cert-init existed for Fargate, hence the brief). Now there's nothing to add — Fargate gets the same plain-HTTP shape as EC2, no special-casing.

# DNS records per slug — distinct lifecycles

Each slug has *two* DNS records that the Vault Waker manages, but they belong to different lifecycles:

```
+-------------------------------------------------------------------+
|        A record — REGISTRATION lifecycle (long-lived)             |
+-------------------------------------------------------------------+
|                                                                   |
|  alice.cv.sgraph.ai           A   d123abc.cloudfront.net          |
|     ^ ALIAS to CloudFront      (alias - effectively CNAME for     |
|     ^ TTL 60s                   apex-safe records)                |
|                                                                   |
|  WRITTEN when:    slug is first allocated to a customer           |
|  REMOVED when:    customer offboards / deletes the slug           |
|  NOT changed:     when vault starts/stops/restarts                |
|                                                                   |
+-------------------------------------------------------------------+

+-------------------------------------------------------------------+
|         TXT record — RUNTIME lifecycle (ephemeral)                |
+-------------------------------------------------------------------+
|                                                                   |
|  _sg.alice.cv.sgraph.ai       TXT  "v=1;ip=10.0.1.5;port=8080;    |
|     ^ The runtime pointer          type=ec2;launched=1747700000;  |
|     ^ TTL 30s                      instance=i-0abc123def"         |
|     ^ Read by OpenResty                                           |
|                                                                   |
|  WRITTEN when:    vault target boots and binds :8080              |
|  UPDATED when:    vault's IP changes (EC2 stop/start) or backend  |
|                   is replaced                                     |
|  REMOVED when:    vault terminates (clean) or Reaper detects      |
|                   the instance is gone (cleanup)                  |
|                                                                   |
+-------------------------------------------------------------------+
```

The proxy interprets the combination:

```
+----------------+----------------+-------------------------------+
|  A record      |  TXT record    |  Proxy behavior               |
+----------------+----------------+-------------------------------+
|  Missing       |  Missing       |  "slug not recognised" page   |
|                |                |  (unknown slug)                |
|                |                |                                |
|  Missing       |  Present       |  IMPOSSIBLE if Vault Waker     |
|                |                |  is correct; reaper should     |
|                |                |  remove the orphan TXT         |
|                |                |                                |
|  Present       |  Missing       |  Trigger Vault Waker (wake);   |
|                |                |  serve loading page            |
|                |                |  (registered but inactive)     |
|                |                |                                |
|  Present       |  Present       |  Reverse-proxy to TXT's        |
|                |                |  ip:port (warm path)           |
+----------------+----------------+-------------------------------+
```

The four scenarios where A exists but TXT doesn't are:

1. **New slug just registered.** Customer signed up, slug allocated, A written. No vault has been provisioned because no one has visited the URL yet.
2. **Slug exists but has never been opened.** Same observable state as (1), just longer elapsed time.
3. **Vault's EC2/Fargate instance has terminated.** Could be clean termination (customer shut it down → Vault Waker removes TXT) or unexpected loss (spot interruption → Vault Waker's termination handler removes TXT, or Reaper catches up later).
4. **Reaper cleaned up an orphaned TXT.** Reaper found A+TXT both present but the instance the TXT pointed at was gone. Reaper removed TXT, left A alone.

All four are observably identical from the proxy's perspective: trigger the Vault Waker, serve loading page. The waker has the operational intelligence to figure out which kind of wake is needed.

## TXT record schema

Version-prefixed to allow evolution. v=1 fields:

| Field | Required | Format | Example | Purpose |
|---|---|---|---|---|
| `v` | yes | integer | `1` | schema version |
| `ip` | yes | IPv4 | `10.0.1.5` | backend address |
| `port` | yes | uint16 | `8080` | backend port |
| `type` | yes | enum | `ec2` / `fargate` | informational, lets proxy adjust behavior if needed |
| `launched` | yes | unix ts | `1747700000` | for staleness detection |
| `instance` | no | string | `i-0abc123def` | for ops, not used by proxy |

Parsing: simple `key=value;key=value` format. Stays under DNS TXT 255-char limit. Resist the temptation to put JSON in there — it works but is harder to debug from `dig` output.

# Slug state machine

Slugs have a clear lifecycle. Only the Vault Waker can transition them between states.

```
       +-----------------+
       |  unprovisioned  |  <-- no DNS records exist
       +-----------------+
              |
              | customer signs up for a slug
              | Vault Waker writes A record
              v
       +-----------------+
       |   registered    |  <-- A exists, TXT doesn't
       +-----------------+      ("dormant" - no backend yet)
              |
              | first request arrives
              | Vault Waker provisions backend
              v
       +-----------------+
       |  provisioning   |  <-- backend booting, TXT not yet written
       +-----------------+
              |
              | backend healthy + TXT written
              v
       +-----------------+    idle (no req for X min)
       |     active      |  -------------------------+
       +-----------------+                           |
              ^                                      v
              | first request                +----------------+
              | wakes it                     |   stopped or   |
              |                              |  TXT removed   |
              |                              |  (back to      |
              +------------------------------|  "registered") |
                                             +----------------+
                                                    |
                                                    | sg va offboard
                                                    | Vault Waker removes A
                                                    v
                                            (unprovisioned)
```

The `registered` state is the new one — it doesn't exist in today's design. With SG/Edge, a slug can be allocated (A record exists, customer owns it) without any backend running yet. The first visit triggers provisioning naturally.

For Fargate slugs the state machine collapses slightly because there's no "stopped" — tasks are running or terminated. Wake-from-stopped is replaced by "provision a new task" from the proxy's perspective, but Vault Waker handles both paths transparently.

# Cold-vault sequence (waking a registered slug)

This is the *second* layer of cold start, distinct from the cold-cold proxy fleet boot covered in `sg-edge__02-edge-fleet.md`. The two layers overlap (parallel-boot optimization) when both happen simultaneously, but each can also happen independently.

```
User    Proxy (OpenResty)    Vault Waker     EC2 API     Route 53
 |             |                  |              |           |
 |---req------>|                  |              |           |
 |             |                  |              |           |
 |             | A lookup -> exists              |           |
 |             | TXT lookup -> NXDOMAIN          |           |
 |             |                  |              |           |
 |             |---trigger-------->|             |           |
 |             |   (async HTTP    |              |           |
 |             |    to waker fn   |              |           |
 |             |    URL)          |              |           |
 |             |                  |              |           |
 |<-loading----|                  |              |           |
 | page        |                  |              |           |
 |             |                  |--RunInstances-->         |
 |             |                  |              |           |
 |             |                  | (poll EC2 API + probe    |
 |             |                  |  vault :8080 /health for |
 |             |                  |  readiness)              |
 |             |                  |              |           |
 |        ...30-90s boot time...                             |
 |             |                  |              |           |
 |             |                  |<-running-----|           |
 |             |                  |                          |
 |             |                  | (get IP from instance md)|
 |             |                  |                          |
 |             |                  |--write _sg.<slug> TXT--->|
 |             |                  |<-ok----------------------|
 |             |                  |                          |
 |   (client polls /_edge/wait-status until proxy sees TXT)  |
 |             |                                              |
 |   loading page reloads when TXT is visible                |
 |             |                                              |
 |<------- (warm path now works) -----------------------> | 
```

A few important properties of this flow:

1. **The TXT record is the readiness signal.** OpenResty's `/_edge/wait-status` endpoint just checks TXT cache — if TXT exists, the slug is ready (with the implicit assumption that if Vault Waker wrote TXT, the backend was healthy at write time).
2. **TXT NXDOMAIN cache TTL is short (5s).** This means the proxy notices the freshly-written TXT within seconds of the Vault Waker writing it.
3. **The Vault Waker also handles EC2 IP changes.** If the EC2 instance previously existed and was stopped, starting it might give a different IP. Vault Waker writes the *new* TXT with the new IP; the proxy invalidates its cache on the next 502 from the old IP (or on the 30s TXT-found TTL expiring, whichever comes first).

# Cleanup, orphans, and the Vault Reaper

The architecture's main failure mode is orphaned DNS records — entries whose backends are gone. Two places this can happen:

| Failure | Symptom | Mitigation |
|---|---|---|
| Vault Waker crashes mid-provision | Backend running but TXT not written | Vault Waker writes TXT only after backend is healthy; if crash before TXT, backend is orphaned (Reaper detects via instance state + proxy in-memory data) |
| EC2 / Fargate dies unexpectedly | TXT exists, backend gone | Reaper detects via EC2 API state + absence of recent activity in proxy `slug_seen` |

## Liveness source-of-truth: the proxies themselves

Rather than have vault targets phone home (the older "vault writes SSM heartbeat" design), liveness is tracked by the SG/Edge proxies in memory. Every successful upstream proxy_pass updates `slug_seen[slug] = now()` in the proxy's shared_dict. Each proxy exposes its full `slug_seen` map via `/_edge/slug_seen` (see `sg-edge__02-edge-fleet.md`).

Why this is the right place for the data:
- Proxies are the long-lived components that already see every request — they have the data anyway
- No new code on the vault target (no systemd timer, no SSM permissions, no extra failure modes)
- Works identically locally (proxies have shared_dict in any deployment; SSM is AWS-only)
- One less moving part — the heartbeat *is* the proxy traffic itself

The Reaper unions `slug_seen` data across all live proxies in the fleet, then makes its decisions.

## Reaper logic

```
+---------------------------------------------------------------+
|                         Vault Reaper                          |
+---------------------------------------------------------------+
|                                                               |
|  Every 5 minutes:                                             |
|                                                               |
|  1. Collect liveness data                                     |
|       a. List all proxies (Route 53: proxies.<parent>)        |
|       b. For each proxy: GET /_edge/slug_seen                 |
|       c. Union the maps -> {slug: max(last_seen_ts)}          |
|                                                               |
|  2. List all _sg.* TXT records in managed zones               |
|                                                               |
|  3. For each TXT record:                                      |
|       a. Parse TXT, get instance/task identifier              |
|       b. Check EC2/Fargate API for instance state             |
|       c. Look up slug in unioned slug_seen map                |
|       d. If instance state == terminated/stopped/missing      |
|          OR (last_seen older than 10 minutes                  |
|              AND TXT launched > 5 min ago):                   |
|             remove _sg.<slug> TXT record                      |
|             log + emit metric                                 |
|                                                               |
|  IMPORTANT: Reaper only ever touches TXT records.             |
|  It NEVER removes A records (those are owned by the           |
|  registration lifecycle, not the runtime lifecycle).          |
|                                                               |
|  Special case: fleet at zero (no proxies up).                 |
|  Reaper has no slug_seen data and cannot judge liveness.      |
|  It either skips this cycle entirely OR relies on             |
|  EC2/Fargate API state only (no false-positive risk since     |
|  "terminated" is unambiguous).                                |
|                                                               |
+---------------------------------------------------------------+
```

The Reaper is conservative — false negatives (failing to reap an orphan) are fine, false positives (reaping a live vault) are damaging. The unioned `slug_seen` view across all proxies provides the redundant signal: a slug is only deemed dead if *no* proxy has successfully reached its backend in the window AND the EC2/Fargate API confirms the instance is gone.

A nice property: if the proxy fleet is torn down entirely (scale-to-zero), orphan cleanup naturally pauses. That's fine — orphans are only worth cleaning up when traffic is flowing anyway, and the moment a proxy boots and the Reaper runs, normal cleanup resumes. In the meantime, an orphan TXT is self-correcting: the next user to hit the slug will get a 502 from the dead backend, the proxy will mark it unhealthy and trigger Vault Waker, Vault Waker will rebuild and rewrite the TXT.

The clean separation here is important: **Reaper is the runtime-state janitor; never the registration janitor.** Removing an A record is a customer-impacting operation (offboards their slug); it's only ever done explicitly by Vault Waker on `sg va offboard <slug>`, never automatically.

# IAM model

The Vault Waker needs slightly different permissions than today:

```
+-------------------------------------------------------------+
|                  Vault Waker IAM (additions)                |
+-------------------------------------------------------------+
|  EXISTING:                                                  |
|    - ec2:RunInstances, ec2:TerminateInstances               |
|    - ec2:DescribeInstances                                  |
|    - ec2:StartInstances, ec2:StopInstances (wake)           |
|    - ecs:RunTask, ecs:StopTask (Fargate)                    |
|    - ecs:DescribeTasks (poll for Fargate IP after RUNNING)  |
|    - iam:PassRole (vault instance role)                     |
|    - route53:ChangeResourceRecordSets (slug zones)          |
|                                                             |
|  NEW (small additions):                                     |
|    - route53:ChangeResourceRecordSets (_sg.* records too)   |
|                                                             |
|  REMOVED (the cert-init permissions go away):               |
|    - acm:* (was used for cert-init validation)              |
|    - secretsmanager:GetSecretValue (LE account)             |
|                                                             |
|  NOT needed:                                                |
|    - ssm:* (no SSM heartbeat in this design)                |
+-------------------------------------------------------------+
```

The Vault Reaper has its own minimal IAM:

```
+-------------------------------------------------------------+
|                    Vault Reaper IAM                         |
+-------------------------------------------------------------+
|    - route53:ListResourceRecordSets (read TXT records)      |
|    - route53:ChangeResourceRecordSets (delete TXT only)     |
|    - ec2:DescribeInstances                                  |
|    - ecs:DescribeTasks                                      |
|    - (the Reaper queries proxies' /_edge/slug_seen via HTTP |
|       - no AWS perms needed for that)                       |
|                                                             |
|    NO ec2:RunInstances (cannot launch)                      |
|    NO ec2:TerminateInstances (cannot terminate)             |
|    NO route53 writes on apex A records (only _sg.* TXT)     |
+-------------------------------------------------------------+
```

The Vault Waker continues to have no edge permissions — it can't modify `proxies.<parent>` records or touch the Edge Waker's resources. The blast-radius separation is symmetric.

The vault instance role itself is smaller than today (no ACM, no Secrets Manager for cert key, no SSM heartbeat, no Route 53 — those were either unused or moved to Vault Waker, or eliminated entirely).

# Changes to existing modules

For an implementing engineer working from the existing `sg_compute_specs/` tree:

| File | Change |
|---|---|
| `vault_app/service/Vault_App__Service.py` | Remove `tls_mode` parameter from `create_stack`. Always plain HTTP. Add TXT record write to the readiness gate; A record write is now conditional (only on first allocation, not on every wake) |
| `vault_app/service/Vault_App__User_Data__Builder.py` | Remove cert-init container env injection. Remove ACME credentials. Remove FQDN propagation logic. Remove Vault Heartbeat systemd timer setup |
| `vault_publish/service/Vault_Publish__Service.py` | Remove `tls_mode=letsencrypt-hostname` path. Slug registration now writes A pointing at CloudFront, not direct to EC2 |
| `vault_app/fargate/service/Vault_App__Fargate__Setup.py` | Remove the TLS-gap note. This is now the canonical Fargate flow. Add `ecs:DescribeTasks` polling for IP post-RUNNING in the Vault Waker workflow |
| `vault_app/service/Vault_App__Auto_DNS.py` | Distinguish A-write (registration, idempotent) from TXT-write (runtime, per-boot). Remove the "wait for DNS before cert-init" coordination |
| (new) `sg_edge/service/SG_Edge__TXT_Builder.py` | Helper to compose and validate v=1 TXT records, shared between Vault Waker and Vault Reaper |
| (new) `sg_edge/cloudfront_function/` | CloudFront viewer-request function (Host preservation, slug extraction) |
| (new) `vault_reaper/service/Vault_Reaper__Service.py` | The scheduled reaper (TXT-only cleanup, queries proxies' `/_edge/slug_seen`) |

Total deletion vs addition is roughly balanced — net code surface is similar. The complexity reduction is in the *boot path* (cert-init container, ACME, FQDN coordination, heartbeat timer all gone) which is where most of the operational pain lives today.

# Decisions (formerly open questions)

1. **Heartbeat storage.** Resolved: use the SG/Edge proxies' in-memory `slug_seen` shared_dict — proxies are the long-lived components that see traffic anyway, so they're the natural source of truth for liveness. No vault-side heartbeat, no SSM dependency, works identically locally. See the Reaper section above for the full mechanism.
2. **Backend auth between proxy and target.** Resolved: add HTTP-level auth using the existing `Serverless_Fast_API` key — the proxy injects the `X-API-Key` header on every upstream proxy_pass; the vault's Serverless_Fast_API middleware validates. The key value is passed to the proxy as `SERVERLESS_FAST_API_KEY` env var at boot. This is defense-in-depth alongside the security group restriction, and works identically in local dev where there's no security group.
3. **Fargate task IP discovery timing.** Resolved: this is part of the Vault Waker workflow. Vault Waker calls `RunTask`, then polls `DescribeTasks` until the task transitions to `RUNNING` and exposes its IP, then writes the TXT record. ~5-10s extra, not optimized for MVP.
4. **What about WebSockets?** Not in MVP. Vault doesn't use WS today; the architecture supports it natively (OpenResty + CF both handle Upgrade), but no test scenarios for it in Phase 1/2.
5. **Future agentic mode and the A record.** MVP uses human-customer mode only. Vault registration goes via the existing `sg va` / `sg vp` CLI, which writes the A record on first allocation. Agentic modes (A-less, pooled-A) are Phase 3+ and out of scope.
