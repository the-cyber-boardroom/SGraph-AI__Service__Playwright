# 07 — Testing Patterns

→ [Catalogue README](README.md)

Full testing guide: `library/guides/v3.1.1__testing_guidance.md`

---

## The No-Mocks Rule

**Never use `mock`, `patch`, `MagicMock`, or any monkey-patching.**

Instead: every AWS- or HTTP-touching class has a real `*__In_Memory` subclass that overrides
the I/O methods with in-memory state. Tests instantiate the In_Memory variant directly.

---

## How to Achieve No-Mocks

| Real class | In_Memory substitute | Pattern |
|------------|---------------------|---------|
| `S3__Inventory__Lister` | `S3__Inventory__Lister__In_Memory` | Canned `{prefix: [records]}` dict |
| `Inventory__HTTP__Client` | `Inventory__HTTP__Client__In_Memory` | In-memory ES doc store |
| `S3__Object__Fetcher` | `S3__Object__Fetcher__In_Memory` | Canned `{(bucket, key): bytes}` map |
| `Inventory__Manifest__Reader` | `Inventory__Manifest__Reader__In_Memory` | Canned unprocessed doc list |
| `Inventory__Manifest__Updater` | `Inventory__Manifest__Updater__In_Memory` | Records mark/reset calls |
| `Elastic__AWS__Client` | `Elastic__AWS__Client__In_Memory` | Fake EC2 state |
| `Kibana__Saved_Objects__Client` | `Kibana__Saved_Objects__Client__In_Memory` | In-memory saved objects |
| `Ec2__AWS__Client` | `_Fake_EC2` (`_Fake_Boto3_Client`) | Real subclass, no daemon |
| `Observability__AWS__Client` | `Observability__AWS__Client__In_Memory` | Fixture listings + delete outcomes |
| Docker client | In-memory fake docker client | Overrides `build()` |

Chromium tests are gated on `SG_PLAYWRIGHT__CHROMIUM_EXECUTABLE` env var; skip cleanly when absent.

---

## Deterministic Helpers

| Helper | Purpose |
|--------|---------|
| `Deterministic__Run__Id__Generator` | Produces predictable run IDs for test assertions |
| `Fake__Response` | Canned `requests.Response`-shaped object for HTTP client regression tests |
| `_Recording_HTTP_Client` | Subclasses `Inventory__HTTP__Client__In_Memory` + records `request()` calls |

---

## Test Folder Structure

```
tests/
    unit/                        ← mirrors source tree
        agent_mitmproxy/
        agentic_fastapi/
        agentic_fastapi_aws/
        boot/
        dispatcher/
        docker/
        fast_api/routes/
        schemas/
        scripts/
        service/
        sgraph_ai_service_playwright__cli/
            aws/
            deploy/
            ec2/service/
            elastic/
                lets/cf/
                    inventory/   ← 150 tests
                    events/      ← 201 tests
                    consolidate/ ← ~57 tests
                    sg_send/
                lets/runs/
                service/         ← 165 tests
            fast_api/
            image/
            observability/
            opensearch/
            prometheus/
    deploy/                      ← deploy-via-pytest (numbered, run top-down)
    docker/                      ← Docker build + ECR push tests
    integration/                 ← real Chromium (gated on env var)
    local/                       ← local-only tests
```

---

## Current Test Count (approximate)

| Area | Count |
|------|-------|
| Playwright service (unit) | 395 |
| agent_mitmproxy (unit) | 34 passing + 1 skipped |
| EC2 spike (unit) | 19 |
| SP CLI — aws, deploy, ec2, image, observability (unit) | ~100 |
| SP CLI — opensearch (unit) | 131 |
| SP CLI — prometheus (unit) | 19 |
| SP CLI — elastic service (unit) | 165 |
| SP CLI — LETS inventory (unit) | 150 |
| SP CLI — LETS events (unit) | 201 |
| SP CLI — LETS consolidate (unit) | ~57 |
| **Full suite total** | **~499 passing** |

---

## Writing a New Test

1. Create `*__In_Memory` test double if the class has an I/O seam.
2. Override the I/O method (e.g. `request()`, `s3()`, `ec2()`) in the subclass.
3. Inject the In_Memory instance via the service's constructor field.
4. Assert on schemas and contract data, not implementation details.
5. Gate Chromium tests with `@pytest.mark.skipif(not os.getenv(...), reason=...)`.

---

## Deploy-via-Pytest

Deploy tests in `tests/deploy/` are numbered and run top-down:

```python
test_1__create_lambda
test_2__invoke__health_info
test_3__...
```

They verify the live Lambda after deployment. Running them out-of-order is not supported.

---

## Cross-Links

- `library/guides/v3.1.1__testing_guidance.md` — full testing guide
- `team/roles/librarian/reality/v0.1.31/04__tests.md` — canonical test inventory
