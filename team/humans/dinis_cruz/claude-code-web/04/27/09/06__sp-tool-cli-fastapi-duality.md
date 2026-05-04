# 06 — The `sp` Tool: CLI ↔ FastAPI Duality and the Refactoring in Progress

Understanding this doc is important context for the LETS planning session —
the new `sg-send` commands must follow the same architectural pattern being
applied across the whole CLI.

---

## What `sp` is

`sp` is a Typer CLI entrypoint (installed from the repo via `pyproject.toml`)
with a tree of sub-commands organised by section:

```
sp el ...       # Ephemeral Elasticsearch + Kibana (sp elastic)
sp el lets cf ...   # LETS pipeline on CloudFront logs (the subject of this brief)
sp ob ...       # Observability stack (OpenSearch + AMP + Grafana)
sp os ...       # sp os — OpenSearch sister section (Phase B, in progress)
```

Scripts live in `scripts/` (`elastic.py`, `elastic_lets.py`,
`observability.py`, `provision_ec2.py`, …).  Each mounts its Typer app
onto the top-level `sp` entrypoint.

The `sp` CLI and `Fast_API__SP__CLI` (a FastAPI app) are **two entry
points into the same service classes**.

---

## The core design principle — CLI-first but API-native

The problem the design solves: every `sp` command used to embed business
logic directly inside the `typer` command function, mixed with `Console`
output.  The only way to call the logic was through the CLI.  That made:

- **Automation impossible** — scheduling `sp ob create` required shell access
  or subprocess calls from GitHub Actions.
- **Testing awkward** — tests had to invoke Typer's runner or duplicate logic.
- **API exposure** — no way to expose the same operation over HTTP without
  copy-pasting the code.

The fix is a **three-tier architecture** where every operation lives in a
pure service class that both the CLI and the FastAPI routes call:

```
┌─────────────────────────────────────────────────────────────┐
│  Tier 1 — Pure logic  (no I/O, no Console, returns schemas)  │
│                                                             │
│  Elastic__Service          elastic/service/                  │
│  Ec2__Service              ec2/service/                      │
│  Image__Build__Service     image/service/          ← NEW     │
│  OpenSearch__Service       opensearch/service/     ← IN PROG │
│  Observability__Service    observability/service/            │
└──────────┬──────────────────────────────────────────────────┘
           │ called by both ↓
    ┌──────┴──────┐          ┌──────────────────┐
    │  Tier 2A    │          │  Tier 2B          │
    │  CLI layer  │          │  FastAPI layer    │
    │  typer cmds │          │  route handlers   │
    │  Rich print │          │  return .json()   │
    └─────────────┘          └──────────────────┘
```

### Tier 1 — service class rules (non-negotiable)

- Extends `Type_Safe`.  No `Console`, no `typer`, no `sys.exit`.
- Every method returns a `Type_Safe` schema.  Never a raw dict.
- Long-running AWS waits can emit progress via an injected `on_progress`
  callback — CLI passes a Rich print function; FastAPI sets `None`.
- AWS calls are isolated in a sibling `{Section}__AWS__Client` class —
  the only place that touches boto3.

### Tier 2A — CLI rules

Every typer command body fits in ~5 lines:

```python
@app.command('create')
def cmd_create(name: str, ...):
    svc = Elastic__Service(on_progress=lambda m: c.print(m))
    result = svc.create(name, region=region or '')
    _render_create_result(result, c)          # Rich formatting only
```

No business logic in the command body.

### Tier 2B — FastAPI route rules

Every route body fits in ~3 lines:

```python
class Route__EC2__Playwright__Create(Type_Safe):
    def handle(self, body: Schema__EC2__Create__Request) -> Response:
        result = Ec2__Service().create(**body.json())
        return result.json()
```

Routes ship **in the same PR** as the CLI commands.  "API will follow
later" is what left `sp el` (Elastic+Kibana) CLI-only — that is explicitly
documented as a known gap in the v0.1.96 plan.

---

## The v0.1.96 plan — what's approved and in progress

The full plan lives at `team/comms/plans/v0.1.96__playwright-stack-split__*.md`
(8 documents).  Key points:

**Motivation:** The main Playwright EC2 bundles ~9 containers (Playwright +
mitmproxy + VNC + Prometheus + cAdvisor + node-exporter + fluent-bit +
Dockge + …).  That bundling was a PoC convenience.  It is now a liability
for production clarity, image size, and security surface.

**Locked decisions:**
1. Main Playwright EC2 → exactly **2 containers**: `playwright` + `agent-mitmproxy`
2. Three **sister sections** modeled on `sp el` (the proven template):
   - `sp os` — OpenSearch (distinct from `sp el` Elasticsearch; both kept)
   - `sp prom` — Prometheus + cAdvisor + node-exporter
   - `sp vnc` — Nginx + VNC + Mitmproxy for human browser debugging
3. API-first for every new section from day one
4. **`sp el` stays CLI-only this round** (explicit out-of-scope; noted as a follow-up)
5. Every EC2/AMI is **100% self-contained** — no external runtime dependencies
   (no S3, no vault, no Parameter Store fetches at boot).  All artefacts baked
   at AMI build time.  This unlocks reliable fast-launch and AWS Marketplace
   eligibility.

---

## What Phase A built (complete, merged to dev)

Phase A established the shared foundation all sister sections inherit:

### Step 1 — `Stack__Naming` (commit `4ee540c`)

`sgraph_ai_service_playwright__cli/aws/Stack__Naming.py`

A `Type_Safe` class with `section_prefix: str`.  Two methods:
- `aws_name_for_stack(name)` — adds `{prefix}-` if not already present
  (prevents double-prefixing like `elastic-elastic-*`)
- `sg_name_for_stack(name)` — appends `-sg` (never `sg-*` prefix — AWS
  reserves `sg-*` for SG IDs and rejects `CreateSecurityGroup` with that
  pattern)

Each section instantiates once at module level:

```python
ELASTIC_NAMING = Stack__Naming(section_prefix='elastic')
OS_NAMING      = Stack__Naming(section_prefix='opensearch')
PROM_NAMING    = Stack__Naming(section_prefix='prometheus')
VNC_NAMING     = Stack__Naming(section_prefix='vnc')
```

Single source of truth for the rules encoded in CLAUDE.md #14 and #15.

### Step 2 — `Image__Build__Service` (commit `0162e93`)

`sgraph_ai_service_playwright__cli/image/service/Image__Build__Service.py`

De-duplicated ~70% overlap between `Build__Docker__SGraph_AI__Service__Playwright`
(Playwright EC2 image) and `Docker__SP__CLI` (SP CLI Lambda image).  Both
builders now thin composers over this shared class.  Two seams:
- `stage_build_context()` — pure I/O, unit-testable
- `build()` — docker daemon call, covered by deploy-via-pytest

### Steps 3a-3f — `Ec2__AWS__Client` refactoring (commits `68a6c85` → `cde60c5`)

The EC2 boto3 boundary was spread across `provision_ec2.py`.  Moved into:
`sgraph_ai_service_playwright__cli/ec2/service/Ec2__AWS__Client.py`

Five sub-steps:
- **3a:** naming helpers + instance lookup (`find_instances`, `resolve_instance_id`, `terminate_instances`)
- **3b:** AWS context accessors (`aws_account_id`, `ecr_registry_host`, `default_playwright_image_uri`)
- **3c:** IAM helpers + constants (`ensure_instance_profile`, `decode_aws_auth_error`)
- **3d:** SG + AMI helpers (`ensure_security_group`, `latest_healthy_ami`, `create_ami`, `wait_ami_available`)
- **3f:** typer commands in `provision_ec2.py` reduced to thin wrappers
  (`cmd_list`, `cmd_info`, `cmd_delete` now ~10 lines each)

A real bug was caught during 3d: an em-dash in the SG description string
was rejected by AWS (non-ASCII in `GroupDescription`).

### Step 4 — `DELETE /ec2/playwright/delete-all` route (commit `14cdc51`)

`fast_api/routes/Routes__Ec2__Playwright.py`

The only EC2 operation that lacked a FastAPI route.  Closes the CLI ↔ API
parity gap for the EC2 section.

---

## What Phase B has started (in progress)

### Step 5a — `sp os` foundation (commit `b0f3805`)

`sgraph_ai_service_playwright__cli/opensearch/`

Established the namespace with:
- `primitives/Safe_Str__OS__Stack__Name.py`
- `enums/Enum__OS__Stack__State.py`
- `service/OpenSearch__AWS__Client.py` (skeleton with `OS_NAMING` + 6 tag constants)

**Key lesson from 5a:** The folder is `opensearch/` not `os/` — naming it
`os/` shadows Python's stdlib `os` module, causing 175 test import failures
discovered at commit time.  The Typer alias (`sp os`) is unaffected.

Steps 5b through 5i (schemas, AWS client methods, service orchestrator, HTTP
client, user-data builder, dashboard generator, FastAPI routes, CLI commands)
are **not yet started**.

---

## What the LETS commands (`sp el lets`) inherit from this

The `lets` commands live under `sp el` and therefore inherit the context of
the `sp el` (Elastic+Kibana) section:

- They use `Elastic__Service.get_stack_info()` to resolve the running stack
- They call `Inventory__HTTP__Client` (a thin wrapper over `Elastic__HTTP__Client`)
  for all Elastic/Kibana HTTP
- They follow Tier 1 purity — `Inventory__Loader`, `Events__Loader`,
  `SG_Send__Orchestrator` (planned) have no `Console`, no `typer`

**The `sp el lets` section is CLI-only today** — consistent with `sp el`
itself being CLI-only (locked decision #4 in v0.1.96).  When/if `sp el` gets
FastAPI routes, the `lets` commands can follow.

---

## Key rules summary for any new `sg-send` command

| Rule | Detail |
|------|--------|
| Service class first | Write `SG_Send__Orchestrator` before the Typer command body |
| No logic in CLI | Command body: build request schema, call service, render with Rich |
| Type_Safe returns | Orchestrator returns `Schema__SG_Send__Sync__Response`, not a dict |
| AWS boundary isolation | S3 calls go through `S3__Object__Fetcher`; Elastic calls go through `Inventory__HTTP__Client` — no new boto3 calls scattered in the orchestrator |
| No FastAPI needed yet | `sg-send` commands are CLI-only, consistent with `sp el` section today |
| One class per file | Every new schema, enum, primitive in its own file |

---

## Optional reading — the full plan series

These 8 plan documents at `team/comms/plans/` explain the full v0.1.96 intent.
They are **approved and locked** — not aspirational.

| Doc | What |
|-----|------|
| `v0.1.96__playwright-stack-split__01__overview.md` | Motivation, scope, 8 locked decisions, success criteria |
| `v0.1.96__playwright-stack-split__02__api-consolidation.md` | Three-tier architecture, rules for new sections, image build, EC2 migration |
| `v0.1.96__playwright-stack-split__03__strip-playwright-ec2.md` | Before/after compose (2-container target) |
| `v0.1.96__playwright-stack-split__04__sp-os__opensearch.md` | `sp os` folder layout, schemas, commands |
| `v0.1.96__playwright-stack-split__05__sp-prom__prometheus.md` | `sp prom` section |
| `v0.1.96__playwright-stack-split__06__sp-vnc__nginx-vnc-mitmproxy.md` | `sp vnc` section |
| `v0.1.96__playwright-stack-split__07__command-cleanup-and-migration.md` | Top-level pruning, migration order |
| `v0.1.96__playwright-stack-split__08__licensing-and-marketplace.md` | License review, marketplace eligibility |

The duality idea was first articulated in:
`team/comms/briefs/v0.1.72__sp-cli-fastapi-duality.md` — read this for the
full rationale and the GitHub Actions scheduling examples.
