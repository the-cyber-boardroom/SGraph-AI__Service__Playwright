# Reality — SP CLI Linux/Docker/Elastic Routes + Catalog + Admin/User UI — Slice 13

**Added:** 2026-04-29  
**Branch:** `claude/setup-dev-agent-ui-titBw`  
**Dev pack:** `library/dev_packs/v0.1.101__mvp-of-admin-and-user-ui`

---

## What exists after this slice

### PR-1 — Linux + Docker routes mounted on `Fast_API__SP__CLI`

`Routes__Linux__Stack` and `Routes__Docker__Stack` were already implemented
but were not mounted. They are now wired in.

| Method | Path | Handler |
|--------|------|---------|
| GET    | `/linux/stacks`              | `Routes__Linux__Stack.list_stacks`  |
| GET    | `/linux/stack/{name}`        | `Routes__Linux__Stack.info`         |
| POST   | `/linux/stack`               | `Routes__Linux__Stack.create`       |
| DELETE | `/linux/stack/{name}`        | `Routes__Linux__Stack.delete`       |
| GET    | `/linux/stack/{name}/health` | `Routes__Linux__Stack.health`       |
| GET    | `/docker/stacks`             | `Routes__Docker__Stack.list_stacks` |
| GET    | `/docker/stack/{name}`       | `Routes__Docker__Stack.info`        |
| POST   | `/docker/stack`              | `Routes__Docker__Stack.create`      |
| DELETE | `/docker/stack/{name}`       | `Routes__Docker__Stack.delete`      |
| GET    | `/docker/stack/{name}/health`| `Routes__Docker__Stack.health`      |

**Schema fix:** `extra_ports: List__Port` changed to `List[int]` in both
`Schema__Linux__Create__Request` and `Schema__Docker__Create__Request` —
`Type_Safe__List` subclasses are not handled by `Type_Safe__To__BaseModel`,
so `List[int]` is required for FastAPI startup.

---

### PR-2 — `catalog/` sub-package + `Routes__Stack__Catalog`

New package: `sgraph_ai_service_playwright__cli/catalog/`

**Enums:**
- `Enum__Stack__Type` — `LINUX`, `DOCKER`, `ELASTIC`, `OPENSEARCH`, `VNC`

**Schemas:**
- `Schema__Stack__Type__Catalog__Entry` — one type's metadata (display_name,
  description, available flag, endpoint paths, boot estimate)
- `Schema__Stack__Type__Catalog` — response for `GET /catalog/types`
- `Schema__Stack__Summary` — type-agnostic view of one running stack
- `Schema__Stack__Summary__List` — response for `GET /catalog/stacks`

**Collections:**
- `List__Schema__Stack__Type__Catalog__Entry`
- `List__Schema__Stack__Summary`

**Service:**
- `Stack__Catalog__Service__Entries` — mixin; builds the 5 catalog entries
- `Stack__Catalog__Service` — composes `Linux__Service`, `Docker__Service`,
  `Elastic__Service`; provides `get_catalog()` + `list_all_stacks(type_filter)`

**Routes:**
- `Routes__Stack__Catalog` — tag `catalog`

| Method | Path | Notes |
|--------|------|-------|
| GET | `/catalog/types`       | Returns all 5 types; linux/docker/elastic `available=True`; opensearch/vnc `available=False` |
| GET | `/catalog/stacks`      | Cross-section list; optional `?type=linux\|docker\|elastic` filter; 422 on unknown type |

---

### PR-3 — `Routes__Elastic__Stack`

New folder: `sgraph_ai_service_playwright__cli/elastic/fast_api/routes/`

| Method | Path | Handler |
|--------|------|---------|
| GET    | `/elastic/stacks`              | `Routes__Elastic__Stack.list_stacks` |
| GET    | `/elastic/stack/{name}`        | `Routes__Elastic__Stack.info` (404 on miss) |
| POST   | `/elastic/stack`               | `Routes__Elastic__Stack.create` |
| DELETE | `/elastic/stack/{name}`        | `Routes__Elastic__Stack.delete` (404 on miss: empty `target` field) |
| GET    | `/elastic/stack/{name}/health` | `Routes__Elastic__Stack.health` |

**Service method notes (verified against `Elastic__Service.py`):**
- `create(body)` — not `create_stack`
- `get_stack_info(stack_name, region)` — name-first (opposite of linux/docker)
- `delete_stack(stack_name, region)` — name-first
- `health(stack_name, password, check_ssm)` — no `region` param

---

### Static UI — `sgraph_ai_service_playwright__api_site/`

**New shared utilities:**
- `shared/tokens.css` — CSS custom properties (colours, spacing, typography)
- `shared/api-client.js` — module singleton `ApiClient`; reads/writes
  `sg_api_url` + `sg_api_key` from localStorage; 401 → `sg-auth-required` event
- `shared/catalog.js` — page-lifetime cache of `/catalog/types`
- `shared/poll.js` — health-poll loop; 3-phase back-off (3s/5s/10s);
  visibility-pause; timeout + stopOn support

**New Web Components (`shared/components/`):**
- `sg-api-client.js` — no-render; listens for `sg-auth-required`, opens auth panel
- `sg-auth-panel.js` — connection drawer; API URL + key inputs; shadow DOM
- `sg-header.js` — top bar with title slot + ⚙ settings button
- `sg-toast-host.js` — listens for `sg-toast` event; renders transient toasts
- `sg-stack-card.js` — one stack; compact / detail modes; stop button
- `sg-stack-grid.js` — 4 render modes: `admin-table`, `type-cards`,
  `user-cards`, `user-active`
- `sg-create-modal.js` — 3-state modal: form → progress → ready

**New admin UI (`admin/`):**
- `admin/index.html` — dashboard shell; type-card strip + active-stacks table
- `admin/admin.js` — page controller; polls `/catalog/stacks` every 30s
- `admin/admin.css`

**New user UI (`user/`):**
- `user/index.html` — provisioning shell; available-type cards + active stacks
- `user/user.js` — page controller; polls active stacks every 15s
- `user/user.css`

**Updated root:**
- `index.html` — now a landing page with [Admin Dashboard] / [Provision] nav links

**Local dev script:**
- `scripts/ui__serve-locally.sh` — serves `api_site/` via `python3 -m http.server`
  on port 8090. Pair with `scripts/sp-cli__run-locally.sh` (port 10071).

---

## `Fast_API__SP__CLI` — updated route surface

Routes now mounted (in order):

| Service attr | Route class | Prefix |
|---|---|---|
| `ec2_service`         | `Routes__Ec2__Playwright`  | `/ec2/playwright/` |
| `observability_service` | `Routes__Observability`  | `/observability/`  |
| `linux_service`       | `Routes__Linux__Stack`     | `/linux/`          |
| `docker_service`      | `Routes__Docker__Stack`    | `/docker/`         |
| `catalog_service`     | `Routes__Stack__Catalog`   | `/catalog/`        |
| `elastic_service`     | `Routes__Elastic__Stack`   | `/elastic/`        |

**Total routes: 27** (was 10 after PR-0; +10 linux/docker in PR-1; +2 catalog in PR-2; +5 elastic in PR-3).

---

## Tests added

| Suite | New tests | Approach |
|-------|-----------|----------|
| `test_Fast_API__SP__CLI.py` | +4 mounting tests (linux, docker, catalog, elastic) | Path-set membership |
| `catalog/schemas/test_catalog_schemas.py` | schema round-trips | Type_Safe `.json()` |
| `catalog/service/test_Stack__Catalog__Service.py` | 4 service tests | `_Fake_*` real subclasses |
| `catalog/service/test_Stack__Catalog__Service__list.py` | 4 list tests | same |
| `catalog/fast_api/routes/test_Routes__Stack__Catalog.py` | 5 route tests | TestClient |
| `elastic/fast_api/routes/test_Routes__Elastic__Stack.py` | 5 list/info tests | TestClient + `_Fake_Elastic__Service` |
| `elastic/fast_api/routes/test_Routes__Elastic__Stack__write.py` | 5 create/delete/health tests | same |

**Total suite: 1176 passing** (1 pre-existing botocore failure unrelated to this slice).

---

## Not included in this slice (PROPOSED — does not exist yet)

- `Routes__OpenSearch__Stack` is **not** mounted on `Fast_API__SP__CLI`
  (route class exists; mounting is a one-line follow-up PR)
- VNC stack routes — depends on `sp vnc` slice
- Full TestClient coverage for linux/docker routes (mounting tests only)
- Auth beyond `X-API-Key` (no OAuth, no per-user identity)
