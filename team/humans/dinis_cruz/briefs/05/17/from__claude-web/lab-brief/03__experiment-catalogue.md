---
title: "03 — Experiment catalogue"
file: 03__experiment-catalogue.md
author: Architect (Claude)
date: 2026-05-16 (UTC hour 15)
parent: README.md
---

# 03 — Experiment catalogue

Every named experiment in the harness. Each gets a CLI verb (`sg aws lab <verb>`) and produces a `Schema__Lab__Run__Result`.

Experiments split into three tiers:

- **Tier-0 (read-only)** — no mutations. Always safe.
- **Tier-1 (mutating, low-cost)** — small AWS work; ~$0.001/run. Gated.
- **Tier-2 (mutating, higher cost)** — provisions CF / Lambda / EC2 briefly; ~$0.05–0.50/run. Gated + confirmation.

---

## Format

Each entry: ID, name, CLI verb, tier, what it proves, the steps, the result schema fields. ASCII timeline where it helps.

---

## DNS read-only experiments (Tier-0)

### E01 — zone-inventory
**CLI:** `sg aws lab dns zone-inventory [<zone>]`
**Tier:** 0
**Proves:** what we have to work with — zone NS set, record counts, presence of any existing `*.<zone>` wildcard.
**Steps:**
1. `Route53__AWS__Client.get_hosted_zone(zone_id)` — extract NS list (4 names).
2. `Route53__AWS__Client.list_records(zone_id)` paginated — count by type.
3. Filter for `*.<zone>` records — show what wildcard records exist today (if any).
**Result fields:** `zone_id, zone_name, ns_servers[4], record_count_by_type, wildcard_records[]`.

### E02 — resolver-latency
**CLI:** `sg aws lab dns resolver-latency <name> [--type A]`
**Tier:** 0
**Proves:** how long the 8 public resolvers each take to answer a known stable record. Establishes a baseline before doing anything.
**Steps:** Fan out `dig @<resolver> +short <name> A` to each of 8 resolvers, in parallel. Record per-resolver duration_ms.
**Result fields:** `name, rtype, observations[{resolver, value, duration_ms, error}]`.
**Optional flag:** `--repeat N` — do it N times, return percentiles.

### E03 — authoritative-ns-latency
**CLI:** `sg aws lab dns authoritative-ns-latency <zone>`
**Tier:** 0
**Proves:** how long each of the 4 Route 53 NS for a zone takes to answer the same `SOA` query.
**Steps:** Get NS set; fan out `dig +norecurse @<ns> SOA <zone>` to each. Repeat N times if `--repeat`.
**Result fields:** `zone_name, observations[{ns, soa_serial, duration_ms}]`.

### E04 — wildcard-pre-check
**CLI:** `sg aws lab dns wildcard-pre-check <name>`
**Tier:** 0
**Proves:** what each resolver returns for a not-yet-created specific name **right now** — establishes the "before" baseline for E11.
**Steps:** D3.4-style probe against `<name>` (which doesn't exist); record what each resolver returns (NXDOMAIN or wildcard match).
**Result fields:** `name, observations[{resolver, value, rcode, duration_ms}]`.

---

## DNS mutating experiments (Tier-1)

### E10 — insync-distribution
**CLI:** `sg aws lab dns insync-distribution --repeat 20`
**Tier:** 1
**Proves:** Q2 — how long `ChangeInfo` actually takes to go PENDING → INSYNC. Distribution, not just a single number.
**Steps:**
1. For each of N runs:
   - `upsert_record(zone, lab-insync-<run-id>-<i>.<zone>, A, 192.0.2.1, ttl=60)`
   - poll `get_change(change_id)` every 1 s until INSYNC; record time
   - `delete_record(...)`
   - register both create and delete for ledger
2. Aggregate: min, p50, p95, p99, max.
**Cleanup:** synchronous after each run.
**Result fields:** `n_runs, durations_ms[], stats{min, p50, p95, p99, max}`.

### E11 — propagation-timeline
**CLI:** `sg aws lab dns propagation-timeline [--ttl 60]`
**Tier:** 1
**Proves:** Q2 + Q1 partial — after INSYNC, when does each of the 8 public resolvers actually start returning the new value?
**Steps:**
1. upsert `lab-prop-<run-id>.<zone>` A 192.0.2.42 TTL=`<ttl>`
2. wait for INSYNC (record time)
3. immediately start fanning out `dig @<resolver>` queries every 2 s for up to 5 min
4. record per-resolver first-seen-correct time
5. delete the record + register for cleanup
**Cleanup:** synchronous; sweeper backstop.
**Result fields:** `record_name, insync_at_ms, observations[{resolver, first_correct_ms, dig_count}]`.
**Output (terminal timeline):**
```
00:00  upsert    →  ChangeId  /change/C0123…
00:04  INSYNC    ✓
00:06  CLOUDFLARE_1   1.1.1.1     ✓ (returned 192.0.2.42)
00:06  GOOGLE_1       8.8.8.8     ─ (returned NXDOMAIN)
00:08  GOOGLE_1       8.8.8.8     ✓
00:10  QUAD9          9.9.9.9     ✓
…
```

### E12 — wildcard-vs-specific
**CLI:** `sg aws lab dns wildcard-vs-specific`
**Tier:** 1
**Proves:** Q1 — the core architectural claim. Does specific-record-beats-wildcard actually work?
**Steps:**
1. (precondition) the harness either reads `--wildcard-already-present` or creates a wildcard pointing at TEST-NET-1 (192.0.2.1) for the run.
2. baseline: dig `lab-wildcard-test-<run-id>.<zone>` from all 8 resolvers → expect 192.0.2.1.
3. upsert specific `lab-wildcard-test-<run-id>.<zone>` A 198.51.100.1 (TEST-NET-2).
4. wait INSYNC; record convergence per resolver.
5. delete specific record.
6. measure how long until resolvers go back to 192.0.2.1 (validates Q5 — return-to-wildcard).
**Cleanup:** delete specific record + (if created) delete wildcard.
**Result fields:** `wildcard_value, specific_value, convergence_to_specific[], convergence_back_to_wildcard[]`.

### E13 — ttl-respect
**CLI:** `sg aws lab dns ttl-respect --ttl 60`
**Tier:** 1
**Proves:** do public resolvers actually respect the TTL? (Some are known to clamp very-low TTLs upward.)
**Steps:**
1. upsert `lab-ttl-<run-id>.<zone>` A 192.0.2.1 TTL=60
2. wait INSYNC + initial resolver pickup (E11-style)
3. update to A 192.0.2.2 (same TTL)
4. measure time from update→INSYNC→each-resolver-flips. If a resolver still returns the old value past 60 s, it clamped.
**Cleanup:** delete record.
**Result fields:** `nominal_ttl, observed_ttl_per_resolver_seconds[]`.

### E14 — delete-propagation
**CLI:** `sg aws lab dns delete-propagation`
**Tier:** 1
**Proves:** how long after `delete_record` does each resolver return NXDOMAIN?
**Steps:** create → upsert with TTL=60 → wait for full propagation → delete → measure NXDOMAIN convergence.
**Cleanup:** synchronous; the experiment *is* a delete.

---

## CloudFront read-only experiments (Tier-0)

### E20 — cf-distribution-inspect
**CLI:** `sg aws lab cf inspect <distribution-id>`
**Tier:** 0
**Proves:** what a distribution actually looks like in AWS terms. Useful for any pre-existing distribution; for the v2 wildcard distribution once it lands.
**Steps:** `get_distribution + get_distribution_config`; render the cache behaviour, origin config, alternate-domain-names, cert ARN, status.
**Result fields:** `distribution_id, status, enabled, aliases[], origin_count, cache_policy_id, cert_arn, last_modified`.

### E21 — cf-edge-locality
**CLI:** `sg aws lab cf edge-locality <distribution-domain> [--from-positions ec2,local,fargate]`
**Tier:** 0
**Proves:** which CF edge each network position resolves to. (Useful for understanding "wait, but my dev box and my Lambda see different edges" cases.)
**Steps:** `dig <distribution-domain>` from N positions; record the IPs returned; reverse-lookup to PoP code if possible.
**Result fields:** `domain, observations[{position, edge_ips[], pop_guess}]`.

### E22 — cf-tls-handshake
**CLI:** `sg aws lab cf tls-handshake <alt-domain-name>`
**Tier:** 0
**Proves:** the CF cert is properly attached and chains to public CA; the cipher/TLS-version posture is what we want.
**Steps:** `openssl s_client -connect <cf-edge>:443 -servername <alt-domain>` — parse cert chain, cipher, TLS version, SANs.
**Result fields:** `tls_version, cipher_suite, cert_sans[], chain_depth, root_ca_name`.

---

## CloudFront mutating experiments (Tier-2)

These provision a CF distribution per run. Each create takes ~15 min, each delete ~15-25 min (CF is slow). Run sparingly.

### E25 — cf-cache-policy-enforcement
**CLI:** `sg aws lab cf cache-policy-enforcement`
**Tier:** 2
**Proves:** Q3 — `CachingDisabled` actually disables caching, even when the response has cache-friendly headers.
**Steps:**
1. Provision lab Lambda with a Function URL that always returns `Cache-Control: max-age=3600` and a body containing `request-id: <uuid>`.
2. Provision a CF distribution: lambda-FN-URL as origin, CachingDisabled cache policy. Wait Deployed (~15 min).
3. Hit the alternate domain twice in quick succession. Record both bodies.
4. Assert each response has a distinct request-id (proving no cache hit).
**Cleanup:** disable + delete the distribution; delete Lambda; delete cert if minted for this run.
**Result fields:** `request_ids[], same_response, cf_cache_status_headers[]`.

### E26 — cf-origin-error-handling
**CLI:** `sg aws lab cf origin-error-handling --case <case>`
**Tier:** 2
**Proves:** Q3 — exactly what CloudFront does when the origin misbehaves.
**Steps (parametric):**
- `--case timeout` — origin Lambda has a 10 s sleep; CF origin connection timeout = 2 s
- `--case 503` — origin Lambda returns HTTP 503 immediately
- `--case 502` — origin Lambda returns malformed response
- `--case refused` — point CF origin at a non-existent function URL host
- `--case slow-headers` — origin opens TCP but never sends headers
Each case: hit CF, record response code, latency, response body, any `X-Cache` / `X-Amz-Cf-*` headers.
**Cleanup:** distribution + Lambda.
**Result fields:** `case, response_code, response_body, response_time_ms, x_cache, x_amz_cf_id`.

### E27 — full-cold-path-end-to-end
**CLI:** `sg aws lab e2e cold-path`
**Tier:** 2
**Proves:** the v2 brief's entire cold-path works end-to-end, and where the milliseconds go.
**Steps:**
1. Provision: ACM cert (or reuse), CF distribution wired to a lab waker Lambda, wildcard ALIAS, a lab vault-app EC2 (stopped).
2. Issue a request to `<lab-slug>.sg-compute.sgraph.ai`; record every transition timestamp.
3. Watch the warming page; record refresh count until EC2 healthy.
4. After healthy, watch the DNS swap (Lambda upserts specific record); record convergence.
5. Make a second request; verify it goes direct to EC2 (no Lambda invocation in the new CloudTrail / X-Ray trace).
**Cleanup:** terminate EC2, delete A record, delete CF, delete Lambda.
**Result fields:** the full timeline `[(t_ms, event, detail)]`.

---

## Lambda experiments (Tier-1 / Tier-2)

### E30 — lambda-cold-start-distribution
**CLI:** `sg aws lab lambda cold-start --repeat 20 [--include-osbot]`
**Tier:** 1
**Proves:** Q4 — actual cold-start time distribution.
**Steps:**
1. Deploy a minimal `lab_waker_stub` Lambda — FastAPI + Lambda Web Adapter, returns warming HTML, no business logic.
2. Optionally include `add_osbot_utils=True` + `add_osbot_aws=True` based on flag.
3. For each of N runs: invoke; record `Init-Duration` + `Duration` from response logs; wait long enough for the container to be evicted (`--cold-spacing 600`, default 10 min) or update the Lambda to force a new container.
4. Aggregate.
**Cleanup:** delete the Lambda + Function URL.
**Result fields:** `cold_starts_ms[], warm_starts_ms[], init_duration_p50, init_duration_p99`.

### E31 — lambda-deps-impact
**CLI:** `sg aws lab lambda deps-impact`
**Tier:** 1
**Proves:** Q4 sub-question — how much do `osbot-utils` + `osbot-aws` cost at cold start?
**Steps:** Run E30 four times: (a) bare, (b) +osbot-utils, (c) +osbot-aws, (d) both. Report deltas.

### E32 — lambda-stream-vs-buffer
**CLI:** `sg aws lab lambda stream-vs-buffer --body-size 1MB,5MB,9MB`
**Tier:** 1
**Proves:** the streaming-mode discussion from the v2 review (item #1). Concrete numbers on truncation + TTFB.
**Steps:** Deploy two Lambdas, identical except `invoke_mode='BUFFERED' | 'RESPONSE_STREAM'`. Invoke each with body sizes that bracket the 6 MB ceiling. Record TTFB, total ms, actual response size.

### E33 — lambda-internal-r53-call
**CLI:** `sg aws lab lambda r53-call-latency`
**Tier:** 1
**Proves:** Q5 — when the Waker upserts the specific A record from inside the Lambda, how long does it take?
**Steps:** Deploy a Lambda that makes one `Route53__AWS__Client.upsert_record` call against a throwaway record and returns the duration. Invoke 20 times. Aggregate.

### E34 — lambda-internal-ec2-curl
**CLI:** `sg aws lab lambda ec2-curl <ec2-public-ip>`
**Tier:** 1
**Proves:** Q5 — when the Lambda proxies to an EC2, what's the network cost from inside the Lambda VPC-less environment?
**Steps:** Deploy Lambda that curls `https://<public_ip>:443/info/health` and returns connect / tls / ttfb / total ms. Invoke 20 times against a known-healthy lab EC2 (pre-provisioned or pointed at a public address).

### E35 — lambda-function-url-vs-direct
**CLI:** `sg aws lab lambda url-vs-direct-invoke`
**Tier:** 1
**Proves:** how much overhead does Function URL add vs `lambda.invoke()` direct?
**Steps:** Invoke same Lambda 20 times via Function URL (HTTPS), 20 times via direct invoke API. Compare TTFB.

---

## Composite / transition experiments (Tier-1 + Tier-2)

### E40 — dns-swap-window
**CLI:** `sg aws lab transition dns-swap-window [--ttl 60]`
**Tier:** 1
**Proves:** T2 — for how long after upserting the specific record do public resolvers still return the wildcard?
**Steps:**
1. baseline: wildcard already exists (or create one for the run); E11-style pre-check that all resolvers return the wildcard value.
2. upsert specific record with TTL.
3. continuously sample all 8 resolvers every 2 s for up to TTL+30 s.
4. for each resolver, record the moment it flipped from wildcard-value to specific-value.
**Cleanup:** delete specific; (if created) delete wildcard.
**Result fields:** `nominal_ttl, per_resolver_flip_seconds[8], max_flip_seconds`.

### E41 — stop-race-window
**CLI:** `sg aws lab transition stop-race-window`
**Tier:** 1
**Proves:** T3 — the "stop EC2 then delete A record" race (review item #3).
**Steps:**
1. given a lab vault-app stack with a specific A record
2. start a tight loop curling the specific hostname every 0.5 s
3. trigger stop-then-delete vs delete-then-stop in two separate runs
4. count: TCP-RSTs, NXDOMAIN responses, successful warming-pages
**Result fields:** `ordering, sample_count, tcp_rst_count, warming_page_count, success_count`.

### E42 — concurrent-cold-thunder
**CLI:** `sg aws lab transition concurrent-cold-thunder --concurrency 20`
**Tier:** 2
**Proves:** if N concurrent users hit a slug at once, what does the Waker do? Race? duplicate `StartInstances`? duplicate `upsert_record`?
**Steps:**
1. given a lab stack, stop it
2. fire `concurrency` concurrent requests
3. count: distinct Lambda containers invoked (`Init-Duration` presence), distinct `StartInstances` calls in CloudTrail, distinct `ChangeBatch` calls
**Result fields:** `concurrency, lambda_init_count, ec2_start_call_count, r53_change_count`.

---

## Summary

| Tier | Count | Aggregate runtime | Aggregate cost / run |
|------|------:|-------------------|---------------------:|
| 0 | 10 | seconds | $0 |
| 1 | 8  | 1–5 min each | <$0.01 |
| 2 | 5  | 30–45 min each (CF dominates) | $0.05–0.50 |

The Tier-0 + Tier-1 experiments are where the daily measurement work happens. Tier-2 experiments are special — run on demand, once or twice each, to characterise CF / E2E behaviour.

The next file ([§4](04__safety-and-cleanup.md)) explains how every one of these is **guaranteed not to leak** even when things go wrong.
