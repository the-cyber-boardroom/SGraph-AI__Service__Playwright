# Phase B · Step 7e — `sp vnc` Service orchestrator (read paths) + flows()

**Date:** 2026-04-29.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split__06__sp-vnc__nginx-vnc-mitmproxy.md`.
**Template:** Phase B step 6e (`2b5b93b`) — `sp prom` Service read paths.
**Predecessor:** Phase B step 7d — `sp vnc` HTTP base + probe (`4d5a035`).

---

## What shipped

4 small focused files mirroring the prom 6e shape, plus an extra `flows()` operation on the service for the future `sp vnc flows` typer + `Routes__Vnc__Flows` route.

| File | Role |
|---|---|
| `vnc/service/Caller__IP__Detector.py` | Section-local; tests subclass + override `fetch()`. |
| `vnc/service/Random__Stack__Name__Generator.py` | Vocabulary parity with elastic + os + prom (parity test). |
| `vnc/service/Vnc__Stack__Mapper.py` | Pure mapper. Builds `viewer_url` + `mitmweb_url` (empty when no public IP). Decodes the `sg:interceptor` tag back into `(kind, name)`. |
| `vnc/service/Vnc__Service.py` | Tier-1 orchestrator. Read paths + `flows()`. `setup()` wires 5 helpers; `create_stack` lands in 7f. |

## Departures from the `sp prom` 6e template

- **Two probes per `health()`** — both `nginx_ready` and `mitmweb_ready` must pass for state to flip to READY. `flow_count` falls through to `-1` sentinel when mitmweb is unreachable, mirroring the prom convention.
- **`flows(region, stack_name)` operation** — new at the service level (no equivalent in prom). Returns `List__Schema__Vnc__Mitm__Flow__Summary`. Empty when no instance / no IP / mitmweb unreachable. The `Routes__Vnc__Flows` route in 7g is a 5-line wrapper.
- **N5 interceptor decode** — `Vnc__Stack__Mapper._interceptor_from_tag` parses the three marker forms (`'none'` / `'name:{ex}'` / `'inline'`) back into `(Enum__Vnc__Interceptor__Kind, name)`. Defensive on unknown markers (falls through to NONE).
- **Mitmweb payload mapper** — `_flow_summary_from_mitmweb` is a small module-level pure function, not a class, since it's only used by `flows()`. Handles missing `pretty_url` (falls back to `url`), missing `response` (`status_code=0`), and missing `timestamp_created` (empty string).

## Tests

25 new tests, all green:

| Group | Tests |
|---|---|
| `Caller__IP__Detector` | 3 — defaults, strips trailing newline, rejects malformed |
| `Random__Stack__Name__Generator` | 2 — shape, **vocabulary parity with elastic + os + prom** |
| `Vnc__Stack__Mapper` | 7 — happy path, no public IP → empty URLs, **interceptor `none` / `name:{ex}` / `inline`** decoding, unknown marker → NONE (defensive), state mapping |
| `Vnc__Service` (read paths + flows) | 13 — list (empty + 2 stacks), get (hit + miss), delete (hit + miss), health (no instance / no public IP / nginx+mitmweb ready / nginx-only-ready), flows (no instance / mitmweb payload mapping incl. missing fields), setup() returns self + wires 5 helpers |

## Test outcome

| Suite | Before | After | Delta |
|---|---|---|---|
| `tests/unit/sgraph_ai_service_playwright__cli/vnc/` | 89 | 114 | +25 |

## Files changed

```
A  sgraph_ai_service_playwright__cli/vnc/service/Caller__IP__Detector.py
A  sgraph_ai_service_playwright__cli/vnc/service/Random__Stack__Name__Generator.py
A  sgraph_ai_service_playwright__cli/vnc/service/Vnc__Stack__Mapper.py
A  sgraph_ai_service_playwright__cli/vnc/service/Vnc__Service.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/service/test_Caller__IP__Detector.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/service/test_Random__Stack__Name__Generator.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/service/test_Vnc__Stack__Mapper.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/service/test_Vnc__Service.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## Next

Step 7f (combined per the operator's note for sp prom) — user-data + compose template + interceptor resolver + launch helper + wire `create_stack`. One commit.
