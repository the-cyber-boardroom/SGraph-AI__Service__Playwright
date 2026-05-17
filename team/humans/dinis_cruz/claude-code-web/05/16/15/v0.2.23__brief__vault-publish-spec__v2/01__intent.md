---
title: "01 — Intent & Architecture"
file: 01__intent.md
author: Claude (Architect)
date: 2026-05-16 (UTC hour 15)
parent: README.md
---

# 01 — Intent & Architecture

What we are trying to do, in concrete request-path detail, with the architecture that makes it work.

---

## 1. What we are trying to do

**One sentence:** an operator runs `sg vault-publish register sara-cv`, then anyone in the world can `GET https://sara-cv.sg-compute.sgraph.ai/` and see the vault Sara published — even when no EC2 is running for Sara's slug at request time.

The operational properties we want:

- **No traffic = no EC2 running.** Idle slugs cost nothing beyond an EBS snapshot.
- **First cold request returns within ~200 ms** (a warming page that auto-refreshes), not a 60-second hang.
- **Warm path is direct.** Once the EC2 is up and serving, requests bypass any proxy / CloudFront / Lambda and go straight to the EC2's public IP. Lambda is invoked only during cold start.
- **One container substrate** — the same vault-app docker stack that already runs under `sg vault-app create`. No new image, no new compose.
- **One DNS name per slug** — `<slug>.sg-compute.sgraph.ai`. No URL changes between cold and warm.
- **No bespoke signing, manifest interpreter, or new auth surface** — the existing `sg-send-vault` image already serves the published vault content; everything else is plumbing.

---

## 2. The trick that makes this simple — DNS specific-record-beats-wildcard

Route 53 (and every DNS resolver) returns a more-specific record in preference to a less-specific wildcard. We use that to switch between the cold path and the warm path with no proxy infrastructure in the warm path at all.

```
                    DNS state when EC2 is STOPPED                    DNS state when EC2 is RUNNING
                    ────────────────────────────                     ────────────────────────────

  *.sg-compute.sgraph.ai     A ALIAS  →  CloudFront           *.sg-compute.sgraph.ai     A ALIAS  →  CloudFront
                                                                sara-cv.sg-compute.sgraph.ai   A  →  1.2.3.4
                              ▲                                                                          ▲
                              │ wildcard wins because no                                                 │ specific record beats
                              │ specific record exists                                                   │ the wildcard
                              │                                                                          │
                              ▼                                                                          ▼
                           Lambda waker                                                              EC2 directly
```

The vault-publish spec just maintains the per-slug A record in lock-step with EC2 state: present-and-pointing-at-the-IP when running, deleted when stopped. The wildcard is created once at bootstrap and never changes. No CloudFront origin reconfiguration per slug, no Lambda invocations once the EC2 is healthy, no Elastic IPs.

---

## 3. End-to-end request paths

### 3.1 Warm path (the common case after the first cold start)

```
   Browser
     │  GET https://sara-cv.sg-compute.sgraph.ai/
     │
     ▼
   DNS recursive resolver
     │  sara-cv.sg-compute.sgraph.ai  ?  →  A 1.2.3.4   (TTL 60s; specific record beats *)
     │
     ▼
   EC2 (vault-app stack)
     │   sg-send-vault :443   (TLS terminated by cert-init letsencrypt-hostname)
     │   serves the vault content
     │
     ▼
   Browser  ←  200 OK
```

Lambda not invoked. CloudFront not invoked. Cost: one EC2 instance hour while serving (idle-shutdown turns it off when traffic stops).

### 3.2 Cold path (first request after idle-shutdown)

```
   Browser
     │  GET https://sara-cv.sg-compute.sgraph.ai/
     │
     ▼
   DNS recursive resolver
     │  sara-cv.sg-compute.sgraph.ai  ?  →  (specific record absent — slug is stopped)
     │  *.sg-compute.sgraph.ai  ?      →  A ALIAS  dxxxx.cloudfront.net
     │
     ▼
   CloudFront edge
     │  alternate-name match (*.sg-compute.sgraph.ai); ACM wildcard cert
     │  forwards Host header; cache disabled for this distribution
     │
     ▼
   Lambda Function URL  (the Waker)
     │  1. parse Host header → slug = 'sara-cv'
     │  2. SSM Parameter Store: /sg-compute/vault-publish/sara-cv/instance-id  → 'i-0abc...'
     │  3. EC2_Instance('i-0abc...').state()  →  'stopped'
     │  4. EC2_Instance('i-0abc...').start()
     │  5. return warming HTML  (HTTP 200, body = auto-refresh page, no-cache)
     │
     ▼
   Browser shows warming page; meta-refresh fires after 3 s
```

Lambda is invoked once per cold-tick (every 3 s while the user keeps the warming page open). EC2 starts in the background.

### 3.3 The transition (cold → warm)

```
   Browser  ──refresh #N──>  CloudFront  ──>  Lambda Waker
                                                  │  1. EC2_Instance.state() → 'running'
                                                  │  2. health-probe http://1.2.3.4:443/info/health  →  OK
                                                  │  3. Route53__AWS__Client.upsert_record(
                                                  │         'sara-cv.sg-compute.sgraph.ai', 'A',
                                                  │         ['1.2.3.4'], ttl=60)
                                                  │  4. reverse-proxy the request to 1.2.3.4:443
                                                  │     return its response  (no warming page —
                                                  │     a real response, transparently proxied)
                                                  │
                                                  ▼
                                          Browser sees the vault content

   Browser  ──refresh #N+1──>  CloudFront  ──>  Lambda Waker
                                                  │  (DNS is still cached on the browser /
                                                  │   recursive resolver, so the user keeps
                                                  │   coming through CloudFront for up to TTL=60s)
                                                  │
                                                  │  Lambda continues to reverse-proxy.
                                                  │  This is the only window where Lambda is in
                                                  │  the data path while EC2 is healthy.
                                                  ▼

   Browser  ──refresh after ~60s──>  DNS re-resolves  →  A 1.2.3.4
     │                                                       │
     ▼                                                       ▼
   EC2 directly                                       Lambda out of the data path
```

The DNS-swap on first healthy response is the key. Once the per-slug A record is in place, Route 53 returns it to any *new* DNS query, and the wildcard CloudFront alias is no longer matched for this slug. The Lambda proxy job is bounded to one TTL.

### 3.4 The idle path (warm → cold)

```
   sg vault-app stop sara-cv        (called by the idle-shutdown timer that already runs on each instance)
        │
        │   Vault_App__Service.stop_stack(region, 'sara-cv'):
        │     1. EC2.instance_stop(i-0abc...)
        │     2. EC2.wait_for_instance_stopped(i-0abc...)
        │     3. Route53__AWS__Client.delete_record(
        │            'sara-cv.sg-compute.sgraph.ai', 'A')
        │     4. mark SSM Parameter Store: /…/sara-cv/state  = 'stopped'
        ▼
   slug now points at the wildcard → CloudFront → Waker (cold path active)
```

---

## 4. The components and where they live

```
┌──────────────────────────────────────────────────────────────────────────┐
│                      sg_compute_specs/vault_publish/                      │
│                              (THE SPEC)                                   │
│                                                                            │
│  Slug__Validator     reserved + naming policy                              │
│  Slug__Registry      SSM Parameter Store: /sg-compute/vault-publish/...   │
│  Vault_Publish__Service                                                    │
│      register(slug)    → calls sg vault-app create --with-aws-dns         │
│                          + registry write                                  │
│      unpublish(slug)   → calls sg vault-app delete                         │
│                          + registry delete                                 │
│                          + DNS record delete                               │
│      status(slug)      → registry read + sg vault-app info                 │
│      bootstrap()       → one-time: ACM cert + wildcard ALIAS + Waker      │
│                          Lambda + CloudFront distribution                  │
│  waker/                                                                    │
│      Waker__Handler          the Lambda entry point                        │
│      Endpoint__Resolver       interface                                    │
│      Endpoint__Resolver__EC2  (phase 2c)                                   │
│      Endpoint__Resolver__Fargate (phase 3)                                 │
│      Endpoint__Proxy          urllib3 reverse-proxy                        │
│      Warming__Page            HTML generator                               │
│  cli/Cli__Vault_Publish       Typer surface — register / unpublish /      │
│                                status / list / bootstrap                   │
└──────────────────────────────────────────────────────────────────────────┘
                                  │
                                  │   composes
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          OUTSIDE THE SPEC                                 │
│                                                                            │
│  sg_compute_specs/vault_app/      EXISTS — needs `stop` and `start`       │
│                                    verbs added; auto-DNS re-runs on start │
│                                                                            │
│  sgraph_ai_service_playwright__cli/aws/dns/     EXISTS                    │
│      Route53__AWS__Client          read/write Route 53                     │
│      Route53__Zone__Resolver       FQDN → owning zone                      │
│      Route53__Instance__Linker     EC2 ref → public IP                     │
│      Route53__Smart_Verify         TTL-aware verification                  │
│                                                                            │
│  sgraph_ai_service_playwright__cli/aws/acm/     EXISTS (read-only)        │
│                                                                            │
│  sgraph_ai_service_playwright__cli/aws/cf/      PROPOSED — phase 2a       │
│      CloudFront__AWS__Client       sole boto3 boundary                     │
│      CloudFront__Distribution__Builder    create / update config builder  │
│      Cli__Cf                       sub-typers: distributions / origins    │
│                                                                            │
│  sgraph_ai_service_playwright__cli/aws/lambda_/ PROPOSED — phase 2b       │
│      Lambda__Deployer              wraps osbot_aws.Deploy_Lambda           │
│      Cli__Lambda                   sub-typers: deployments / urls         │
└──────────────────────────────────────────────────────────────────────────┘
                                  │
                                  │   uses
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                              osbot-aws                                    │
│                                                                            │
│  EC2 / EC2_Instance        instance_start, instance_stop, wait_for_*,    │
│                             state(), ip_address(), info()                  │
│  Lambda / Deploy_Lambda    full surface incl. function_url_*,             │
│                             add_folder, add_osbot_aws, set_handler,       │
│                             set_env_variables, deploy, update             │
│  Parameter (SSM)           put / get / put_secret / get_secret            │
│  IAM_Role_With_Policy      Lambda execution role                          │
│  Cloud_Front               list + invalidate only — phase 2a wraps the    │
│                             missing distribution-create/update/delete     │
│  ECS_Fargate_Task          phase 3 — Fargate execution target             │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Non-goals (explicitly out of scope of this brief)

- **No bespoke manifest interpreter, signature verifier, or "vault-publish manifest" schema.** The published content is the vault content; the `sg-send-vault` image serves it directly. There is no provisioning language we need to interpret. The signing scheme question (`v0.2.11 #4`) and the SG/Send fetch contract question (`v0.2.11 #3`) both disappear in this design.
- **No CloudFront in the warm path.** Once a per-slug A record exists, requests bypass CloudFront entirely.
- **No Elastic IPs.** Each EC2 gets a fresh public IP on start; the DNS-swap-on-start handles the IP change.
- **No multi-vault sharing inside one container.** One slug → one EC2 → one vault. Vault-app already does this; we use it as-is.
- **No private VPC in phase 1 / 2.** Public IPs throughout; private VPC + ALB is phase 4 territory.
- **No Fargate / ECS in phase 1 / 2.** The `Endpoint__Resolver` abstraction is there to make phase 3 a drop-in swap, but the first cut is EC2-only.

---

## 6. The four "is this really better?" sanity checks

| Concern | v0.2.11 design (what I wrote before) | This design |
|---------|--------------------------------------|-------------|
| **New AWS primitives to build** | CloudFront + Lambda + bespoke registry + waker | CloudFront + Lambda (+ small stop/start addition to vault-app) |
| **New schemas / type families** | ~17 schemas, 8 enums, 9 primitives across manifest / interpreter / verifier | ~5 schemas + the slug primitives we already wrote |
| **SG/Send-side open questions** | #1 simple-token derivation, #3 fetch contract, #4 signing scheme | #1 only (and weaker — see [04](04__vault-publish-spec.md§3)) |
| **Container substrate** | Bespoke `Vault_App__Manifest` allowlist interpreter | Reuses the vault-app stack image as-is |

Every line in the right column is "we already have this" or "tiny wrapper over what's there".
