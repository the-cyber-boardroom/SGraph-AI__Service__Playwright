# [EC2] Solution At A Glance

**Applies to:** EC2 / direct compute deployments. Lambda / serverless retains its direct-to-internet topology — see the Lambda note at the bottom and `01__architecture.md` for detail.

One-page summary. For details: `01__architecture.md`.

---

## The architecture in one sentence

**On EC2:** every Playwright container is paired with an `agent_mitmproxy` sidecar; all browser traffic routes through the sidecar, which provides audit logging, correlation IDs, runtime policy control, and (optionally) authenticated upstream-proxy forwarding.

**On Lambda:** Playwright goes direct to the internet (no sidecar). Authenticated-proxy support is not offered; no-auth proxy configuration is possible via Playwright's native proxy config.

---

## Topology

```
┌───────────────────────────────────────────────────────────────┐
│  EC2 instance (one of N behind an NLB + ASG)                  │
│                                                               │
│   ┌──────────────────┐       ┌───────────────────────────┐    │
│   │ playwright       │       │ agent_mitmproxy           │    │
│   │ container        │       │ container                 │    │
│   │                  │       │                           │    │
│   │  FastAPI         │       │  mitmweb :8080 ◀──────────┼────┼── browser traffic
│   │  (API)           │       │   + addon pipeline        │    │    (always through here)
│   │                  │       │      • Default_Interceptor │    │
│   │  spawns          │       │      • Audit_Log          │    │
│   │  browsers ───────┼───────┼─▶ :8080                   │    │
│   │                  │       │                           │    │
│   │                  │       │  uvicorn :8000 (admin)    │    │
│   │                  │       │   /health /ca /config /ui │    │
│   └──────────────────┘       └───────────────────────────┘    │
│                                         │                     │
└─────────────────────────────────────────┼─────────────────────┘
                                          │
                                          ▼
                       Direct to internet,  OR  via authenticated
                       (default, no config)    upstream (env vars set)
```

---

## Two modes, one image

| Mode | Set `AGENT_MITMPROXY__UPSTREAM_*`? | Traffic path |
|---|---|---|
| Direct | No | Browser → sidecar → Internet |
| Upstream | Yes | Browser → sidecar → authenticated upstream → Internet |

Addon pipeline runs in both. Observability story is identical. The upstream option is the fix for the proxy-auth bug described in `02__origin-story.md`.

---

## Scaling

```
      NLB
       │
   ────┴────
   │   │   │
  EC2 EC2 EC2      ← each is self-contained (2 containers, no shared state)
   │   │   │
   └───┼───┘
    ASG with launch template pointing at a baked AMI
```

Each API call is fully self-contained. No session stickiness needed. ASG health checks probe instance `/health` which verifies both containers are live. Unhealthy instances get terminated and replaced.

---

## Packaging

Same artefact, three distribution channels:

| Channel | How |
|---|---|
| Local dev | `docker compose up` |
| Self-hosted prod | ASG with AMI, UserData injects env vars |
| AWS Marketplace | AMI subscription |

---

## What's shipped (v0.1.32)

- `agent_mitmproxy` Docker image → ECR
- Two bundled addons (correlation + audit-log)
- Admin FastAPI with health, CA, config, UI passthrough
- EC2 provisioning spike script
- Unit-tested CI pipeline

## What's next

1. Upstream-forwarding mode (1-day PR)
2. Wire Playwright service to launch browsers pointing at the sidecar
3. `docker compose` for local dev
4. NLB + ASG IaC
5. AMI publishing pipeline (for Marketplace)
6. Fluent-bit → OpenSearch

See `03__roadmap.md` for detail.

---

## 🟡 Lambda note (out of scope for this architecture)

Lambda deployments retain their current topology: **Playwright goes direct to the internet**, no sidecar, no addon pipeline, no audit logging via this mechanism (Lambda has its own CloudWatch-based observability story).

Why the sidecar doesn't fit Lambda: the pattern assumes a persistent second process alongside Playwright. Lambda's execution model is single-container-per-invocation with tight Firecracker resource constraints and a cold-start cost amortised per invocation — running mitmproxy as a sibling process there is awkward and fragile.

**What works on Lambda:**
- Direct browsing (no proxy)
- No-auth proxy via Playwright's native `proxy={'server': '...'}` config

**What doesn't work on Lambda:**
- Authenticated upstream proxy (same retry-pattern bug as on EC2, and no sidecar workaround option)
- Audit logging through the `agent_mitmproxy` pipeline
- Correlation IDs, CA distribution, runtime policy control

If authenticated-proxy support becomes a Lambda requirement, the likely path is an external sidecar on EC2 reachable over the VPC — not a sidecar inside the Lambda. See `01__architecture.md` → *What this architecture does not cover* for detail.
