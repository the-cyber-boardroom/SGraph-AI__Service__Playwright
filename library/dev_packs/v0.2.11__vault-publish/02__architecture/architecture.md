# Architecture

Two architectures sit side by side: the **infrastructure** (DNS / cert / CDN /
compute) and the **code** (`vault_publish` package). They meet at the waker Lambda.

---

## 1. Infrastructure — four layers

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │ Layer 1 — DNS            Route 53 hosted zone sgraph.app            │
  │   *.sgraph.app           ALIAS/A  → CloudFront distribution         │
  │   *.qa.sgraph.app        ALIAS/A  → same distribution               │
  │   *.dev.sgraph.app       ALIAS/A  → same distribution               │
  │   *.main.sgraph.app      ALIAS/A  → same distribution               │
  │   (set once; never changes per slug)                                │
  ├─────────────────────────────────────────────────────────────────────┤
  │ Layer 2 — Certificate    ACM wildcard cert in us-east-1             │
  │   SANs: *.sgraph.app, *.qa.sgraph.app, *.dev.sgraph.app,            │
  │         *.main.sgraph.app                                           │
  │   (set once; auto-renews; DNS-validated via the Route 53 zone)      │
  ├─────────────────────────────────────────────────────────────────────┤
  │ Layer 3 — CDN            One CloudFront distribution                │
  │   alternate domain names = the four wildcards above                 │
  │   origin failover: primary = live path, secondary = waker Lambda    │
  │   origin connection timeout tuned low (≈2 s, 1 attempt)             │
  ├─────────────────────────────────────────────────────────────────────┤
  │ Layer 4 — Compute        Per-slug EC2, private subnet, no public IP │
  │   generic AMI; control-plane FastAPI; idle-shutdown timer           │
  │   reached by CloudFront as a VPC origin (Phase 2b) or proxied by    │
  │   the waker (Phase 2a)                                              │
  └─────────────────────────────────────────────────────────────────────┘
```

**Why single-label wildcards matter.** ACM and DNS wildcards match *exactly one*
label. `*.sgraph.app` covers `sara-cv.sgraph.app` but **not**
`sara-cv.qa.sgraph.app`. Every environment (and, later, every region) is its own
single-label wildcard — a separate SAN on the cert and a separate alternate domain
name on the distribution. The env set and region set must therefore be **closed,
enumerable lists**. This is why region-in-hostname is deferred (locked decision
#15): it is additive, not free.

---

## 2. Code — the `vault_publish` package

A new top-level package, structured like everything else in the repo.

```
  vault_publish/
    schemas/              Tier 1 data — Schema__*, Enum__*, Safe_* (one class per file)
    service/              Tier 1 logic — pure Type_Safe service classes
    fast_api/             Tier 2 — FastAPI routes (thin delegation)
    cli/                  Tier 3a — `sg vp` Typer verb tree
    waker/                Tier 3b — the CF ⇄ HTTP adapter for the Lambda
    version
```

### Tier 1 — service classes (pure)

No Typer, no Console, no Rich, no Lambda event types. Callable identically from a
test, the CLI, the FastAPI route, and the waker. The candidate service classes:

| Class | Responsibility |
|-------|----------------|
| `Slug__Validator` | Enforce the naming rules and the reserved/profanity lists. The single place slug rules live. |
| `Slug__Resolver` | `slug → (Transfer-ID, read key)` — the deterministic derivation. Wraps the SG/Send simple-token mechanism. |
| `Vault__Fetcher` | Fetch the immutable vault folder from `send.sgraph.ai` by `(Transfer-ID, read key)`. The only class that talks to SG/API. |
| `Manifest__Verifier` | Verify the provisioning manifest's signature against the key from the billing record. Reject on failure. |
| `Manifest__Interpreter` | Translate a verified manifest into allowlisted control-plane operations. The allowlist boundary. |
| `Instance__Manager` | Start / stop / status of the per-slug EC2 — via `osbot-aws`. Idempotent. Arms / re-arms the idle-shutdown timer. |
| `Control_Plane__Client` | Drive provisioning through the instance's control-plane FastAPI, authenticated with the single-use key. |
| `Publish__Service` | The orchestrator. `register`, `unpublish`, `wake`, `status` — composes the classes above. The trigger contract. |

### Tier 2 — FastAPI routes

Pure delegation to `Publish__Service`. Every route returns `.json()` on a
`Type_Safe` schema. See `03__cli/cli-surface.md` for the route list.

### Tier 3a — `sg vp` CLI

A Typer verb tree built with the repo's `Spec__CLI__Builder` shape. Thin wrapper —
constructs a request schema, calls Tier 2 / Tier 1, renders the response.

### Tier 3b — the waker Lambda

The same `vault_publish` FastAPI app, deployed behind the AWS Lambda Web Adapter,
exposed as a Lambda Function URL that CloudFront uses as its failover origin. The
**only** edge-specific code is the translation between the incoming request and a
FastAPI call — extract the slug from the forwarded Host header, invoke the route,
return the response. No business logic. This is the same single-image model as the
repo's existing `lambda_handler.py`.

```
  CloudFront ──(origin failover)──► Lambda Function URL
                                         │
                                    Lambda Web Adapter
                                         │
                                    vault_publish FastAPI app
                                         │
                                    Publish__Service  (Tier 1)
```

---

## 3. The trigger contract

`Publish__Service` exposes one shape per operation:
`request: Schema__VaultPublish__*__Request → Schema__VaultPublish__*__Response`.
Because the service classes are pure, the same `.wake(request)` call is made by:

- a pytest test (in-memory composition, no mocks),
- the `sg vp wake` CLI command,
- the FastAPI `/vault-publish/wake` route,
- the CloudFront-invoked waker Lambda.

Keeping that contract clean is what makes "one service layer, three callers"
(principle 1) real rather than aspirational.

---

## 4. Where the boundaries are

| Boundary | The only class allowed to cross it |
|----------|------------------------------------|
| Talking to SG/API (`send.sgraph.ai`) | `Vault__Fetcher` |
| Talking to AWS (EC2, Route 53, ACM, CloudFront) | classes in `service/`, always via `osbot-aws` |
| Talking to an instance's control-plane | `Control_Plane__Client` |
| Deciding what a manifest is *allowed* to do | `Manifest__Interpreter` (the allowlist) |
| Slug naming rules | `Slug__Validator` |

These mirror the repo's existing single-responsibility boundaries
(`Artefact__Writer` is the only sink writer, `Request__Validator` holds all
cross-schema validation, etc.). The Architect rejects any change that blurs them.
