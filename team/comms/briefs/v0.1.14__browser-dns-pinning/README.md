---
title: Browser DNS pinning + HTTP/1.1 socket pooling — what bit us and what to do
date: 2026-05-19
authors: [vault-publish team]
version: v0.1.14
related:
  - team/comms/briefs/v0.1.14__vault-publish-end-to-end-flow/README.md
  - team/comms/briefs/v0.1.14__sg-va-cert-init-observability/README.md
  - sg_compute_specs/vault_publish/waker/Warming__Page.py
---

# What we observed

`sg vp register tls-test-3 --vault-key tls-test-3 --wait` succeeded end-to-end:

- Auto-DNS upserted `tls-test-3.aws.sg-labs.app A → <ec2-ip>` (INSYNC + 4/4 NS).
- EC2 booted, cert-init ran, LE-hostname cert issued, vault on `:443` returning 401.
- CLI Phase 2 polled `https://tls-test-3.aws.sg-labs.app/ui/` → got `HTTP 401` and reported
  `Path : direct to EC2 (per-slug DNS converged)`.
- `curl https://tls-test-3.aws.sg-labs.app/` from the same shell returned the vault 401 JSON
  with `Server: uvicorn` — confirming the FQDN resolves to the EC2 directly.

But the **browser tab** that was already open on `https://tls-test-3.aws.sg-labs.app/` kept
showing the warming page on every auto-refresh, even though the vault was demonstrably up.
The user manually clicked "Cancel auto-refresh", waited a beat, then reloaded — and only
then did the browser show the vault response.

Two distinct things were broken; both deserve writing down.

---

# Cause 1 — Lambda's health check was always failing on cert validation

`Waker__Handler._health_ok` and `Endpoint__Proxy` both used:

```python
urllib3.PoolManager(timeout=…)
```

`urllib3` v2's `PoolManager` defaults to `cert_reqs='CERT_REQUIRED'`. The Lambda probes the
EC2 over its **public IP** (`https://{ip}/...`) because that's what the resolver returns from
`describe_instances`. The Let's Encrypt cert on the EC2 is bound to the FQDN, not the IP, so
every cert validation against the IP failed with:

```
SSL: CERTIFICATE_VERIFY_FAILED: IP address mismatch, certificate is not valid for '18.x.x.x'
```

Consequence: `_health_ok` returned `False` forever. The waker state machine therefore stayed
in `WARMING` indefinitely — every request returned the warming HTML, never the actual vault.

The same bug would also have broken `Endpoint__Proxy.proxy()` if the warming-state path ever
yielded to the proxy path, but in practice `_health_ok` fails first.

This was identical in nature to the CLI's Phase 2 bug we fixed earlier (polling
`https://{ip}/ui/` with default `urllib3` cert validation — see commit `2c39052`).

### Fix

Both `_health_ok` and the proxy pool now create the `PoolManager` with `cert_reqs='CERT_NONE'`
+ `assert_hostname=False` (and suppress the resulting `InsecureRequestWarning`). Cert
validation is meaningless for an IP-bound probe; trust is established by the fact that the IP
came from a `describe_instances` lookup scoped by our IAM role + the `sg:slug` tag.

Files: `Waker__Handler.py:152`, `Endpoint__Proxy.py:16`.

---

# Cause 2 — browser DNS pinning via HTTP/1.1 socket pooling

Even once Cause 1 is fixed and Lambda starts proxying correctly, the user's browser will
**still** keep going to CloudFront → Lambda for the duration of the existing socket — even
after authoritative DNS has switched from the wildcard (CF) to the per-slug A record (EC2).

This is "DNS pinning" but it's misleading to think of it as a DNS-layer phenomenon. The
mechanism is at the transport layer:

1. Browser navigates to `https://<slug>.aws.sg-labs.app/`.
2. Browser asks the OS resolver — gets `99.86.x.x` (the `*` wildcard → CF edges).
3. Browser opens a TLS connection to that IP. **The TLS socket is now bound to that IP for
   its lifetime.**
4. Subsequent same-origin requests (e.g. the meta-refresh of the warming page) reuse the
   existing socket via HTTP/1.1 keep-alive. They never re-consult DNS.
5. Even after the OS DNS cache expires (TTL 60s on Route 53 records) and `nslookup` would
   now return the EC2 IP, the browser's connection pool still has a usable idle socket to
   the CloudFront IP — so it reuses it.

There is **no JS API** to invalidate a kept-alive socket. The only ways out are:

| Mechanism | Reliability | Notes |
|-----------|-------------|-------|
| Time + no traffic — let the keep-alive idle timer expire on the socket | High | Chrome/Firefox idle out ~60-90s of no activity; ~5-15s for short timeouts. Server `Connection: close` is also possible but CloudFront strips/manages hop-by-hop headers. |
| User-initiated fresh navigation (typed URL, ⌘R reload sometimes) | Medium | "Hard reload" (Shift+⌘R) bypasses the cache; behavior on the socket pool varies. |
| Open in new tab | High | New tab has its own connection pool slot allocation — often forces a fresh socket. Requires user gesture. |
| Cross-origin redirect (different host entirely) | High but heavy | Forces fresh resolution of a different name. Overkill for this. |

### What this means for our warming page

The old meta-refresh approach:

```html
<meta http-equiv="refresh" content="10">
```

…sends a request every 10s, keeping the socket pool warm. The browser never gets a chance
to idle out. Even after the vault is up and Lambda is happily proxying, the browser keeps
hitting CloudFront (because the socket is still alive). And when Lambda's `_health_ok` is
also broken (Cause 1), the result is the warming page rendering forever.

### Fix

`Warming__Page` is now JS-driven:

1. **Active phase (state=warming)** — poll the same URL every `poll_ms` (5s default). The
   socket stays alive intentionally — every poll goes through Lambda and that's fine. The
   JS reads `X-Waker-State` + `X-Waker-Ec2-State` from each response to show boot progress.

2. **Settle phase (state=proxied)** — once Lambda starts proxying (vault is healthy), the
   JS switches to a **silent countdown** of `settle_ms` (60s default). **No fetches happen
   during this countdown.** This lets:
   - the browser's keep-alive socket pool drain (idle timeout fires)
   - the OS DNS cache expire (TTL 60s on Route 53)
   - the next navigation perform a fresh DNS lookup + open a fresh socket

3. **Redirect** — after `settle_ms`, JS triggers `window.location.replace(... + '?_t=N')`.
   The fresh navigation:
   - opens a new TCP connection (socket pool was drained)
   - re-resolves DNS (cache was expired)
   - more-specific A record wins over the `*` wildcard → resolves to EC2 IP
   - browser connects direct to EC2 with the LE cert that validates for the FQDN ✓

4. **Detection that we're already direct** — every probe response is inspected for the
   `X-Waker-State` header. Its **absence** means the response did not go through Lambda
   (which always injects it) — i.e. the request landed directly on the EC2. In that case,
   we redirect immediately, skipping the settle countdown.

5. **Escape hatch** — there's an "Enter now" button that bypasses the countdown and
   navigates immediately via whatever path is currently live (proxy or direct). For the
   user who doesn't want to wait the full 60s and is fine with the Lambda hop.

Files: `Warming__Page.py:20` (template), `Warming__Page.py:142` (config injected into the JS).

---

# What still doesn't work (known limits)

- **Long-lived browser tabs**: a tab that's been open for a very long time can occasionally
  pin a host's resolved IP for the lifetime of the tab in some browsers' anti-rebinding
  defenses. The settle delay does not always defeat this. The "Enter now" button is the
  workaround — explicit user gesture.

- **Aggressive corporate DNS**: some corporate resolvers cache records beyond their TTL.
  60s settle is sometimes not enough. The user can either wait longer (increase
  `settle_ms`) or open the URL in a fresh tab.

- **HTTP/2 / HTTP/3 keep-alive**: longer idle timeouts than HTTP/1.1 (often 5+ minutes).
  Browsers do not negotiate H2/H3 with CloudFront wildcard the same way for every cert path.
  Currently our CF distribution serves H2; the settle window is still usually enough but
  may need bumping if we see it in the wild.

---

# References

- Chromium socket pool overview:
  https://www.chromium.org/developers/design-documents/network-stack/socket-pools/
- MDN — `fetch()` `cache` option (no-store is honored at the HTTP cache layer, not the socket pool):
  https://developer.mozilla.org/en-US/docs/Web/API/RequestInit#cache
- urllib3 v2 default `cert_reqs` behavior:
  https://urllib3.readthedocs.io/en/stable/advanced-usage.html#ssl-warnings
- "DNS rebinding" is a different (security) topic that sometimes intersects:
  https://en.wikipedia.org/wiki/DNS_rebinding

---

# Testability checklist

When changing the warming page or the Lambda health check, verify:

- [ ] Open `https://<new-slug>.aws.sg-labs.app/` in browser BEFORE running register —
      confirm the JS-driven warming page renders (no meta-refresh in DOM).
- [ ] Run `sg vp register <slug> --vault-key <slug> --wait` and watch the browser.
      It should transition from "EC2 booting" → "Vault is ready" → countdown → vault response,
      all within ~90-150s on a cold start.
- [ ] Open the same URL with the EC2 already terminated — should see "Vault not found"
      page (state=not_found), not the warming spinner.
- [ ] Check Lambda CloudWatch logs — the JSON-log line should show
      `state: proxied` (not `state: warming`) within seconds of cert-init completing.
- [ ] Open DevTools → Network on the warming page — the recurring fetches should have
      `_probe=<timestamp>` cache-busting query, `cache: no-store`, and 5s spacing.
- [ ] After the settle countdown, the redirect should re-fetch via a NEW connection ID
      (visible in DevTools as `Connection ID` column under timing).
