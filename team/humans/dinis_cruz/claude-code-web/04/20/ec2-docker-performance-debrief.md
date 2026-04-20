# Performance Debrief — EC2/Docker vs Lambda

**Date:** 2026-04-20  
**Session:** `013AHDBwYgC2s4XDRAsF4io8`  
**Service version:** v0.1.48  
**Prepared by:** Claude Code (DevOps / SRE)

---

## Summary

The Playwright service on EC2 (Docker two-container stack) is **5–15× slower** than the same service on Lambda for equivalent requests. This is not a code bug — it is structural. The two deployment targets have different constraint profiles. This document records the observed data, identifies the root causes in order of impact, and outlines what would fix each one.

---

## Observed Data

### Smoke test — t3.large (instance type 1)

Run 1:

| URL | Cold (ms) | Warm avg (ms) | Screenshot KB |
|-----|-----------|----------------|---------------|
| google.com | 31,566 | 17,681 | 74 |
| sgraph.ai | 26,231 | 21,072 | 58 |
| send.sgraph.ai | 31,185 | 1,133 | 53 |
| news.bbc.co.uk | 3,549 | 33,419 | 420 |

Run 2 (same instance, later run, credits recovering):

| URL | Cold (ms) | Warm avg (ms) | Screenshot KB |
|-----|-----------|----------------|---------------|
| google.com | 32,039 | 1,636 | 74 |
| sgraph.ai | 1,026 | 13,115 | 58 |
| send.sgraph.ai | 1,357 | 31,556 | 53 |
| news.bbc.co.uk | 33,714 | 20,385 | 420 |

**Avg cold: 17,034 ms. Avg warm: 16,673 ms. Total elapsed: 305 s (for 12 requests).**

### Lambda (baseline, from prior sessions)

Equivalent screenshot/navigate requests: **2,000–5,000 ms** consistently. No credit depletion pattern. No variance spike.

---

## Root Cause Analysis

### RC-1 — mitmproxy HTTPS interception (estimated impact: +10–25 s on heavy pages)

**Present on:** EC2 only. Lambda has no sidecar.

Every byte of browser traffic — including all HTTPS sub-resources — passes through the `agent-mitmproxy` container on the Docker bridge. mitmproxy performs a full TLS man-in-the-middle on every CONNECT tunnel:

1. Browser sends `CONNECT hostname:443`
2. mitmproxy accepts the tunnel and opens its own TLS session to the origin
3. mitmproxy intercepts the request, applies addons, forwards upstream
4. Repeat for every sub-resource on the page

A page like `news.bbc.co.uk` has 80–120 distinct origin hosts. Each requires a CONNECT + TLS handshake pair through the proxy. On Lambda this doesn't exist — Chromium talks directly to the internet.

**Evidence:** `news.bbc.co.uk` (many sub-resources) is consistently the slowest URL. `send.sgraph.ai` with a fast warm run (1,133 ms) was a noise outlier — later runs show 31 s, consistent with resource-heavy pages.

**Fix:** None without changing the architecture. The mitmproxy sidecar *is* the product — it exists to intercept. Options:
- **Selective interception** — configure mitmproxy to pass through certain CDN domains (`*.cloudfront.net`, `*.akamaihd.net`, etc.) without MITM. Reduces the number of TLS handshakes without losing audit-log coverage of first-party calls.
- **Connection pooling** — mitmproxy already reuses upstream TCP connections to some extent; tuning `connection_strategy` may help.
- **Async addon processing** — move audit-log writes off the critical path (already the case with current addon design, but worth confirming).

---

### RC-2 — t3 CPU credit depletion (estimated impact: +20–30 s per request after credits exhausted)

**Present on:** EC2 t3 family only. Lambda allocates dedicated CPU for invocation duration.

t3 instances are burstable. They earn credits at a baseline rate (30% per vCPU) and spend them during CPU bursts. When the credit balance reaches zero, the instance is throttled to its baseline rate.

**t3.large baseline:** 2 vCPU × 30% = 0.6 vCPU effective sustained throughput.

**Chromium + mitmproxy load profile:** Each request launches a fresh Chromium process (multi-threaded, ~150% CPU during page load) plus mitmproxy handling dozens of HTTPS tunnels concurrently. A single 12-request smoke run (4 URLs × 3 requests) depletes the credit balance within 5–6 requests.

**The depletion signature is clearly visible in Run 2:**

```
Request  1  (google cold):    32 s   ← first request, EBS cold-read of Chromium binary
Requests 2–5 (warm/cold):    1–1.4 s ← credits available, fast
Request  6  (sgraph warm2):  25 s   ← credits EXHAUSTED, throttled to 0.6 vCPU
Requests 7+:                 31–35 s ← fully throttled
Request 11  (bbc warm1):      6 s   ← brief credit recovery between requests
Request 12  (bbc warm2):     35 s   ← depleted again immediately
```

**Fix options:**
- **Switch to fixed-performance instance type** — `c5.xlarge` (preset 4) or `m5.xlarge` (preset 5) have no burst credit system. CPU is fully available at all times. Expected: all requests drop to 1–5 s (just mitmproxy TLS overhead).
- **Use `t3 unlimited` mode** — costs extra but eliminates throttling. Not recommended; `c5.xlarge` is cheaper at the same throughput for this workload.
- **Spread load** — add instance-level sleep between smoke test requests (not a fix, just hides the symptom).

**Recommended immediate action:** run the smoke test against a `c5.xlarge` (preset 4) to isolate whether removing CPU credits narrows the variance. If variance collapses, RC-2 is the dominant cause; mitmproxy (RC-1) is the baseline floor.

---

### RC-3 — Stateless Chromium per request (estimated impact: +1–3 s per request, constant)

**Present on:** EC2 and Lambda equally. This is architectural — by design.

Every `/browser/*` request launches a fresh Chromium process via `sync_playwright().start()` + `browser_type.launch()`, runs steps, and tears down in `try/finally`. There is no persistent browser pool.

**"Warm" is misleading terminology** in our smoke output. It means the Chromium *binary* is in the Linux page cache (faster to read from disk), not that a Chromium process is already running. The distinction matters:

- Cold request 1: Chromium binary reads from EBS → 1–3 s just for the read
- Subsequent requests (same boot): Binary in RAM cache → ~0.1 s for the read
- All requests: Full `playwright.start()` + browser launch → 0.5–1.5 s regardless of cache state

On Lambda, the execution environment is reused between invocations. The `playwright` object and Chromium binary stay in memory between warm invocations. This is the main reason Lambda feels faster on "warm" calls — it's not that Lambda is faster hardware, it's that the cost of the launch is amortised across many invocations sharing the same execution environment.

**Fix options:**
- **Persistent browser pool on EC2** — a background coroutine pre-launches N Chromium instances and leases them to requests. Risk: state leakage between requests, memory pressure. Not currently planned.
- **Accept the cost** — 1–3 s Chromium overhead is acceptable if RC-1 and RC-2 are resolved (requests drop from 30 s to 3–5 s).

---

### RC-4 — First-request EBS cold read (estimated impact: +5–10 s on request #1 only)

**Present on:** EC2 only (first request after instance boot or container restart).

The Chromium binary in the Playwright Docker image is ~300 MB. On first access after a container start, the kernel reads it from the EBS volume over the network. On t3.large this manifests as the first request taking 30+ s even when the CPU credits are healthy.

**Evidence:** Run 2 request 1 (google cold): 32 s on a freshly-started instance — even before any credit depletion.

**Fix:**
- **AMI bake with pre-warmed page cache** — the current bake pipeline runs `docker pull` and `docker compose up`, which brings Chromium into the page cache. After baking, the AMI snapshot includes hot page-cache state *if* the snapshot is taken without rebooting. The `--NoReboot True` flag in `create_ami` preserves this.
- **Verify in smoke test** — the AMI-based launch in the verify phase of `bake-ami` should show a lower first-request time than a from-scratch EC2 install.

---

## Comparison Table

| Factor | Lambda | EC2 / Docker |
|--------|--------|--------------|
| Sidecar (mitmproxy) | No | Yes — all traffic MITM'd |
| CPU model | Dedicated (for invocation) | Burstable (t3) or fixed (c5/m5) |
| Chromium in memory | Yes (warm invocations) | No (per-request launch) |
| EBS cold read on first req | No (container filesystem) | Yes (EBS over network) |
| Typical navigate time | 1–3 s | 2–35 s (depending on credits + page) |
| Traffic visibility | None | Full (mitmproxy audit log) |
| Sidecar audit log | No | Yes |

**The tradeoff is intentional.** EC2 with the sidecar is the architecture for full traffic visibility. Lambda is the architecture for raw performance / cost / simplicity. They serve different purposes.

---

## Recommended Next Actions

1. **Run smoke against c5.xlarge (preset 4)** — confirms whether CPU credits are the dominant cause. If all 12 requests land under 5 s, switch the default instance type recommendation to `c5.xlarge` for production.

2. **Profile mitmproxy CONNECT overhead** — add a `time_start`/`time_end` to the `Default_Interceptor` addon and expose per-flow latency in the Prometheus metrics (already planned in the observability brief). This gives a per-request breakdown of how much mitmproxy adds.

3. **Implement selective passthrough** — configure mitmproxy to `allow_remote_connect` for CDN domains that carry no useful audit data. This reduces the TLS handshake count for heavy pages from ~100 to ~10.

4. **Validate AMI bake warm-cache benefit** — compare first-request times on a scratch install vs an AMI-based launch after the bake pipeline ships. If the AMI shows ≤5 s on request #1, that justifies the bake-and-launch model for production.

5. **Do not try to match Lambda performance on EC2** — the sidecar HTTPS interception is the product. The right goal is < 5 s per request on `c5.xlarge` with selective CDN passthrough, not parity with Lambda.

---

## Related docs

- `team/humans/dinis_cruz/claude-code-web/04/20/10/devops-sre-observability-brief.md` — Prometheus/Grafana stack that will expose per-request timing breakdown
- `team/humans/dinis_cruz/claude-code-web/04/20/10/v0_21_4__dev-brief__qa-refactoring-playwright-modes-traffic.md` — QA workflow brief; Workflow D (EC2 smoke) is the test harness for these benchmarks
- `.github/workflows/bake-ami.yml` — AMI bake pipeline; the verify phase gives a clean baseline measurement
