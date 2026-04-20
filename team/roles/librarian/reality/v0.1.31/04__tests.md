# Tests — Reality (v0.1.31 / v0.1.32)

See [README.md](README.md) for the index and split rationale.

---

## Playwright

### Unit — 395 passing (unchanged since v0.1.29)

- `tests/unit/agentic_fastapi/test_Agentic_Boot_State.py` — 7 tests. Ring buffer symmetric, get-returns-copy, overflow drops oldest; last-error defaults-empty, set/get, set-None-becomes-empty, reset clears both.
- `tests/unit/agentic_fastapi/test_Agentic_Admin_API.py` — 13 tests. Happy paths on all 8 admin endpoints via real `FastAPI TestClient`; `/admin/*` all reachable without an API key.
- `tests/unit/agentic_fastapi_aws/test_Agentic_Code_Loader.py` — resolve → local / s3 / passthrough.
- `tests/unit/agentic_fastapi_aws/test_Agentic_Boot_Shim.py` — 10 tests. `read_image_version` file / missing; boot happy path + env-var writes; error-pinned inside Lambda; re-raise outside; 3 boot-state-writes gap tests.
- Older unit test folders unchanged from v0.1.24.

### Unit — EC2 spike (v0.1.31)

- `tests/unit/scripts/test_provision_ec2.py` — module surface; constants (t3.large, AL2023 pattern, :8000, SG name); user-data rendering (docker install, ECR login, run command, API-key env, 120 s watchdog); `--terminate` short-circuit; argparse safety (terminate off by default).

### Integration + deploy — unchanged from v0.1.24

Deploy-via-pytest tests still point at the 10 public endpoints; smoke tests don't yet assert `/admin/*`.

---

## agent_mitmproxy (v0.1.32)

### Unit — 34 passing + 1 skipped

- `tests/unit/agent_mitmproxy/test_package.py` — 4 tests. `path` attribute, version file presence, `version__agent_mitmproxy` matches file contents.
- `tests/unit/agent_mitmproxy/test_default_interceptor.py` — request-id shape (12-char hex), ts stamp, elapsed-ms calculation, response header round-trip.
- `tests/unit/agent_mitmproxy/test_audit_log_addon.py` — NDJSON shape, Basic `Proxy-Authorization` decode, stdout flush.
- `tests/unit/agent_mitmproxy/test_addon_registry.py` — registry concatenates interceptor + audit addons in expected order.
- `tests/unit/agent_mitmproxy/test_Routes__Health.py` — `/health/info` returns the Schema__Agent_Mitmproxy__Info; `/health/status` runs the CA + interceptor file checks; env-var override path.
- `tests/unit/agent_mitmproxy/test_Routes__CA.py` — `/ca/cert` returns PEM bytes + 503 when absent; `/ca/info` SHA-256 fingerprint matches `cryptography.x509`.
- `tests/unit/agent_mitmproxy/test_Routes__Config.py` — `/config/interceptor` round-trips the script source via `Safe_Str__Text__Dangerous`.
- `tests/unit/agent_mitmproxy/test_Routes__Web.py` — real `http.server.HTTPServer` on a free port; asserts the UI reverse-proxy strips `X-API-Key` + hop-by-hop headers.
- `tests/unit/agent_mitmproxy/test_Docker__Agent_Mitmproxy__Base.py` — `IMAGE_NAME` constant; `agent_mitmproxy.path` is a dir; dockerfile exists on disk. One test gated `@skipUnless(osbot_docker available)` because `Create_Image_ECR.__init__` imports `osbot_docker.apis.API_Docker`.

### Unit — EC2 spin-up (v0.1.32)

- `tests/unit/scripts/test_provision_mitmproxy_ec2.py` — 5 tests. Module surface; constants (t3.small, :8080 + :8000, SG name, role name); user-data rendering (docker install, ECR login, two `-p` bindings, proxy-auth + API-key env vars, `--restart=always`, `--name agent-mitmproxy`); `--terminate` short-circuit; argparse safety.

### No-mocks policy

All tests follow CLAUDE.md §Testing — no `mock`, no `patch`. Route tests use `FastAPI TestClient`; addon tests use `SimpleNamespace` fakes that duck-type the mitmproxy flow/request/response API (no mitmproxy import needed in the test process); the UI reverse-proxy test stands up a real `http.server.HTTPServer` on a free port.
