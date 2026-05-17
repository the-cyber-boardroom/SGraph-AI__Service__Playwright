# qa — Reality Index

**Domain:** `qa/` | **Last updated:** 2026-05-17 | **Maintained by:** Librarian
**Code-source basis:** consolidated from `_archive/v0.1.31/04__tests.md` plus per-slice test counts cited in `06..16__*.md`.

Test strategy, test inventory, deploy-via-pytest, smoke tests. Headline rule: **no mocks, no patches** — every collaborator has an `*__In_Memory` subclass or a real-process fake.

---

## EXISTS (code-verified)

### Playwright service tests

#### Unit — 395 passing at v0.1.29 freeze (unchanged into v0.1.31)

| File | What it covers |
|------|----------------|
| `tests/unit/agentic_fastapi/test_Agentic_Boot_State.py` | 7 tests — ring buffer symmetric, get-returns-copy, overflow drops oldest; last-error defaults-empty, set/get, set-None-becomes-empty, reset clears both |
| `tests/unit/agentic_fastapi/test_Agentic_Admin_API.py` | 13 tests — happy paths on all 8 admin endpoints via real `FastAPI TestClient`; `/admin/*` all reachable without an API key |
| `tests/unit/agentic_fastapi_aws/test_Agentic_Code_Loader.py` | resolve → local / s3 / passthrough |
| `tests/unit/agentic_fastapi_aws/test_Agentic_Boot_Shim.py` | 10 tests — `read_image_version` file / missing; boot happy path + env-var writes; error-pinned inside Lambda; re-raise outside; 3 boot-state-writes gap tests |
| Older folders | Unchanged from v0.1.24 |

#### Unit — EC2 spike (v0.1.31)

- `tests/unit/scripts/test_provision_ec2.py` — 19 tests. Module surface; constants (t3.large, AL2023 pattern, `:8000`, SG name); user-data rendering (docker install, ECR login, run command, API-key env, 120 s watchdog); `--terminate` short-circuit; argparse safety (terminate off by default).

#### Integration + deploy — unchanged from v0.1.24

Deploy-via-pytest tests still point at the 10 public endpoints; smoke tests don't yet assert `/admin/*`.

---

### agent_mitmproxy tests (v0.1.32)

#### Unit — 34 passing + 1 skipped

| File | What it covers |
|------|----------------|
| `tests/unit/agent_mitmproxy/test_package.py` | 4 tests — `path` attribute, version file presence, `version__agent_mitmproxy` matches file contents |
| `tests/unit/agent_mitmproxy/test_default_interceptor.py` | request-id shape (12-char hex), ts stamp, elapsed-ms calculation, response header round-trip |
| `tests/unit/agent_mitmproxy/test_audit_log_addon.py` | NDJSON shape, Basic `Proxy-Authorization` decode, stdout flush |
| `tests/unit/agent_mitmproxy/test_addon_registry.py` | Registry concatenates interceptor + audit addons in expected order |
| `tests/unit/agent_mitmproxy/test_Routes__Health.py` | `/health/info` returns `Schema__Agent_Mitmproxy__Info`; `/health/status` runs CA + interceptor file checks; env-var override path |
| `tests/unit/agent_mitmproxy/test_Routes__CA.py` | `/ca/cert` returns PEM bytes + 503 when absent; `/ca/info` SHA-256 fingerprint matches `cryptography.x509` |
| `tests/unit/agent_mitmproxy/test_Routes__Config.py` | `/config/interceptor` round-trips script source via `Safe_Str__Text__Dangerous` |
| `tests/unit/agent_mitmproxy/test_Routes__Web.py` | Real `http.server.HTTPServer` on a free port; asserts the UI reverse-proxy strips `X-API-Key` + hop-by-hop headers |
| `tests/unit/agent_mitmproxy/test_Docker__Agent_Mitmproxy__Base.py` | `IMAGE_NAME` constant; `agent_mitmproxy.path` is a dir; dockerfile exists. One test gated `@skipUnless(osbot_docker available)` |

#### Unit — EC2 spin-up (v0.1.32, pre-unification)

- `tests/unit/scripts/test_provision_mitmproxy_ec2.py` — 5 tests. Module surface; constants (t3.small, `:8080` + `:8000`, SG name, role name); user-data rendering; `--terminate` short-circuit; argparse safety.

> **Post-v0.1.31 note:** BV2.12 (2026-05-05) deleted `tests/unit/agent_mitmproxy/` (12 files) along with the source package. **VERIFY** before quoting current counts.

---

### CLI / FastAPI / sister-section tests (per-slice counts at v0.1.31 freeze)

| Slice | Tests added | Suite total at the introducing commit |
|-------|------------:|--------------------------------------:|
| Slice 3 (EC2 routes) | 10 TestClient cases + adapter helpers (34 across the new package) | 34 (new package) |
| Slice 6 (duality refactor — Stack__Naming, Image__Build, Ec2__AWS__Client) | 9 + 15 + 24 | (cumulative) |
| Slice 6 (`sp os` Phase B5) | 131 | |
| Slice 6 (`sp prom` Phase B6) | 170 | |
| Slice 6 (`sp vnc` Phase B7) | 189 | |
| Slice 9 (observability routes) | 5 + 5 | 62 (cumulative on `Fast_API__SP__CLI`) |
| Slice 13 (linux/docker/catalog/elastic mounts) | 4 + several catalog/elastic suites | **1176 total suite** |
| Slice 14 (VNC mount) | +2 mounting tests | (incremental) |
| Slice 16 (`sg aws dns` + `sg aws acm`) | 136 | (cumulative) |
| LETS slice 1 (inventory) | 150 | |
| LETS slice 2 (events) | 201 | 531 total elastic |
| LETS slice 3 (consolidate) | ~57 | **499 passed** at the consolidate commit |

---

### Host-control tests

| File | Test count |
|------|-----------|
| `tests/unit/sgraph_ai_service_playwright__host/containers/test_Container__Runtime__Docker.py` | (subset of 31) |
| `tests/unit/sgraph_ai_service_playwright__host/shell/test_Shell__Executor.py` | (subset of 31) |
| `tests/unit/sgraph_ai_service_playwright__host/fast_api/test_Fast_API__Host__Control.py` | (subset of 31) — 9 FastAPI integration tests skip when `osbot_fast_api_serverless` is absent |

Total host-control test functions: **31** (per [`host-control/index.md`](../host-control/index.md)). Full suite at that commit: **1653 unit tests pass**.

---

### No-mocks policy (CLAUDE.md §Testing)

All tests follow:

- **No `mock`, no `patch`.** Route tests use `FastAPI TestClient`; addon tests use `SimpleNamespace` fakes that duck-type mitmproxy flow/request/response (no mitmproxy import needed in test process); the UI reverse-proxy test stands up a real `http.server.HTTPServer` on a free port.
- **Real subclasses for AWS/HTTP boundaries** — every `*__AWS__Client` has an `*__AWS__Client__In_Memory` subclass; every `*__HTTP__Client` has an `*__HTTP__Client__In_Memory`. Tests pass these in via constructor or factory seam.
- **In-memory stack composition** — `register_playwright_service__in_memory()` for test composition (no separate process required).
- **Real Chromium for integration** — gate on `SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE`; skip cleanly when absent.
- **Deploy-via-pytest** — numbered tests (`test_1__create_lambda`, `test_2__invoke__health_info`, …) run top-down.

Full guidance: `library/guides/v3.1.1__testing_guidance.md`.

---

### Snapshot / structural tests (post-v0.1.31)

| File | Assertions |
|------|-----------|
| `tests/ci/test_sg_compute_spec_detail__snapshot.py` | 13 |
| `tests/ci/test_sg_compute_ami_picker__snapshot.py` | 17 |

These pin the structural shape of dashboard components after the T3.3b rename — see [`sg-compute/index.md`](../sg-compute/index.md).

---

## PROPOSED — does not exist yet

See [`proposed/index.md`](proposed/index.md).

---

## See also

- Source: [`_archive/v0.1.31/04__tests.md`](../_archive/v0.1.31/04__tests.md)
- Testing guidance: `library/guides/v3.1.1__testing_guidance.md`
- Infra (image build tests, deploy-via-pytest harness): [`infra/index.md`](../infra/index.md)
- Per-domain test inventories are also embedded in each domain's `index.md`
