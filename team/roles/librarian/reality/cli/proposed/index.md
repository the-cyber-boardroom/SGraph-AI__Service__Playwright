# cli — Proposed

PROPOSED — does not exist yet. Items below extend the `sp` / `sg` CLI and `Fast_API__SP__CLI` surfaces but are not in code today.

Last updated: 2026-05-17 | Domain: `cli/`
Sources: `_archive/v0.1.31/09__sp-cli-observability-routes.md` (gaps), `_archive/v0.1.31/13__sp-cli-linux-docker-elastic-catalog-ui.md` (not-included), `_archive/v0.1.31/16__sg-aws-dns-and-acm.md` (known gaps).

---

## P-1 · `POST /v1/observability/stack` (create)

**What:** Mutation path for creating an observability stack via HTTP. Today only list / get / delete are wired.

**Source:** `09__sp-cli-observability-routes.md` — brief v0.1.72 promise unsatisfied.

## P-2 · `POST /v1/observability/stack/{name}/backup`

**Source:** `09__sp-cli-observability-routes.md`.

## P-3 · `POST /v1/observability/stack/{name}/restore`

**Source:** `09__sp-cli-observability-routes.md`.

## P-4 · `POST /v1/observability/stack/{name}/dashboard-import`

**Source:** `09__sp-cli-observability-routes.md`.

## P-5 · `/v1/` path prefix on observability routes

**What:** The v0.1.72 brief uses `/v1/observability/...`; Lambda mounts at `/observability/...`. Add `/v1/` via API-GW stage path or a `prefix` attribute on the `Fast_API__Routes` subclass.

**Source:** `09__sp-cli-observability-routes.md`.

## P-6 · `Routes__OpenSearch__Stack` mount on `Fast_API__SP__CLI`

**What:** The route class exists; the one-line mount in `setup_routes()` is the only follow-up needed.

**Source:** `13__sp-cli-linux-docker-elastic-catalog-ui.md` (slice 13 not-included).

## P-7 · `Routes__Prometheus__Stack` mount on `Fast_API__SP__CLI`

**What:** Same as P-6 — class exists, mount needed.

**Source:** `13__...md` (slice 13/14 not-included).

## P-8 · `Enum__Stack__Type.PROMETHEUS`

**What:** The catalog enum does not include `PROMETHEUS` yet, blocking surfaces that derive from `Enum__Stack__Type`.

**Source:** `14__sp-cli-ui-sg-layout-vnc-wiring.md` not-included list.

## P-9 · Catalog `region` filtering through to per-service `list_stacks`

**What:** `/catalog/stacks?region=…` only forwards `region` to VNC/Linux/Docker; Elastic uses its own `resolve_region`. Make the behaviour uniform.

**Source:** `14__...md` not-included list.

## P-10 · Auth beyond `X-API-Key`

**What:** No OAuth, no per-user identity, no RBAC. Cross-references host-control P-2 and playwright-service P-11.

**Source:** `13__...md` and `14__...md` not-included lists.

## P-11 · Full Type_Safe port of `provision_ec2.py`

**What:** `Ec2__Service` is an adapter — converts dict returns from `scripts/provision_ec2.py` into Type_Safe schemas. Full port still pending; when it lands, only the method bodies change.

**Source:** `07__sp-cli-ec2-fastapi.md` tech-debt note 1.

## P-12 · Live deploy-via-pytest for `sp-playwright-cli` Lambda

**What:** Numbered tests (`test_1__ensure_role`, `test_2__build_push_image`, …) mirroring `tests/deploy/` — provides real-AWS confidence beyond the unit tests.

**Source:** `08__sp-cli-lambda-deploy.md` known-gap 1.

## P-13 · `acm list --all-regions`

**What:** Currently stubbed `"not implemented in P0"`.

**Source:** `16__sg-aws-dns-and-acm.md` known-gaps.

## P-14 · `acm request` / `acm delete`

**What:** ACM mutations — not in scope for P0/P1; the §12 ADDENDUM cert workflow needs these.

**Source:** `16__...md` known-gaps.

## P-15 · `sg playwright vault re-cert --hostname <fqdn>`

**What:** The cert-warning info block printed by `records add` points users at this command, which does not exist. **Q9 still PENDING** (DNS-01 vs HTTP-01 for the cert sidecar). Highest-value remaining work from the DNS slice.

**Source:** `16__...md` known-gaps (§12 ADDENDUM).

## P-16 · CloudFront support in the bigger CF+R53 brief

**What:** Main P2 deliverable of the bigger DNS plan. Partially landed in v0.2.23 (`sg aws cf` distribution CRUD — see [`sg-compute/index.md`](../sg-compute/index.md)), but the full DNS + CF integration is still pending.

**Source:** `16__...md` known-gaps.

## P-17 · Reverse DNS lookup

**What:** "Which records does instance `i-...` own?" — not in scope for the P0 DNS slice.

**Source:** `16__...md` known-gaps.

## P-18 · Other observability mutation ops (Tier-1 service)

**What:** `create`, `backup`, `restore`, `dashboard-import`, `data-export`, `data-import` — currently scripts-only or absent. The Type_Safe service layer ships only the read + delete paths.

**Source:** `06__sp-cli-duality-refactor.md` "What does NOT exist yet".

## P-19 · GH Actions workflows for `obs-morning.yml` / `obs-evening.yml`

**What:** Brief v0.1.72 promises scheduled GH Actions to create/delete observability stacks daily. Not written.

**Source:** `06__...md` "What does NOT exist yet".
