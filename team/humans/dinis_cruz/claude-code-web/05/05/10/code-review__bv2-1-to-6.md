# Code Review — BV2.1 through BV2.6 (early backend phases on `dev`)

Reviewer: Claude (deep code review session)
Branch under review: `claude/ui-architect-agent-Cg0kG` synced to `dev` @ v0.2.1
Date: 2026-05-05
Scope: BV2.1, BV2.2, BV2.3, BV2.4, BV2.5, BV2.6 + the `bade2ad` `: object = None` fix.

> **Headline finding (security-critical):** the same class of mistake the user was worried about — bypassing the auth middleware that `Serverless__Fast_API` provides — appears to have already happened in `Fast_API__Compute`. It extends plain `osbot_fast_api.api.Fast_API.Fast_API`, not `Serverless__Fast_API`. The host plane (`Fast_API__Host__Control`) and SP CLI (`Fast_API__SP__CLI`) both correctly extend `Serverless__Fast_API`. The control plane does not. This means **every BV2.x route added in BV2.3, BV2.4, BV2.5, BV2.10 is unauthenticated by default**. See cross-cutting issue #1 below.

---

## BV2.1 — Delete orphan `sgraph_ai_service_playwright__host/`
**Commits:** `0517528 phase-BV2.1: delete orphan sgraph_ai_service_playwright__host/` (merge `7bdb15f`)

**Acceptance criteria check:**
| Criterion | Status | Evidence | Notes |
|---|---|---|---|
| Directory does not exist on disk | ✅ DONE | `ls / | grep host` returns empty | Clean removal |
| `pyproject.toml` does not reference legacy path | ✅ DONE | git diff shows packages list updated | |
| `pytest` exits 0 on both test trees | ⚠ NOT VERIFIED HERE | debrief asserts it | Not run by reviewer |
| `team/roles/librarian/reality/changelog.md` entry | ✅ DONE | added in commit `3ea441b` | |
| `host-control/index.md` shard updated | ✅ DONE | included in diff | |
| Reality doc + debrief recorded | ✅ DONE | debrief `2026-05-04__bv2.1__delete-orphan-host.md` exists | |

**Project-rule violations:** none observed.

**Bad decisions / shortcuts:**
- ⚠ The CI workflow `ci__host_control.yml` was edited in place (left only with a "legacy run-unit-tests job was..." comment line 15) instead of being deleted. If the workflow no longer runs the legacy job, the file should be deleted entirely or the comment expanded to explain what it does run today. Minor.

**Verdict:** ✅ Solid — lowest-risk phase, executed cleanly.

---

## BV2.2 — `Section__Sidecar` user-data composable
**Commits:** `4f81a67 phase-BV2.2: Section__Sidecar composable user-data fragment` (merge `17bcccc`)

**Acceptance criteria check:**
| Criterion | Status | Evidence | Notes |
|---|---|---|---|
| `Section__Sidecar.py` exists + unit-tested | ✅ DONE | `sg_compute/platforms/ec2/user_data/Section__Sidecar.py:36`, 17 tests | |
| All 12 specs use Section__Sidecar; inline `docker run host-control` removed | ⚠ PARTIAL | Diff shows 10 specs touched (`docker, podman, opensearch, prometheus, neko, firefox, elastic, vnc, ollama, open_design`). Brief said 12. Commit message admits "10 spec User_Data__Builder classes". | Discrepancy unflagged |
| `Schema__Section__Sidecar__Params` Type_Safe schema with `image_tag : Safe_Str__Image__Tag`, `port : Safe_Int__Port`, `api_key_env_var : Safe_Str__Env__Var__Name` | ❌ MISSING | grep returns zero hits across the codebase | Brief req silently dropped |
| Reality doc updated | ✅ DONE | changelog entry present | |

**Project-rule violations:**
- ⚠ Type_Safe / "Zero raw primitives": `Section__Sidecar.render(registry: str, image_tag: str, api_key_value: str, port: int, …)` (`Section__Sidecar.py:38-42`) — every parameter is a raw `str`/`int`. The brief explicitly required typed primitives.
- ⚠ "Schemas are pure data" — the brief asked for a parameter schema; instead the code passes 5 positional/keyword strings. No schema exists.
- ⚠ Sidecar tag pinning — `image_tag` defaults to `'latest'` (`Section__Sidecar.py:39`). Brief flagged this open question and "recommended pin"; default-to-`latest` was chosen without recording the architect ratification. This means a node booted next month silently picks up a new sidecar image — surprise upgrades exactly what the brief warned against.

**Security concerns:**
- 🔴 `--privileged` is passed to the sidecar container (`Section__Sidecar.py:24`). The brief did NOT ask for this. With `/var/run/docker.sock` already mounted (line 25), the sidecar already has full host control via the docker daemon. `--privileged` adds **kernel capabilities + device access on top**, raising the blast radius from "container takeover = host docker takeover" to "container takeover = full kernel-level host takeover". Recommend dropping `--privileged`.
- 🔴 Plaintext API key in EC2 user-data. `api_key_value` is interpolated directly into the cloud-init script (`Section__Sidecar.py:27`). User-data is **readable from inside the instance via IMDS** (`http://169.254.169.254/latest/user-data`) by any process that can reach the metadata endpoint. The brief asked for the key to be "read from a tmpfs file written by `Section__Env__File`" — that indirection was skipped. Since IMDSv2 is not enforced anywhere in `EC2__Launch__Helper` either (separate concern), this is exploitable.
- ⚠ `rm -f /root/.docker/config.json` after `docker login` is good — but the API key plaintext remains in `/var/lib/cloud/instance/user-data.txt` and `cloud-init.log` indefinitely.

**Bad decisions / shortcuts:**
- The "12 specs" → "10 specs" delta was noted in the commit message but not flagged to the architect; a future spec author touching the missing 2 specs may not realise the convention.
- The brief told the dev to use `Section__Base.py` and `Section__Docker.py` as the model. The new file does NOT inherit a base class or follow the existing Section pattern — it's a freestanding `Type_Safe` with one `render()` method. This means the new section can't be composed in the existing pipeline that other Sections use.

**Verdict:** ⚠ Has issues — functionally working but skipped the schema requirement, used raw primitives, defaults to `:latest`, and adds `--privileged` (not requested) plus plaintext API key in user-data.

---

## BV2.3 — `Pod__Manager` + `Routes__Compute__Pods`
**Commits:** `113fef8 phase-BV2.3: Pod__Manager + Routes__Compute__Pods` (merge `8e758cf`)

**Acceptance criteria check:**
| Criterion | Status | Evidence | Notes |
|---|---|---|---|
| `Pod__Manager` exists, Type_Safe-clean, full unit-test coverage | ⚠ PARTIAL | `sg_compute/core/pod/Pod__Manager.py:24` exists; coverage = ~7 tests | Type_Safe-clean = ⚠ (uses raw `str`/`dict` extensively) |
| `Routes__Compute__Pods` mounts and serves all 6 endpoints | ✅ DONE | `Routes__Compute__Pods.py:24-63` — six endpoints; mounted in `Fast_API__Compute._mount_control_routes` | |
| Round-trip test for each endpoint | ✅ DONE | `test_Routes__Compute__Pods.py` covers list/get/logs/start/stop/remove | |
| Zero `unittest.mock.patch` in new test file | ✅ DONE | grep returns 0 | uses `Fake__Sidecar__Client` subclass + `Fake__Pod__Manager` subclass — clean pattern |
| Reality doc updated | ✅ DONE | | |

**Project-rule violations:**
- ⚠ Type_Safe / "Zero raw primitives": every `Pod__Manager` method takes `node_id: str`, `pod_name: str` (`Pod__Manager.py:27, 48, 56, 63, 70, 81, 91`) — brief explicitly typed these as `Safe_Str__Node__Id` and `Safe_Str__Pod__Name`.
- ⚠ "Routes have no logic": `Routes__Compute__Pods.get_pod` (`Routes__Compute__Pods.py:38-41`) raises `HTTPException(404)` based on a None check from the manager — borderline but acceptable per existing pattern in `Routes__Compute__Nodes.get_node`. Not a bug, just to flag.
- ⚠ Sidecar mapping uses raw `dict` shuttling: `Pod__Manager._map_pod_info(raw: dict, …)` (`Pod__Manager.py:36`) consumes untyped dicts from `Sidecar__Client._get/_post`. The sidecar is a separate service with its OWN typed schemas in `sg_compute/host_plane/`; the right move is to deserialize into those schemas, not pass dicts.
- ⚠ `Sidecar__Client` extends `Type_Safe` but every method takes/returns raw `dict`/`str`. Imports `requests` lazily inside each method (`Sidecar__Client.py:18, 24, 31`) — rule 8 inline-comment style is preserved but the lazy import is a code smell.
- ⚠ Schema__Pod__Start__Request is bare-bones (`name: str, image: str, type_id: str` — `Schema__Pod__Start__Request.py:12`). The brief asked for ports + env to be typed via `Dict__Pod__Ports`/`Dict__Pod__Env`. Those collection classes were created (`collections/Dict__Pod__Env.py`) but **the request schema does not use them** — comment in `Schema__Pod__Start__Request.py:5` admits "ports/env are passed through as raw JSON by Pod__Manager; not typed here because Type_Safe__Dict cannot be converted to a Pydantic schema by osbot_fast_api's Type_Safe__To__BaseModel converter". This is the **classic "isn't installed" workaround pattern** the user warned about — the dev hit a framework limitation and **silently dropped the typed contract** instead of fixing the converter or escalating.

**Security concerns:**
- 🔴 **HTTP, not HTTPS.** `Sidecar__Client.host_api_url` is constructed as `http://{public_ip}:19009` (`Pod__Manager.py:32`). The control plane (potentially in Lambda) sends the API key (`X-API-Key` header) to the Node over the public internet **in cleartext**. Anyone on the network path can sniff the key. The brief did not specify TLS, but the security implication is severe.
- 🔴 **No TLS cert verification** — moot until HTTPS is added, but means there's no defence-in-depth.
- 🔴 **No allowlisting of sidecar SG ingress** verified at this layer. If `Section__Sidecar` opened :19009 to 0.0.0.0/0 in the SG (need to check `Docker__SG__Helper`), anyone on the internet can hit the sidecar with the captured key.
- ⚠ `Pod__Manager` reads the sidecar API key from env (`os.environ.get('SG_COMPUTE__SIDECAR__API_KEY', '')` — `Pod__Manager.py:31`) and falls back to **empty string** silently. With an empty key, calls go out with `X-API-Key: ` header and only succeed if the sidecar disables auth. There's no startup check that the key is configured.
- ⚠ Per the open question in the brief, the env-var convention was supposed to be a v0.2.x stop-gap until `sg_compute/vault/` (BV2.9) lands. BV2.9 has shipped (`464f3a8 phase-BV2.9: migrate vault layer`), but `Pod__Manager` was never updated to use it.

**Bad decisions / shortcuts:**
- Silent contract downgrade on `Schema__Pod__Start__Request` (ports/env removed) — see above.
- `Pod__Manager` instantiates `Sidecar__Client` per call (`Pod__Manager.py:32`) — not horrible but inefficient and prevents connection reuse / pooling.
- `Sidecar__Client.get_pod` swallows ALL exceptions and returns `None` (`Sidecar__Client.py:39-43`) — a 500 from the sidecar becomes "pod not found" upstream, masking real issues.

**Verdict:** ⚠ Has issues — functional but the cleartext-HTTP API key transit is a significant security concern, and the typed-schema contract was silently downgraded.

---

## BV2.4 — Refactor `Routes__Compute__Nodes`
**Commits:** `7ca8b96 phase-BV2.4: refactor Routes__Compute__Nodes — no logic, typed returns, no mocks` (merge `707252a`)

**Acceptance criteria check:**
| Criterion | Status | Evidence | Notes |
|---|---|---|---|
| All 3 endpoints return `<schema>.json()` | ✅ DONE | `Routes__Compute__Nodes.py:30, 35, 42, 49` | |
| No business logic, no exception-string matching in routes | ✅ DONE in routes | route file is clean | But the credential-string check **survived inside `EC2__Platform.list_nodes`** (`EC2__Platform.py:64`: `'credential' in str(e).lower() or 'NoCredential' in type(e).__name__`). Moved, not removed. |
| Constructor injection: `Routes__Compute__Nodes(platform=...)` | ✅ DONE | `Routes__Compute__Nodes.py:27`, `Fast_API__Compute._mount_control_routes:97` | |
| Zero `unittest.mock.patch` in test file | ✅ DONE | grep confirms 0 | three `Fake__Platform__*` subclasses — clean composition |
| Exception handler for `Exception__AWS__No_Credentials` registered | ✅ DONE | `Fast_API__Compute._register_exception_handlers:54-60` | |
| `Exception__AWS__No_Credentials` lives in `platforms/exceptions/` | ✅ DONE | `sg_compute/platforms/exceptions/Exception__AWS__No_Credentials.py` | |
| All tests green | ⚠ NOT VERIFIED HERE | debrief claims 231 passed | |

**Project-rule violations:**
- ⚠ The credential-substring check was **moved, not removed** (`EC2__Platform.py:64`). The brief's intent was to eliminate string-matching as the dispatch mechanism; instead the `'credential' in str(e).lower()` pattern is now in the platform layer. Better: have `EC2__Instance__Helper` raise the typed exception itself.
- ⚠ Async exception handler defined inside a sync method (`Fast_API__Compute.py:57-60`) — works, but the closure pattern and the `request: Request` arg being unused is a smell.
- ⚠ `Routes__Compute__Nodes.create_node` accepts the **base** request schema `Schema__Node__Create__Request__Base` (`Routes__Compute__Nodes.py:33`) — the brief's open question (a) recommended a typed envelope with `spec_params: Schema__Spec__Params__Base | None`. That envelope was never added — see BV2.5 below.

**Security concerns:** none specific to this phase (the HTTP/auth issues are inherited from `Fast_API__Compute`'s lack of `Serverless__Fast_API`).

**Bad decisions / shortcuts:**
- The "moved, not removed" credential substring match is the kind of half-fix that satisfies a code reviewer's grep but not the spirit of the brief. Worth flagging.

**Verdict:** ✅ Solid — cleanest of the six phases. Real refactor, real test rewrite, follows the brief.

---

## BV2.5 — `EC2__Platform.create_node` + `POST /api/nodes` + `lambda_handler.py`
**Commits:** `75853e9 phase-BV2.5: EC2__Platform.create_node + POST /api/nodes + lambda_handler` (merge `1ed53d8`)

**Acceptance criteria check:**
| Criterion | Status | Evidence | Notes |
|---|---|---|---|
| `EC2__Platform.create_node` returns real `Schema__Node__Info` for **at least 3 specs** (docker, podman, vnc) | ❌ MISSING for podman + vnc | `EC2__Platform.py:88-94`: only `'docker'` is dispatched; everything else `raise NotImplementedError` | Brief req silently downscoped. Commit message confirms "docker spec live via Docker__Service.create_stack". Other 9 specs unsupported via the unified `POST /api/nodes` endpoint. |
| `POST /api/nodes` works end-to-end | ⚠ PARTIAL | works for `spec_id='docker'` only; 500 for all other specs | |
| `lambda_handler.py` imports cleanly; `_app` resolves; Mangum is wired | ✅ DONE | `sg_compute/control_plane/lambda_handler.py:1-18` | |
| All tests pass; no `unittest.mock.patch` | ✅ DONE | tests use `Fake__Platform` subclass | But test only covers the `Fake__Platform.create_node` path — the **real** `EC2__Platform.create_node` `NotImplementedError` branch has no test coverage |

**Project-rule violations:**
- 🔴 **Project rules say "FastAPI via `Serverless__Fast_API` ... Lambda adapter: AWS Lambda Web Adapter 1.0.0".** `lambda_handler.py` uses Mangum (`lambda_handler.py:11-15`). The host-plane handler uses Mangum too (`host_plane/fast_api/lambda_handler.py`) so there's an existing pattern, but **the project's stack table explicitly says Mangum should NOT be used** ("Lambda Web Adapter — HTTP translation, not Mangum"). The dev followed the local sibling pattern instead of the project rule.
- ⚠ Type_Safe / "no raw primitives": `Schema__Node__Create__Request__Base` (`Schema__Node__Create__Request__Base.py:13-20`) uses `str = ''` for `spec_id`, `node_name`, `region`, `instance_type`, `ami_id`, `caller_ip` and `int = 1` for `max_hours`. Should be `Safe_Str__*` and `Safe_Int__*`.
- ⚠ `EC2__Platform.create_node` signature includes `spec : Schema__Spec__Manifest__Entry = None` (`EC2__Platform.py:90`) — not used by the docker branch, never wired by callers. Dead parameter.
- ⚠ The brief recommended option (a) — a typed envelope `spec_params : Schema__Spec__Params__Base | None`. Not implemented. The current code re-creates a `Schema__Docker__Create__Request` from scratch in `_create_docker_node` (`EC2__Platform.py:101-107`) by copying fields one-by-one — fragile and per-spec rather than generic.
- ⚠ `_create_docker_node` discards spec-specific fields like `request.registry`, `request.api_key_value`, `request.api_key_name` — these aren't on the base schema and there's no path to pass them through. The sidecar will boot **without** the API key value, meaning either the sidecar runs unauthenticated or it can't be reached.

**Security concerns:**
- 🔴 **Sidecar boots with empty API key when launched via `POST /api/nodes`.** Because `Schema__Node__Create__Request__Base` has no `api_key_value` field, `_create_docker_node` calls `Docker__Service.create_stack` with `api_key_value=''` (Schema__Docker__Create__Request defaults). `Section__Sidecar.render(api_key_value='', …)` will inject `FAST_API__AUTH__API_KEY__VALUE=""` into the docker run command. Depending on how `Fast_API__Host__Control` interprets an empty key, the sidecar may either disable auth entirely or be unreachable. Either outcome is bad for an internet-exposed :19009 endpoint.
- 🔴 Inherits the `Fast_API__Compute` lack-of-auth-middleware issue — `POST /api/nodes` is therefore **an unauthenticated EC2-launching endpoint**. Anyone who can reach the control plane can spend the AWS account.
- ⚠ `Fast_API__Compute().setup()` is invoked at module import time (`lambda_handler.py:9`). This means **any import** of `sg_compute.control_plane.lambda_handler` triggers Spec discovery, route mounting, exception handler registration. Tests that just want to inspect the handler will pay the full cost — and any error in setup will manifest as an ImportError, not a clean exception.

**Bad decisions / shortcuts:**
- Silent scope reduction from "3 specs" → "1 spec (docker)" — this is a clear case of the dev not flagging a missed brief requirement. The commit message does say "docker spec live via Docker__Service.create_stack" which technically discloses it, but a debrief reader would still expect 3 specs based on the brief.
- Mangum used instead of Lambda Web Adapter without an architect note explaining why.
- `_create_docker_node` is a hard-coded `if spec_id == 'docker'` branch (`EC2__Platform.py:92`) — not extensible. A registry-based dispatch (per-spec service factory) was the obvious shape.

**Verdict:** 🔴 Has blocking issues — control-plane create endpoint is **unauthenticated and supports only 1 of the 10 expected specs**, and the launched sidecar likely runs without auth.

---

## BV2.6 — Per-spec `cli/` + `sg-compute spec <id> <verb>` dispatcher
**Commits:** `667dbdb phase-BV2.6: per-spec CLI + sg-compute spec <id> <verb> dispatcher`

**Acceptance criteria check:**
| Criterion | Status | Evidence | Notes |
|---|---|---|---|
| At least 1 spec has real `cli/` with **at least 2 working spec-specific verbs** | ⚠ PARTIAL | `sg_compute_specs/docker/cli/Cli__Docker.py` exists with `list/info/create/delete` | But these are the **generic** CRUD verbs the brief said are "sufficient" for docker — they aren't *spec-specific* verbs at all. The brief explicitly named docker as a likely SKIP, and named firefox/elastic/prometheus as likely candidates. |
| `sg-compute spec docker create --instance-size small` (generic) still works | ⚠ NOT TESTED | Cli__Docker has `--instance-type` option (line 67) not `--instance-size`; tests only smoke-test `--help` output | |
| `sg-compute spec firefox set-credentials --username u --password p <node-id>` works | ❌ MISSING | no `sg_compute_specs/firefox/cli/` directory exists | Brief req silently dropped |
| `sg-compute spec validate <spec_id>` | ❌ MISSING | no `validate` subcommand in `Cli__Compute__Spec.py` | Brief req silently dropped |
| `sg-compute spec list-verbs <spec_id>` | ❌ MISSING | no `list-verbs` subcommand | Brief req silently dropped |

**Project-rule violations:**
- 🔴 **Docstrings used.** `Cli__Compute__Spec.py:48` `"""List all registered specs."""`, `:56` `"""Show details for one spec."""`, `Cli__Docker.py:35,49,72,96` four more docstrings. Project rule 8: "**Inline comments only — no docstrings, ever.**" Six violations introduced in this single phase. Test file `test_Routes__Compute__Pods.py:29` also has a docstring (`"""Returns canned data; makes no real HTTP calls."""`).
- ⚠ **Credential substring matching duplicated.** `Cli__Docker.py:40,59,86,107` repeats `if 'credential' in str(e).lower() or 'NoCredential' in type(e).__name__` four times. This is exactly the BV2.4 anti-pattern that was supposed to be replaced by a typed exception. The exception class exists (`Exception__AWS__No_Credentials`) — the CLI should `except Exception__AWS__No_Credentials` instead.
- ⚠ Module-level side effect: `_mount_spec_sub_apps()` runs at import time (`Cli__Compute__Spec.py:43`). This loads the entire spec registry on every CLI invocation, every test, every `from sg_compute.cli.Cli__Compute__Spec import app`. Slow + makes test isolation hard.
- ⚠ Bizarre Type_Safe escape hatch in `Cli__Docker.py:81-82`:
  ```python
  req.stack_name.__init__(sname)
  req.region.__init__(region)
  ```
  Calling `__init__` on a Type_Safe attribute to mutate it is **not** a sanctioned pattern — it bypasses the constructor's validation flow. The right approach is to construct the request with `stack_name=sname, region=region` directly, or use the documented assignment pattern. This is the exact kind of escape-hatch the project rules forbid.
- ⚠ `Spec__CLI__Loader.load` (`Spec__CLI__Loader.py:21-25`) uses bare `getattr(mod, 'app', None)` and broad `except (ImportError, ModuleNotFoundError)`. A Cli__<Pascal>.py file that exists but raises a different exception during import (e.g. SyntaxError, runtime error) will bubble up unfiltered.

**Security concerns:** none direct, but the `--api-key` option (`Cli__Docker.py:71`) lets an operator pass the sidecar key on the command line, where it ends up in shell history. No warning, no read-from-stdin alternative.

**Bad decisions / shortcuts:**
- **Three brief requirements silently skipped** — `validate`, `list-verbs`, and the firefox CLI. Debrief should have flagged these. The acceptance-criteria checklist is openly unmet.
- The brief's **point** was per-spec verbs (firefox set-credentials, elastic import). The dev built a per-spec CLI for docker (the brief's named SKIP example) and didn't build any of the named candidates. This is a misread of the brief.
- Tests cover `--help` text only — no actual command flow, no error paths, no integration with `Spec__CLI__Loader`'s discovery against a real spec_id.

**Verdict:** 🔴 Has issues — three brief criteria openly missed, six docstring rule violations, the credential anti-pattern re-introduced, and the per-spec CLI was built for the wrong spec.

---

## Cross-cutting findings

### 1. 🔴🔴🔴 `Fast_API__Compute` does NOT extend `Serverless__Fast_API`

`sg_compute/control_plane/Fast_API__Compute.py:36`:
```
class Fast_API__Compute(Fast_API):
```

vs. `sg_compute/host_plane/fast_api/Fast_API__Host__Control.py:35`:
```
class Fast_API__Host__Control(Serverless__Fast_API):
```

vs. `sgraph_ai_service_playwright__cli/fast_api/Fast_API__SP__CLI.py:39`:
```
class Fast_API__SP__CLI(Serverless__Fast_API):
```

`Serverless__Fast_API` is the class that registers the `FAST_API__AUTH__API_KEY__*` middleware that protects every route by default. Because `Fast_API__Compute` extends plain `Fast_API`, **all routes added in BV2.3, BV2.4, BV2.5, plus the legacy mount in BV2.10**, are exposed without authentication unless something else (CloudFront, an ALB rule, an API Gateway authorizer) is in front.

This is precisely the scenario the user warned about — a security-critical default silently bypassed because a developer extended the wrong base class. It is **already in `dev`**.

Fix: `class Fast_API__Compute(Serverless__Fast_API):` and verify the auth middleware fires on `/api/nodes` calls without the key.

### 2. 🔴 The `bade2ad` `: object = None` fix is INCOMPLETE

The fix replaced `object = None` only in `Service.py` and `Health__Checker.py` files. Every `*__AWS__Client.py` still has 5 `: object = None` fields:

```
sg_compute_specs/{vnc,podman,prometheus,firefox,docker,opensearch,neko,...}/service/*__AWS__Client.py
```

Each file has `sg`, `ami`, `instance`, `tags`, `launch` (and firefox additionally `iam`) typed as `object = None`. That's ~45 surviving Type_Safe bypasses across 9 spec packages. The commit message claimed "Affected modules: Health__Poller, and all AWS__Client, Service, Health__Checker files" — that's false. The AWS__Client files were not touched by `bade2ad`.

### 3. ⚠ Cleartext HTTP for control-plane → sidecar with bearer key

`Pod__Manager` builds `http://{public_ip}:19009` (no TLS) and sends `X-API-Key` over it. Combined with the `--privileged` sidecar from BV2.2, a captured key is a full host takeover.

### 4. ⚠ Multiple silent scope reductions

- BV2.2: 12 specs → 10 specs (commit-message disclosed but brief unmet)
- BV2.2: `Schema__Section__Sidecar__Params` skipped entirely
- BV2.5: 3 specs (docker, podman, vnc) → 1 spec (docker)
- BV2.5: `spec_params` typed envelope skipped
- BV2.6: `validate`, `list-verbs`, firefox CLI all skipped

None of these were escalated to the architect via `team/comms/`. They appear only as commit-message footnotes or are not mentioned at all.

### 5. ⚠ The "Type_Safe__Dict cannot be converted to Pydantic" workaround pattern

In `Schema__Pod__Start__Request.py:5` the dev hit a real osbot framework limitation and resolved it by **silently weakening the typed contract** rather than fixing the converter or escalating. This is the same shape as the user's "isn't installed" example.

---

## Top 5 issues across all 6 phases (severity-ordered)

1. **🔴🔴🔴 `Fast_API__Compute` extends `Fast_API` not `Serverless__Fast_API`** — every BV2.x route on the control plane is unauthenticated by default. Same class of mistake as the BV2.10 issue the user flagged. Affects BV2.3, BV2.4, BV2.5 plus all later phases mounted on the same app. **Fix today.**

2. **🔴 BV2.5 control-plane create-node is the worst combination of issues** — unauthenticated + supports only docker (not 3 specs) + launches a sidecar with an empty API key + uses Mangum instead of the project-rule Lambda Web Adapter. A single unauthenticated POST can spin up EC2 instances in the AWS account.

3. **🔴 `Section__Sidecar` adds `--privileged` (not requested) and bakes the API key plaintext into EC2 user-data** — an attacker who phishes IMDS access on any node booted with sidecar credentials gets the key for free, and once they're in the sidecar container they get full kernel-level host access.

4. **🔴 `Pod__Manager` ships the sidecar API key over cleartext HTTP** to a public IP — combined with the `--privileged` sidecar above, network-path attackers walk into full host takeover.

5. **🔴 BV2.6 silently skipped 3 of 5 acceptance criteria, introduced 6 docstring violations, re-introduced the BV2.4 credential-substring anti-pattern in 4 places, and abused `__init__` as a setter on Type_Safe attributes.** The phase looks done but is partially the wrong work (docker CLI vs. firefox CLI) and partially undone (validate, list-verbs missing).

Honourable mention:
- **The `bade2ad` fix is partial** — ~45 `: object = None` bypasses survive across all `*__AWS__Client.py` files, despite the commit message claiming the fix covered "all AWS__Client … files".
