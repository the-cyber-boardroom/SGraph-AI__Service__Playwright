---
title: "Catalogue — Tests"
file: tests.md
shard: tests
as_of: v0.2.25
last_refreshed: 2026-05-17
maintainer: Librarian
prior_snapshot: (none — first snapshot)
---

# Catalogue — Tests

Three test trees, all under the no-mocks rule. Tests assert on contracts (schemas, status codes, persisted artefacts), not implementation details.

- **`tests/`** — legacy SP CLI + Playwright Lambda packaging-era tests. 286 `test_*.py` files (~275 under `tests/unit/`, 4 under `tests/ci/`, 3 under `tests/integration/`, 4 under `tests/local/`).
- **`sg_compute__tests/`** — `sg_compute/` package tests. 67 `test_*.py` files. Mirrors `sg_compute/` layout (`primitives/`, `core/{spec,node,pod,stack}/`, `platforms/ec2/`, `host_plane/`, `control_plane/`, `vault/`, `cli/{base,…}`, `helpers/`, `stacks/`, `fast_api/`).
- **`sg_compute_specs/{spec}/tests/`** — per-spec test suites co-located with each spec. 79 `test_*.py` files across 15 specs.

> Authoritative testing guide: [`library/guides/v3.1.1__testing_guidance.md`](../guides/v3.1.1__testing_guidance.md) (1,285 lines).

---

## Test File Counts (2026-05-17)

| Tree | Count |
|------|------:|
| `tests/unit/` | 275 |
| `tests/ci/` | 4 |
| `tests/integration/` | 3 |
| `tests/local/` | 4 |
| `tests/` total | 286 |
| `sg_compute__tests/` | 67 |
| `sg_compute_specs/{spec}/tests/` (15 specs) | 79 |
| **Grand total `test_*.py` files** | **432** |

### Per-spec test file counts

| Spec | Files |
|------|------:|
| `docker` | 5 |
| `elastic` | 4 |
| `firefox` | 6 |
| `local_claude` | 4 |
| `mitmproxy` | 12 |
| `neko` | 4 |
| `ollama` | 5 |
| `open_design` | 1 |
| `opensearch` | 4 |
| `playwright` | 5 |
| `podman` | 4 |
| `prometheus` | 4 |
| `vault_app` | 8 |
| `vault_publish` | 8 |
| `vnc` | 5 |

> Earlier reality notes record per-area test-function counts in the hundreds; the file-count above is the conservative number you can derive without running pytest collection.

---

## Test Tree Layouts

### `tests/` (legacy + cross-cutting)

```
tests/
    unit/                         ← mirrors source tree
        agentic_fastapi/
        api_site/
        dispatcher/
        docker/                   ← Docker build + ECR push tests
        fast_api/routes/
        schemas/
        scripts/
        service/
        sgraph_ai_service_playwright__cli/
            aws/                  ← dns, acm, billing, cf, lambda
            catalog/
            core/
            docker/
            ec2/
            elastic/
            fast_api/
            firefox/
            image/
            neko/
            observability/
            opensearch/
            prometheus/
            vault/
            vnc/
    ci/                           ← runs in CI only (4 files)
    integration/                  ← real Chromium (gated on env var, 3 files)
    local/                        ← local-only (4 files)
```

### `sg_compute__tests/` (sg_compute SDK)

```
sg_compute__tests/
    cli/{base/, …}
    control_plane/
    core/{node,pod,spec,stack}/{schemas/, …}
    fast_api/{tls/, …}
    helpers/{aws,health,networking,user_data}/
    host_plane/{fast_api,images,pods,shell}/
    platforms/{ec2/{secrets,user_data},tls}/
    primitives/
    stacks/{ollama,open_design,podman,vnc}/
    vault/{api/routes/, service/}
```

### `sg_compute_specs/{spec}/tests/`

Each spec's tests mirror the spec's own internal layout (e.g. `sg_compute_specs/playwright/tests/` mirrors `sg_compute_specs/playwright/{core/,service/}`).

---

## The No-Mocks Rule

**Never use `mock`, `patch`, `MagicMock`, or any monkey-patching.** Every AWS- or HTTP-touching class has a real `*__In_Memory` subclass that overrides I/O methods with in-memory state. Tests instantiate the In_Memory variant directly. There are 15 `*__In_Memory.py` files in the repo today.

Representative pairs:

| Real class | In_Memory substitute |
|------------|---------------------|
| `S3__Inventory__Lister` | `S3__Inventory__Lister__In_Memory` |
| `Inventory__HTTP__Client` | `Inventory__HTTP__Client__In_Memory` |
| `S3__Object__Fetcher` | `S3__Object__Fetcher__In_Memory` |
| `Inventory__Manifest__Reader` | `Inventory__Manifest__Reader__In_Memory` |
| `Inventory__Manifest__Updater` | `Inventory__Manifest__Updater__In_Memory` |
| `Elastic__AWS__Client` | `Elastic__AWS__Client__In_Memory` |
| `Kibana__Saved_Objects__Client` | `Kibana__Saved_Objects__Client__In_Memory` |
| `Ec2__AWS__Client` | `_Fake_EC2` (`_Fake_Boto3_Client`) |
| `Observability__AWS__Client` | `Observability__AWS__Client__In_Memory` |

For the Playwright service itself, composition is via `register_playwright_service__in_memory()` (or equivalent — VERIFY: confirm the helper name post-BV2.11, since the service moved into `sg_compute_specs/playwright/`).

---

## Chromium-Gated Integration Tests

`tests/integration/` (3 files; primarily under `tests/integration/service/`) drives a real Chromium. Gated on `SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE` — tests skip cleanly when the env var is absent so the suite passes on machines without a Chromium install.

```python
@pytest.mark.skipif(
    not os.getenv('SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE'),
    reason='Chromium not installed',
)
```

---

## Deploy-via-Pytest Pattern

Deploy tests are numbered and run **top-down** as a single sequence. They verify a live deployment from the outside, calling the real Lambda (historical) or live container (current). Run order is meaningful — `test_2__…` depends on `test_1__…` having created the resource.

```python
test_1__create_lambda          # historical — Lambda packaging retired v0.2.11
test_2__invoke__health_info
test_3__…
```

> The Lambda-deploy variants are largely retired in favour of Docker-Hub-image runs. The pattern survives for the host-control image and the vault-publish Waker Lambda.

---

## Writing a New Test

1. If the class has an I/O seam, create a `*__In_Memory` subclass and override the I/O method (e.g. `request()`, `s3()`, `ec2()`).
2. Inject the In_Memory instance via the service's constructor field.
3. Assert on schemas and contract data, not implementation details.
4. Gate Chromium tests with `@pytest.mark.skipif(not os.getenv(...), reason=...)`.
5. Co-locate spec tests under `sg_compute_specs/{spec}/tests/`; cross-cutting tests under `sg_compute__tests/` or `tests/unit/`.

---

## Cross-Links

- Authoritative testing guide: [`library/guides/v3.1.1__testing_guidance.md`](../guides/v3.1.1__testing_guidance.md)
- QA reality: pending migration — currently [`team/roles/librarian/reality/_archive/v0.1.31/04__tests.md`](../../team/roles/librarian/reality/_archive/v0.1.31/04__tests.md)
- Test-helpers in `sg_compute__tests/helpers/{aws,health,networking,user_data}/`
- CI workflows: [`infra.md`](infra.md)
