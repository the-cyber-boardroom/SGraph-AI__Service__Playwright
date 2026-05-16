---
title: "04 — The vault-publish spec"
file: 04__vault-publish-spec.md
author: Claude (Architect)
date: 2026-05-16 (UTC hour 15)
parent: README.md
---

# 04 — The vault-publish spec

What lives inside `sg_compute_specs/vault_publish/`. Peer of `sg_compute_specs/vault_app/`, `playwright/`, `mitmproxy/`, `elastic/`, etc.

The spec is **thin glue** over the substrate (`sg vault-app`) and the platform primitives (`sg aws cf`, `sg aws lambda`, `sg aws dns`). The only domain logic that lives here is **slug policy** and **wake routing**. Everything that smells like AWS-resource-management is delegated.

---

## 1. Folder layout

```
sg_compute_specs/vault_publish/
├── __init__.py                                 (empty per CLAUDE.md §22)
├── manifest.py                                 spec metadata (catalogue entry)
├── version                                     spec version, decoupled from repo
│
├── cli/
│   ├── __init__.py
│   └── Cli__Vault_Publish.py                   `sg vault-publish ...`  + alias `sg vp`
│
├── service/
│   ├── __init__.py
│   ├── Vault_Publish__Service.py               orchestrator (register / unpublish / status / list / bootstrap)
│   ├── Slug__Validator.py                      naming policy — ported from old vault_publish/
│   ├── Slug__Registry.py                       SSM Parameter Store backend
│   ├── Slug__Routing__Lookup.py                read-only registry lookup used by the Waker
│   └── reserved/
│       ├── __init__.py
│       └── Reserved__Slugs.py                  reserved + profanity sets — ported
│
├── schemas/
│   ├── __init__.py
│   ├── Safe_Str__Slug.py                       ported (charset / length only)
│   ├── Safe_Str__Vault__Key.py                 the sgit vault key the slug binds to
│   ├── Enum__Slug__Error_Code.py               ported (8 specific reasons)
│   ├── Enum__Vault_Publish__State.py           UNREGISTERED | STOPPED | PENDING | RUNNING | STOPPING
│   ├── Schema__Vault_Publish__Entry.py         one slug's registry record
│   ├── Schema__Vault_Publish__Register__Request.py
│   ├── Schema__Vault_Publish__Register__Response.py
│   ├── Schema__Vault_Publish__Unpublish__Response.py
│   ├── Schema__Vault_Publish__Status__Response.py
│   ├── Schema__Vault_Publish__List__Response.py
│   ├── Schema__Vault_Publish__Bootstrap__Response.py
│   ├── List__Slug.py
│   └── List__Schema__Vault_Publish__Entry.py
│
├── waker/                                      the Lambda code (deployed as one function)
│   ├── __init__.py
│   ├── lambda_entry.py                         AWS Lambda Web Adapter / Function URL entry
│   ├── Waker__Handler.py                       request dispatch — parse / lookup / decide
│   ├── Endpoint__Resolver.py                   abstract base — `resolve(entry) -> (state, url|'')`
│   ├── Endpoint__Resolver__EC2.py              phase 2c — uses EC2_Instance
│   ├── Endpoint__Resolver__Fargate.py          phase 3 (PROPOSED — does not exist yet)
│   ├── Endpoint__Proxy.py                      urllib3-based reverse-proxy
│   ├── Warming__Page.py                        HTML generator (auto-refresh)
│   └── Slug__From_Host.py                      Host header → slug; reuses Route53__Zone__Resolver shape
│
└── tests/
    ├── __init__.py
    ├── test_Slug__Validator.py                 ported, same assertions
    ├── test_Slug__Registry.py                  in-memory SSM client
    ├── test_Vault_Publish__Service.py          orchestrator end-to-end
    ├── test_Cli__Vault_Publish.py              CLI golden-file
    └── waker/
        ├── __init__.py
        ├── test_Slug__From_Host.py
        ├── test_Endpoint__Resolver__EC2.py     in-memory EC2_Instance
        ├── test_Endpoint__Proxy.py
        └── test_Waker__Handler.py              full state-machine coverage
```

About 30 production files + 8 test files. Of those, **5 (the slug primitives + validator + reserved set + their tests) are direct ports from the top-level `vault_publish/` package** — they survived the v0.2.11 → v2 redesign. Everything else is new (and small, because it delegates).

---

## 2. The slug registry — `Slug__Registry`

Backed by SSM Parameter Store. Namespace:

```
/sg-compute/vault-publish/<slug>/instance-id        StringParameter
/sg-compute/vault-publish/<slug>/stack-name         StringParameter
/sg-compute/vault-publish/<slug>/vault-key          SecureStringParameter   (the sgit vault key)
/sg-compute/vault-publish/<slug>/owner              StringParameter         (free-text caller id)
/sg-compute/vault-publish/<slug>/registered-at      StringParameter         (ISO 8601 UTC)
/sg-compute/vault-publish/<slug>/region             StringParameter
/sg-compute/vault-publish/<slug>/fqdn               StringParameter         (e.g. sara-cv.sg-compute.sgraph.ai)
```

`Slug__Registry` API:

```python
class Slug__Registry(Type_Safe):
    namespace_prefix : str = '/sg-compute/vault-publish'

    def put(self, entry: Schema__Vault_Publish__Entry) -> None: ...
    def get(self, slug: str) -> Optional[Schema__Vault_Publish__Entry]: ...
    def delete(self, slug: str) -> bool: ...
    def list_slugs(self) -> List__Slug: ...           # uses Parameter.list with the namespace
```

Backed by `osbot_aws.helpers.Parameter` (see [`02 §7.4`](02__what-exists-today.md#74-ssm-parameter-store--the-slug-registry-backing)). The vault key is stored as a SecureStringParameter (KMS-encrypted at rest); reads use `get_secret`.

`Slug__Routing__Lookup` is the read-only subset the Waker uses; isolated for two reasons:
- Lambda code keeps its surface small (no need for `put` / `delete`)
- Cache-friendly — the Waker can wrap the read with a short in-Lambda TTL cache without coupling to the full registry surface

---

## 3. Slug policy — `Slug__Validator` + `Reserved__Slugs`

**Ported wholesale** from the top-level `vault_publish/` package. Three files:

- `schemas/Safe_Str__Slug.py` — charset `[a-z0-9\-]+`, max 40, strict MATCH validation, allow_empty=True (for response defaults)
- `service/reserved/Reserved__Slugs.py` — frozenset of reserved slugs + basic profanity filter; registry-class exception per CLAUDE.md §21
- `service/Slug__Validator.py` — full naming policy returning `Enum__Slug__Error_Code` (TOO_SHORT / TOO_LONG / BAD_CHARSET / LEADING_HYPHEN / TRAILING_HYPHEN / DOUBLE_HYPHEN / RESERVED / PROFANE)

These are the only pieces of the v0.2.11 work that survive verbatim. Tests port verbatim too.

**What changes** vs the old top-level package:

- `Slug__Resolver` (the bespoke "derive (Transfer-ID, read-key) from slug") — **deleted.** The vault key is stored on the registry entry, not derived. The SG/Send open question #1 disappears.
- `Vault__Fetcher`, `Manifest__Verifier`, `Manifest__Interpreter` — **deleted.** No bespoke manifest; the `sg-send-vault` image serves the vault content directly. SG/Send open questions #3 and #4 disappear.
- `Instance__Manager`, `Control_Plane__Client` — **deleted.** Replaced by direct calls to `sg vault-app start/stop` and the existing host-control-plane (which is already on every vault-app box at `127.0.0.1:19009`).
- `Waker__Lambda__Adapter` (the stub HTML adapter I wrote) — **replaced** by the real `Waker__Handler` in `waker/`.

---

## 4. The orchestrator — `Vault_Publish__Service`

The spec's single service class. Composes:

```python
class Vault_Publish__Service(Spec__Service__Base):
    validator    : Slug__Validator
    registry     : Slug__Registry
    vault_app    : Vault_App__Service             # the substrate
    route53      : Route53__AWS__Client            # for the bootstrap wildcard ALIAS
    cf_client    : CloudFront__AWS__Client         # phase 2a primitive
    lambda_client: Lambda__AWS__Client             # phase 2b primitive
    lambda_deployer : Lambda__Deployer             # phase 2b primitive
```

Methods (each maps 1:1 to a CLI verb):

```python
def register(self, slug: str, vault_key: str, owner: str = '', region: str = '') -> Schema__Vault_Publish__Register__Response:
    # 1. validate slug → return error if invalid
    # 2. registry.get(slug) → reject if already registered
    # 3. compose a Vault_App create request:
    #      - stack_name        = slug
    #      - seed_vault_keys   = vault_key
    #      - with_aws_dns      = True              (writes <slug>.sg-compute.sgraph.ai)
    #      - with_tls_check    = True              (letsencrypt-hostname auto-flips on)
    #      - max_hours         = N                 (idle-stop, not terminate)
    #      - storage_mode      = 'disk'            (vault data on EBS root)
    # 4. vault_app.create_stack(request)
    # 5. registry.put(Schema__Vault_Publish__Entry(slug, instance_id, stack_name, vault_key, owner, ...))
    # 6. return Register__Response with fqdn / url / vault_app_info

def unpublish(self, slug: str) -> Schema__Vault_Publish__Unpublish__Response:
    # 1. registry.get(slug) → 404 if absent
    # 2. vault_app.delete_stack(region, slug)     (terminates EC2 + SG)
    # 3. delete per-slug A record  (already-stopped case may have it gone; idempotent)
    # 4. registry.delete(slug)

def status(self, slug: str) -> Schema__Vault_Publish__Status__Response:
    # 1. registry.get(slug)
    # 2. vault_app.get_stack_info(region, slug) → state, public_ip, time_remaining_sec
    # 3. route53.get_record(zone, fqdn, 'A') → present? value matches public_ip?
    # 4. combine into a Status__Response

def list_slugs(self) -> Schema__Vault_Publish__List__Response:
    # registry.list_slugs() — return entries (vault keys redacted)

def bootstrap(self) -> Schema__Vault_Publish__Bootstrap__Response:
    # one-time AWS-side setup; see §6 below.
```

`register` and `unpublish` are gated by `SG_AWS__DNS__ALLOW_MUTATIONS=1` (because they mutate DNS) and `SG_VAULT_PUBLISH__ALLOW_MUTATIONS=1` (the spec's own gate, mirroring the platform pattern).

---

## 5. The Waker Lambda handler

Code lives at `sg_compute_specs/vault_publish/waker/`, deployed as a single Lambda by `sg aws lambda deployment deploy ...` (called from `bootstrap`).

### 5.1 Entry-point shape

The Lambda uses **AWS Lambda Web Adapter** (the repo's deploy pattern — see `lambda_entry.py` precedent). That means the Lambda runs a FastAPI app; the Function URL forwards the HTTP request to the FastAPI process which returns the response. We get a regular HTTP handler, not a manual event-shape parser.

```python
# sg_compute_specs/vault_publish/waker/lambda_entry.py
from fastapi import FastAPI, Request
from sg_compute_specs.vault_publish.waker.Waker__Handler import Waker__Handler

app     = FastAPI()
handler = Waker__Handler().setup()

@app.get('/{full_path:path}')
@app.post('/{full_path:path}')
@app.put('/{full_path:path}')
@app.delete('/{full_path:path}')
@app.patch('/{full_path:path}')
async def catchall(request: Request, full_path: str):
    return await handler.handle(request)
```

The Lambda Function URL is configured `auth_type='NONE'` (public — CloudFront is the gate); `invoke_mode='BUFFERED'` for phase 2; `RESPONSE_STREAM` is a phase-2-followup if response sizes warrant it.

### 5.2 `Waker__Handler` — the state machine

```python
class Waker__Handler(Type_Safe):
    slug_from_host   : Slug__From_Host
    routing_lookup   : Slug__Routing__Lookup
    endpoint_resolver: Endpoint__Resolver           # __EC2 in phase 2c, __Fargate in phase 3
    proxy            : Endpoint__Proxy
    warming_page     : Warming__Page
    route53          : Route53__AWS__Client          # for cold→warm DNS-swap
    dns_swap_marker  : Set__Str                      # per-Lambda-instance: which slugs we already swapped this freeze cycle

    async def handle(self, request) -> Response:
        host = request.headers.get('host', '')
        slug = self.slug_from_host.parse(host)
        if not slug:
            return Response(status=404, body='Not a valid vault-publish host')

        entry = self.routing_lookup.lookup(slug)
        if entry is None:
            return Response(status=404, body=f'No vault registered for {slug!r}')

        state, endpoint_url = self.endpoint_resolver.resolve(entry)

        if state == Enum__Instance__State.STOPPED:
            self.endpoint_resolver.start(entry)
            return self.warming_page.render(slug, message='Starting…')

        if state == Enum__Instance__State.PENDING:
            return self.warming_page.render(slug, message='Booting…')

        if state == Enum__Instance__State.RUNNING and endpoint_url:
            if not self._health_probe(endpoint_url):
                return self.warming_page.render(slug, message='Containers starting…')

            # First healthy response on a cold→warm transition: re-upsert the per-slug A record
            # so DNS converges; the Lambda exits the data path within one TTL.
            if slug not in self.dns_swap_marker:
                public_ip = self._ip_from_endpoint(endpoint_url)
                self.route53.upsert_record(entry.zone_id, entry.fqdn, 'A', [public_ip], ttl=60)
                self.dns_swap_marker.add(slug)

            return await self.proxy.proxy(request, endpoint_url)

        return Response(status=503, body='Unknown state')
```

`dns_swap_marker` is per-Lambda-container memory (lasts until the container is frozen / recycled). For repeated cold-starts the marker resets — re-upserting an unchanged value is a no-op at the Route 53 API level, so safe.

### 5.3 The `Endpoint__Resolver` interface

```python
class Endpoint__Resolver(Type_Safe):                                # abstract base
    def resolve(self, entry: Schema__Vault_Publish__Entry) -> tuple:
        # returns (state: Enum__Instance__State, endpoint_url: str)
        raise NotImplementedError

    def start(self, entry: Schema__Vault_Publish__Entry) -> None:
        raise NotImplementedError


class Endpoint__Resolver__EC2(Endpoint__Resolver):                  # phase 2c
    def resolve(self, entry):
        inst  = EC2_Instance(instance_id=entry.instance_id)
        state = inst.state()                                        # 'stopped' / 'pending' / 'running'
        ip    = inst.ip_address() if state == 'running' else ''
        url   = f'https://{ip}:443' if ip else ''
        return Enum__Instance__State(state), url

    def start(self, entry):
        EC2_Instance(instance_id=entry.instance_id).start()
```

`Endpoint__Resolver__Fargate` (phase 3) uses `ECS_Fargate_Task` from `osbot_aws.aws.ecs` — same shape, different lookup.

### 5.4 The proxy

```python
class Endpoint__Proxy(Type_Safe):
    pool : urllib3.PoolManager

    async def proxy(self, request, target_url) -> Response:
        # 1. forward method + headers (strip Host, X-Forwarded-*; add via Via header)
        # 2. stream body in / out (urllib3 preload_content=False, 6MB Lambda buffer ceiling enforced)
        # 3. preserve response headers (strip hop-by-hop)
        # 4. preserve status code
```

Phase 2c uses `BUFFERED` invoke-mode → response capped at 6 MB. Phase 2c-follow-up flips to `RESPONSE_STREAM` if a vault site exceeds that.

### 5.5 The warming page

Auto-refreshing HTML, ~30 lines:

```html
<!doctype html>
<html><head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="3">
  <title>Starting {slug}…</title>
  <style>... minimal centred layout ...</style>
</head><body>
  <h1>Starting {slug}…</h1>
  <p>Your vault is waking up — this usually takes about 20–60 seconds.</p>
  <p class="detail">{message}</p>
</body></html>
```

Always served with `Cache-Control: no-cache, no-store, must-revalidate` so neither CloudFront nor the browser pins it.

---

## 6. The bootstrap flow

`sg vault-publish bootstrap` is the one-time setup. Runs **once per environment** (dev / staging / prod). Idempotent — safe to re-run.

```
sg vault-publish bootstrap [--zone sg-compute.sgraph.ai] [--cert-arn arn:...]
```

Steps:

1. **Verify Route 53 hosted zone exists** — `Route53__AWS__Client.get_hosted_zone(zone)`. Fail with a clear error if not.
2. **Verify ACM wildcard cert in `us-east-1`** — `ACM__AWS__Client.find_by_domain('*.sg-compute.sgraph.ai')`. If `--cert-arn` was passed, use that. If not and not found, print instructions for manual issuance (out of scope per [`03 §4.7`](03__sg-compute-additions.md#7-things-explicitly-not-in-scope-of-these-additions)).
3. **Build the Waker Lambda** — `Lambda__Deployer.deploy(`
       `name='sg-vault-publish-waker',`
       `code_path='sg_compute_specs/vault_publish/waker/',`
       `handler='lambda_entry.handler',`
       `add_osbot_aws=True,`
       `add_osbot_utils=True,`
       `env={'SG_AWS__DNS__DEFAULT_ZONE': zone, ...})`.
4. **Create the Function URL** — `Lambda.function_url_create_with_public_access()`; auth=NONE (CloudFront is the only intended caller; the Function URL itself is on a `*.lambda-url.<region>.on.aws` host that nobody else has the URL for).
5. **Create the CloudFront distribution** — `CloudFront__AWS__Client.create_distribution(...)` with:
   - `Aliases = ['*.sg-compute.sgraph.ai']`
   - `ViewerCertificate.ACMCertificateArn = cert_arn`
   - `Origins = [{primary: Lambda Function URL, OriginProtocolPolicy: https-only, ConnectionTimeout: 5}]`
   - `DefaultCacheBehavior = {ForwardedValues.Headers = ['Host'], MinTTL=0, DefaultTTL=0, MaxTTL=0}` (no cache)
6. **Wait for CloudFront Deployed** — `wait_for_deployed(distribution_id)` (~15 min — print a banner).
7. **Upsert the wildcard ALIAS** — `Route53__AWS__Client.upsert_a_alias_record(zone, '*.sg-compute.sgraph.ai', cf_domain, cf_zone_id)`. Now any non-specific subdomain falls through to CloudFront.
8. **Verify** — `Route53__Smart_Verify.verify_after_mutation(...)` confirms authoritative-pass.
9. **Pin the IDs** — write to local config (`.sg/vault-publish-bootstrap.json` or similar) and as SSM params `/sg-compute/vault-publish/bootstrap/{distribution-id,lambda-name,zone,cert-arn}`.

Returns `Schema__Vault_Publish__Bootstrap__Response` with every id.

After bootstrap, `register / unpublish / status / list` all run without further AWS-side changes.

---

## 7. CLI surface

```
sg vault-publish   (alias: sg vp)
├── bootstrap                                    one-time setup; idempotent
├── register <slug> --vault-key <key>            register + create + auto-DNS + return URL
│                  [--owner <id>]
│                  [--max-hours 1.0]
│                  [--region eu-west-2]
├── unpublish <slug>                             terminate EC2 + delete A record + delete registry
├── status <slug>                                registry + vault-app info + DNS check
├── list                                         all registered slugs (vault keys redacted)
└── waker                                        sub-group for Waker management
      info                                       what Lambda is deployed, function URL, CF id
      logs [--tail 200] [--follow]                Waker invocation logs (CloudWatch Logs tail)
      invoke --slug <slug>                       local invoke against a slug (for testing)
```

`bootstrap` / `register` / `unpublish` are mutation-gated by `SG_VAULT_PUBLISH__ALLOW_MUTATIONS=1`.

---

## 8. Tests

In-memory composition throughout. No mocks. The pattern mirrors `vault_app/tests/`:

| Test | In-memory dependency |
|------|----------------------|
| `Slug__Validator` | none (pure) |
| `Slug__Registry` | `Parameter__In_Memory` (subclass of `osbot_aws.Parameter`, dict-backed) |
| `Vault_Publish__Service` | `Slug__Registry` in-memory + `Vault_App__Service` with in-memory `Vault_App__AWS__Client` + in-memory Route53 client |
| `Endpoint__Resolver__EC2` | in-memory `EC2_Instance` subclass |
| `Endpoint__Proxy` | tiny test HTTP server (built into the test) |
| `Waker__Handler` | all of the above wired together; covers every state |
| `Cli__Vault_Publish` | golden-file CLI snapshot tests (matches `Cli__Vault_App` pattern) |

All gated on `SG_VAULT_PUBLISH__ALLOW_MUTATIONS=1` for any test that exercises the mutation paths against in-memory AWS clients.

---

## 9. Manifest

`sg_compute_specs/vault_publish/manifest.py`:

```python
from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry import Schema__Spec__Manifest__Entry

MANIFEST = Schema__Spec__Manifest__Entry(
    spec_id      = 'vault-publish',
    display_name = 'Vault Publish',
    description  = 'Publish a vault as a website at <slug>.sg-compute.sgraph.ai with on-demand wake.',
    stability    = 'experimental',                # graduates to 'stable' after phase 2
    capabilities = ['subdomain-routing', 'on-demand-compute', 'tls-wildcard'],
)
```

Manifest registers the spec with the catalogue — appears in `sg catalog list`.
