---
title: "Architecture Exploration — a dedicated front-door edge (TLS + path routing) for the content_proxy stack"
file: content_proxy__edge-front-door-options.md
author: Architect (Claude)
date: 2026-06-19
version: v0.2.63
status: EXPLORATION — options + trade-offs for human ratification. No code; no decision locked.
problem: today the vault image is the :443 edge (TLS + /pw bolted on via runtime injection). Explore replacing it with a dedicated edge that terminates TLS and routes paths to backends — future-proof for WS / VNC / WebRTC / more FastAPI services.
parent:
  - team/roles/architect/reviews/06/19/content_proxy__architecture-review.md   (D1 cross-spec import, vault-port/TLS bolt-ons)
  - library/docs/specs/v0.2.63__content-transformation-proxy-stack.md
in_house_precedent:
  - "sp vnc → Caddy (caddy-security/JWT) as the :443 edge in front of chromium + mitmweb"
  - "vault_app → Fast_API__TLS__Launcher (self-term) + cert-init sidecar; Fast_API__Reverse_Proxy for /pw"
---

# A dedicated front-door edge for the content_proxy stack

> **Recommendation up front:** introduce a **dedicated edge container** as the
> single `:443` listener (TLS termination + path routing), and make the vault,
> sg-playwright, mitmweb, and future backends plain origins behind it. For the
> edge engine, **Caddy** is the best fit *today* (auto-TLS, native WebSocket,
> simplest config, and we already run it in `sp vnc`); **Traefik** is the
> stronger choice *if/when* per-stack dynamic backend discovery dominates. Keep
> our `Fast_API__Reverse_Proxy` for in-app same-origin needs only — not the edge.

---

## 1. Why change — the problem with "vault as edge"

Today the `sg-send-vault` container is the front door: it terminates TLS on `:443`
and we inject `/pw` into its FastAPI via a runtime override. That created the
exact debt the architecture review flagged:

- **Cross-spec patch (D1):** `content_proxy` imports `vault_app`'s reverse-proxy
  override to bolt `/pw` onto an image we don't own.
- **Edge concerns live in an app:** TLS, path routing, and auth translation are
  smeared across the vault app + cert-init + a Python httpx proxy.
- **Two `:443` semantics** (vault HTTP-on-8080 vs TLS-on-443) caused a real bug.
- **Hard ceiling on streaming:** the `Fast_API__Reverse_Proxy` (httpx, buffered
  request→response) **cannot proxy WebSockets, Server-Sent Events, VNC, or
  WebRTC**. The moment we add a streaming backend, this design is a dead end.

A dedicated edge inverts this: **one component owns the edge** (TLS + routing),
every workload is a dumb origin, and adding a backend is a config edit.

```
                         ┌──────────────────────── EC2 instance ───────────────────────┐
   Internet  ──:443──▶   │  EDGE (TLS terminate + path route)                            │
   (browser)            │     /            → vault-app:8080      (HTTP)                  │
                        │     /pw/*        → sg-playwright:8000  (HTTP + WS)             │
                        │     /mitm/*      → mitmweb:8081        (HTTP + WS)  [optional] │
                        │     /vnc/*       → noVNC:6080          (WS)         [future]   │
                        │     /rtc/*       → signaling:xxxx      (WS)         [future]   │
   (proxy-configured ─────────────────────────────────────────────────────────────────│
    browser)  ──:8080──▶   mitmproxy-ext  (raw forward proxy — stays a SEPARATE port)   │
                         └──────────────────────────────────────────────────────────────┘
```

Note: **mitmproxy-ext (Mode-1 forward proxy) stays its own port** — a forward
proxy is not a reverse-proxy backend; it terminates its own CONNECT tunnels.

---

## 2. The streaming dimension (the real future-proofing test)

Each future workload stresses the edge differently. This table is the deciding lens:

| Workload | Transport | What the edge must do | FastAPI/httpx proxy | nginx | Caddy | Traefik | Envoy/HAProxy |
|----------|-----------|------------------------|:---:|:---:|:---:|:---:|:---:|
| HTTP path routing | HTTP/1.1+2 | route by prefix, rewrite, auth header | ✅ | ✅ | ✅ | ✅ | ✅ |
| FastAPI WebSockets | WS (Upgrade) | honour `Upgrade`/`Connection`, no buffering | ❌ | ✅ | ✅ | ✅ | ✅ |
| Server-Sent Events / chunked | HTTP stream | disable response buffering | ⚠ (buffers) | ✅ | ✅ | ✅ | ✅ |
| noVNC | WS → VNC | WS proxy to a noVNC sidecar | ❌ | ✅ | ✅ | ✅ | ✅ |
| Raw VNC (no noVNC) | TCP | L4 TCP passthrough | ❌ | ✅ (stream) | ⚠ (layer4 plugin) | ✅ (TCP router) | ✅ |
| WebRTC signaling | WS/HTTP | proxy the signaling channel | ❌ | ✅ | ✅ | ✅ | ✅ |
| WebRTC **media** | UDP/SRTP, ephemeral ports | **NOT a reverse-proxy job** → TURN/direct ports/host-net | ❌ | ❌ | ❌ | ❌ | ❌ |

**Two hard truths this surfaces:**
1. **Our httpx-based `Fast_API__Reverse_Proxy` fails the streaming column entirely.** It's fine as an in-app same-origin shim; it is the wrong tool for the edge.
2. **WebRTC media never goes through any reverse proxy.** The edge handles only signaling (WS); media needs a TURN server (e.g. coturn) and/or direct UDP ports + host networking. Plan for that separately — don't expect the edge to solve it.

---

## 3. The options

### A. Our own FastAPI / Python edge (extend `Fast_API__Reverse_Proxy`)
- **Pros:** same stack (Type_Safe, osbot), auth translation in Python, zero new tools, full control, testable in-process.
- **Cons:** **no WebSocket/stream/TCP support** (httpx is request-buffered) — would require a rewrite onto an ASGI streaming proxy or raw `asyncio` TCP, i.e. *building a proxy*. TLS/ACME would also be ours to run (`Fast_API__TLS__Launcher` + cert-init, which we already maintain). Performance and correctness risk for the edge role.
- **Verdict:** **keep it for in-app same-origin routing only.** Promoting it to the edge means reinventing nginx, badly. ❌ as the edge.

### B. nginx
- **Pros:** the industry default; rock-solid TLS termination; path routing + rewrites; **WebSocket upgrade**; SSE/chunked streaming; **`stream{}` module for raw TCP/UDP** (raw VNC, etc.); tiny footprint; huge ops familiarity.
- **Cons:** we generate `nginx.conf` (a templating surface, like our compose templates); **ACME is external** (certbot sidecar or pre-provisioned cert) — no built-in auto-TLS; reload-to-reconfigure.
- **Verdict:** the safe, maximal-capability choice. Best if raw-TCP/L4 (raw VNC) becomes a requirement. ✅

### C. Caddy  ⭐ (recommended for now)
- **Pros:** **built-in automatic HTTPS (ACME)**, incl. internal self-signed for IPs; the simplest config (`Caddyfile`); **native WebSocket + streaming** (no special directives); `reverse_proxy` one-liners; `caddy-security` plugin for JWT/forward-auth; **we already build + run Caddy in `sp vnc`** (caddy + caddy-security via xcaddy, JWT portal, `/mitmweb` reverse proxy) → in-house experience + a copyable template.
- **Cons:** raw L4/TCP needs the `layer4` plugin (less first-class than nginx `stream`); **publicly-trusted bare-IP certs** depend on whether the edge's *built-in* ACME implements LE's IP-identifier profile (see §6) — if not, reuse the proven `cert-init` and mount the cert (Caddy's *internal* CA always covers IP for the self-signed path).
- **Verdict:** **best fit today** — auto-TLS + native WS + simplest config + existing precedent. It directly removes the vault patch and the vault-port/TLS bolt-ons. ⭐

### D. Traefik
- **Pros:** **container-native dynamic config** — discovers backends via Docker labels (add a container + labels → routed, no edge restart); built-in ACME; first-class **WS, gRPC, TCP, UDP routers**; rich **middlewares** (auth, headers, rate-limit, strip-prefix). Ideal when the backend set grows and varies per stack.
- **Cons:** heavier; label-driven config is a different mental model; more moving parts than Caddy for a fixed 3–5 backend set.
- **Verdict:** **the choice when dynamic per-stack backend composition becomes the priority** (many optional containers toggled per launch). Slightly ahead of where we are; revisit when the backend matrix grows. ✅ (future)

### E. Envoy
- **Pros:** most powerful L7+L4 (gRPC, advanced routing, retries, circuit-breaking, deep observability/xDS).
- **Cons:** heavy, steep config (xDS/YAML), operationally serious. Overkill for a per-launch ephemeral box.
- **Verdict:** over-engineered for this stage. ❌ for now.

### F. HAProxy
- **Pros:** elite L4/L7 performance, excellent TCP/stream + WS.
- **Cons:** ACME/dynamic-config ergonomics weaker than Caddy/Traefik; config is its own dialect.
- **Verdict:** strong if raw-TCP throughput dominates; otherwise nginx/Caddy win on ergonomics. ◻ niche.

---

## 4. Decision matrix

| Criterion (weight) | FastAPI proxy | nginx | **Caddy** | Traefik |
|--------------------|:---:|:---:|:---:|:---:|
| WebSocket / streaming | ✗ | ✓✓ | ✓✓ | ✓✓ |
| Raw TCP/UDP (raw VNC) | ✗ | ✓✓ | ✓(plugin) | ✓ |
| Auto-TLS / ACME | ✗(ours) | ✗(certbot) | ✓✓ | ✓✓ |
| Config simplicity | ✓ | ◻ | ✓✓ | ◻ |
| Dynamic backend discovery | ✗ | ✗ | ◻ | ✓✓ |
| In-house precedent | ✓✓ | ◻ | ✓✓ (sp vnc) | ✗ |
| Removes the vault patch (D1) | ✗ | ✓ | ✓ | ✓ |
| Our-stack / Type_Safe control | ✓✓ | ✗ | ✗ | ✗ |
| Footprint / simplicity | ✓ | ✓✓ | ✓✓ | ◻ |

**Reading:** any of nginx/Caddy/Traefik removes the cross-spec patch and unlocks
streaming. **Caddy** wins on ergonomics + auto-TLS + the `sp vnc` precedent;
**Traefik** is the upgrade path for dynamic composition; **nginx** is the
fallback if raw-L4 becomes central. The FastAPI proxy is disqualified for the
edge but **retained for in-app same-origin** use.

---

## 5. What this changes in content_proxy (Caddy path)

| Today | With an edge |
|-------|--------------|
| vault terminates TLS on `:443`; `/pw` injected via the vault override (D1) | **edge** terminates TLS on `:443`; vault is a plain origin on `:8080` |
| `Vault_App__Reverse_Proxy__Override` (cross-spec import) | **deleted** — routing is a Caddyfile |
| `cert-init` sidecar feeds the vault's `FAST_API__TLS__*` | edge does ACME/self-signed itself (or still uses cert-init feeding the edge) |
| vault-port bug (443:443 vs 8080) | gone — vault only ever listens HTTP on 8080 |
| add a backend = patch the vault app | add a backend = **add a Caddyfile route** |
| WS/VNC/WebRTC = impossible | WS/streaming = native; media = separate TURN/direct-port plan |

New shape: a `Content_Proxy__Edge__Template` renders the `Caddyfile` (the same
way `Vnc__*` already renders one), the vault/playwright/mitmweb become origins,
and `proxy CA` (Mode-1 mitmproxy) is untouched (still its own `:8080`).

---

## 6. TLS / cert sourcing — how the edge gets a cert (corrected)

The repo has **three** cert paths, all via `cert-init` (`Cert__ACME__Client`) —
**none use AWS ACM**:

1. `self-signed` — offline, browser warns.
2. `letsencrypt-ip` — **publicly-trusted cert for the bare IP** (LE's short-lived IP-identifier profile, http-01 on `:80`). *(Earlier draft wrongly said ACME won't issue for IPs — it does; this is exactly what `sg cp --tls letsencrypt` and `sg va` use.)*
3. `letsencrypt-hostname` — publicly-trusted cert for an FQDN; **AWS Route 53** (`--with-aws-dns`) writes the A record so the FQDN points at the box, then LE **http-01**. So `sg va`'s "AWS cert" = **Route 53 (DNS) + Let's Encrypt** — *not* ACM.

**Does the edge (Caddy) work with all of these? Yes — two ways:**

- **(Recommended) Edge consumes `cert-init`'s output.** Keep the proven sidecar minting the cert (ip/hostname/self-signed) to a shared volume; point Caddy at it: `tls /certs/cert.pem /certs/key.pem`. Caddy does **no** ACME — it just serves the cert. This mirrors `sg va` exactly and covers **all three** modes (incl. the LE-IP path) with zero new cert logic at the edge.
- **(Optional) Caddy's own ACME.** For a **hostname**, Caddy can issue itself — http-01 (it owns `:443`/`:80`) or **DNS-01 via the `caddy-dns/route53` plugin** (using the instance's AWS creds/role) — a clean fit with the existing Route 53 usage. For a **bare IP**, prefer `cert-init` (Caddy's built-in ACME may not yet request LE's IP-identifier profile).

> **One thing that genuinely does NOT work: a true ACM (AWS Certificate Manager) *public* cert in Caddy/nginx.** ACM public certs are non-exportable — they only terminate at an ALB/CloudFront. So "ACM" implies the ALB path, not a container edge. But since `sg va` uses Route 53 + LE (not ACM), this never blocks parity.

## 6c. The hostname requirement — `*.sgraph.ai` for external callers (e.g. Claude)

**This is now a first-class requirement, not optional.** For an external service
(Claude, agents, webhooks, browsers without a custom CA) to talk to a vault, the
box needs a **stable, publicly-trusted HTTPS hostname** — a per-launch IP with a
self-signed/IP cert won't do (no trust, IP churns per launch). This is exactly
the `sg va --with-aws-dns` path:

1. On `create`, **Route 53** upserts `<slug>.sgraph.ai → box IP` (reuse the
   existing Auto-DNS / `sg aws dns` helper vault_app already uses).
2. `cert-init` runs `letsencrypt-hostname` → publicly-trusted LE cert for the FQDN.
3. The box is reachable at `https://<slug>.sgraph.ai/` (vault), `…/pw/`, etc. —
   trusted by any client, no CA import.

**This is where a domain-based edge is the *right* tool (not a workaround):**
- **Caddy + the hostname owns its own ACME** — http-01 (it holds `:80`/`:443`)
  or **DNS-01 via `caddy-dns/route53`** (the instance role does the Route 53
  TXT) — and **auto-renews**. For a long-lived/stable `<slug>.sgraph.ai`, Caddy
  managing the cert lifecycle is cleaner than a one-shot `cert-init`.
- For the **ephemeral IP** quick-path, keep `cert-init` (LE-IP) feeding the edge.

So the edge gives a clean two-tier story:
| Tier | URL | Cert | Who reaches it |
|------|-----|------|----------------|
| quick / dev | `https://<ip>/` | self-signed or LE-IP (cert-init) | you, with CA import or click-through |
| **integration / prod** | `https://<slug>.sgraph.ai/` | **LE-hostname (Route 53 + ACME)** | **Claude / any external service, trusted** |

`content_proxy` should therefore grow a `--hostname` / `--with-aws-dns` create
option (mirroring `sg va`) and reuse the Route 53 helper — the edge then serves
that FQDN with an auto-renewed trusted cert.

## 6b. Other risks & caveats
- **One more container** on the box (the edge). Negligible footprint; big simplification.
- **WebRTC media is out of scope for the edge** — budget a TURN server / direct ports when that workload lands.
- **One more container** on the box (the edge). Negligible footprint; big simplification.
- **WebRTC media is out of scope for the edge** — budget a TURN server / direct ports when that workload lands.
- **Auth translation** (browser cookie/token → backend `X-API-Key`) currently done in the Python proxy must move to the edge (Caddy `header_up` / forward-auth, or keep a tiny per-backend auth shim). Verify each backend's auth fits the edge's primitives.

---

## 7. Recommendation & next step
1. **Adopt a dedicated edge** as the `:443` front door; demote the vault to a plain origin. This alone resolves D1 + the vault-port/TLS bolt-ons and unblocks streaming.
1b. **Make the `<slug>.sgraph.ai` hostname path first-class** (reuse `sg va`'s Route 53 + LE-hostname) — it's the only way external callers like Claude get a stable trusted URL. The edge (Caddy) auto-manages that cert.
2. **Use Caddy** (reuse the `sp vnc` build/template) for the first cut; **re-evaluate Traefik** when per-stack dynamic backends or rich middleware become the driver.
3. **Retain `Fast_API__Reverse_Proxy`** for in-app same-origin only; stop using it as the edge.
4. **Keep WebRTC media on a separate track** (TURN/direct ports).

Suggested follow-up artefact: a thin PoC — `Content_Proxy__Edge__Template` (Caddyfile) routing `/ → vault:8080`, `/pw/* → sg-playwright:8000` with TLS at the edge — proving the vault patch can be deleted, behind a `--edge caddy|none` flag so it's introduced without breaking the current path.
</content>
