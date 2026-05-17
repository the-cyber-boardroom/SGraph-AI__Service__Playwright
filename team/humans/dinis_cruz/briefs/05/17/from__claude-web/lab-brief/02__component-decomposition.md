---
title: "02 — Component decomposition"
file: 02__component-decomposition.md
author: Architect (Claude)
date: 2026-05-16 (UTC hour 15)
parent: README.md
---

# 02 — Component decomposition

The v2 workflow broken into the smallest units that compose into a behavioural claim. Each unit is a discrete thing the harness can observe; each maps to one or more named experiments in [§3](03__experiment-catalogue.md).

The decomposition runs **across the request lifecycle**, not by AWS service. That's deliberate — the interesting behaviour is in the seams.

---

## The cold-path request, decomposed

```
                       ┌─────────────────────────────────────────────┐
                       │  user enters https://sara-cv.sg-compute…/   │
                       └────────────────────┬────────────────────────┘
                                            │
   D1                                       ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │  D1  Browser's stub resolver decides what to ask its recursive       │   ← DNS — client side
   │      resolver. (Cached? from where? for how long?)                   │
   └────────────────────┬─────────────────────────────────────────────────┘
                        ▼
   D2 / D3 / D4
   ┌──────────────────────────────────────────────────────────────────────┐
   │  D2  Recursive resolver receives the query. Cache miss?              │   ← DNS — recursive
   │  D3  Resolver walks the delegation chain to Route 53's NS set        │      resolver behaviour
   │  D4  One of the 4 R53 NS answers — specific record beats wildcard    │
   │      (the load-bearing claim of the whole architecture)              │
   └────────────────────┬─────────────────────────────────────────────────┘
                        ▼
   When specific record absent → wildcard → CF distribution
   ┌──────────────────────────────────────────────────────────────────────┐
   │  C1  Browser opens TLS to a CloudFront edge IP                       │   ← CloudFront —
   │  C2  CF terminates TLS using the ACM wildcard cert                   │      viewer side
   │  C3  CF picks the matching cache behaviour (CachingDisabled)         │
   │  C4  CF forwards the request to its origin (the Lambda Function URL)│
   │      — with what timeouts? with what retry semantics?                │
   └────────────────────┬─────────────────────────────────────────────────┘
                        ▼
   L1 / L2 / L3
   ┌──────────────────────────────────────────────────────────────────────┐
   │  L1  CF opens TLS to the Function URL host                           │   ← Lambda — invocation
   │  L2  Function URL invokes the Lambda (cold start? warm container?)   │
   │  L3  Lambda runs the FastAPI app, parses Host, looks up registry,    │
   │      reaches EC2 / returns warming HTML                              │
   └────────────────────┬─────────────────────────────────────────────────┘
                        ▼
   E1 / E2 / E3                                       (only on warm-EC2 paths)
   ┌──────────────────────────────────────────────────────────────────────┐
   │  E1  Lambda opens TLS to the EC2 public IP                           │   ← EC2 — origin side
   │  E2  vault-app's sg-send-vault answers                               │
   │  E3  Lambda streams the response back upstream                       │
   └────────────────────┬─────────────────────────────────────────────────┘
                        ▼
   T1 / T2                                            (only on cold→warm flip)
   ┌──────────────────────────────────────────────────────────────────────┐
   │  T1  Lambda upserts the specific A record                            │   ← Transition —
   │  T2  Recursive resolvers re-query after their wildcard TTL expires   │      cold to warm
   │      and now see the specific record → direct path to EC2            │
   └──────────────────────────────────────────────────────────────────────┘
```

Each labelled box is a **component** the harness can measure in isolation or in combination.

---

## The component table

22 components, grouped by request-lifecycle area. Every component has a **probe verb** (what we send) and a **measurement** (what we observe).

### DNS — client-side (informational; we can only sample our own host)

| ID | Component | Probe | Measurement |
|----|-----------|-------|-------------|
| D1 | Local resolver cache | `dig <name>` then `dig <name>` again | Second response ms |
| D1.2 | curl's DNS cache | `curl -v` twice in one process | TTL behaviour in libcurl |

### DNS — Route 53 zone state (read-only, no mutations needed)

| ID | Component | Probe | Measurement |
|----|-----------|-------|-------------|
| D2 | Zone authoritative NS set | `r53.get_hosted_zone(Id=...)` | List of 4 NS, their delegation set |
| D2.1 | Zone existence + record count | `list_resource_record_sets` (paginated) | Total record count, distribution by type |
| D2.2 | Specific record exists? | `r53.list_resource_record_sets(StartRecordName=...)` | Yes/no, TTL, value list |
| D2.3 | Wildcard record presence | filter records by name `*.<zone>` | Wildcard records by type |

### DNS — Route 53 mutation (gated; require ledger)

| ID | Component | Probe | Measurement |
|----|-----------|-------|-------------|
| D3 | upsert_record → ChangeInfo | `r53.change_resource_record_sets(...)` | ChangeId, initial status |
| D3.1 | ChangeInfo → INSYNC | `r53.get_change(Id=ChangeId)` polled | Time to first PENDING→INSYNC |
| D3.2 | Authoritative-NS visibility post-INSYNC | `dig @<each NS> +norecurse` | Per-NS time, agreement count |
| D3.3 | Public-resolver visibility post-INSYNC | `dig @<8 public>` | Per-resolver time, agreement count |
| D3.4 | Specific record beats wildcard test | upsert specific → check public resolvers | Which value each resolver returns |
| D3.5 | TTL countdown after `delete_record` | delete + repeated `dig` | Time to first NXDOMAIN per resolver |

### CloudFront — viewer-side behaviour

| ID | Component | Probe | Measurement |
|----|-----------|-------|-------------|
| C1 | CF edge IP locality | `dig <distribution>.cloudfront.net` from N positions | Edge IPs returned, geolocation |
| C2 | CF TLS handshake | `curl -v --resolve` against the alternate-domain-name | TLS version, cipher, cert SANs |
| C3 | CF cache-policy enforcement | hit with `Authorization: Bearer X` header twice | Was the second served from cache? (must be no) |
| C4 | CF origin connection-timeout | configure 2 s; point origin at a sinkhole IP | What happens to the request? error page? retry? |
| C5 | CF response on origin 5xx | origin returns 503 (Lambda returns it intentionally) | What does CF do? Cached error? Retry? |
| C6 | CF response on origin connection-refused | origin port closed (Lambda Function URL deleted under it) | Same |
| C7 | CF behaviour with two competing aliases | request hits `*.sg-compute.sgraph.ai` and `sara-cv.sg-compute.sgraph.ai` (specific A) | Which path does CF use? |

### Lambda — invocation behaviour

| ID | Component | Probe | Measurement |
|----|-----------|-------|-------------|
| L1 | Function URL TLS overhead | `curl -w` against function-url host directly | Connect / TLS / TTFB ms |
| L2 | Cold start vs warm | invoke after 5 min idle, then immediately again | Cold-ms, warm-ms, ratio |
| L3 | Cold start with osbot deps | same Lambda redeployed with/without `add_osbot_aws` etc. | Bytes diff, cold-start diff |
| L4 | Buffered vs streaming response | same Lambda configured both ways, large body | TTFB, total ms, max response size |
| L5 | Concurrency ceiling | 50 concurrent invokes via threading | Errors, throttles, init-duration spread |
| L6 | Lambda → Route 53 latency | from inside Lambda, time an `upsert_record` call | ms (relevant to the v2 DNS-swap design) |
| L7 | Lambda → EC2 over public IP | from inside Lambda, time a curl-equivalent to a stack | ms (relevant to the warm-path-via-Lambda window) |

### Transition behaviours (composite)

| ID | Component | Probe | Measurement |
|----|-----------|-------|-------------|
| T1 | "DNS swap converges across the public-resolver set" | upsert specific A record + watch all 8 resolvers | Per-resolver flip time, max time |
| T2 | "Lambda exits the data path within one TTL" | combined: D3.4 + L7 measurements pre/post swap | Window where Lambda is invoked while EC2 is healthy |
| T3 | "Stop → A-record-delete race window" | stop the EC2 + delete A in two orderings | Number of dead-IP responses in each ordering |

### ACM — verification only

| ID | Component | Probe | Measurement |
|----|-----------|-------|-------------|
| A1 | Wildcard cert SANs | `acm.describe_certificate(...)` | SAN list, validation status, days-to-expiry |
| A2 | Cert chains to public CA | `openssl s_client` against CF edge | Chain depth, root CA name |

---

## Why this many

Each component above is a *separate measurement*. The temptation is to collapse them — "one big experiment that creates an EC2, registers a slug, and times everything". That experiment is *useful* (see [§3 E27](03__experiment-catalogue.md#e27--full-cold-path-end-to-end)) but it's the *worst* shape for early measurement work because:

- when it fails, you don't know which step regressed,
- when it changes, you can't tell which component shifted,
- you cannot run it cheaply enough to gather a distribution.

The decomposition above lets us run, e.g., D3.3 fifty times in an hour to get a propagation distribution, without ever touching CloudFront or Lambda. That's where the harness's value actually comes from.

---

## Component-to-question matrix

| Component | Q1 (wildcard) | Q2 (INSYNC) | Q3 (CF errors) | Q4 (cold start) | Q5 (Lambda exit) |
|-----------|:-:|:-:|:-:|:-:|:-:|
| D1, D1.2 | | | | | ✓ |
| D2.* | ✓ | | | | |
| D3, D3.1 | | ✓ | | | |
| D3.2 / D3.3 | ✓ | ✓ | | | |
| D3.4 | ✓ | | | | ✓ |
| D3.5 | ✓ | | | | ✓ |
| C1, C2 | | | ✓ | | |
| C3 | | | ✓ | | |
| C4, C5, C6 | | | ✓ | | |
| C7 | ✓ | | ✓ | | |
| L1 | | | | ✓ | |
| L2, L3 | | | | ✓ | |
| L4 | | | ✓ | | |
| L5 | | | | ✓ | |
| L6, L7 | | | | | ✓ |
| T1 | ✓ | | | | ✓ |
| T2 | ✓ | | | | ✓ |
| T3 | ✓ | | | | |
| A1, A2 | | | ✓ | | |

Every question gets covered by multiple components. No component sits alone.
