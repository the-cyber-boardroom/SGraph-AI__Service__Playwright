# Phase B · Step 7f — `sp vnc` user-data + compose + interceptor resolver + launch + wire `create_stack`

**Date:** 2026-04-29.
**Plan:** `team/comms/plans/v0.1.96__playwright-stack-split__06__sp-vnc__nginx-vnc-mitmproxy.md`.
**Template:** Phase B step 6f (`c0911f7`) — `sp prom` create_stack.
**Predecessor:** Phase B step 7e — `sp vnc` Service read paths (`877791e`).

**Compressed slice** — the OS 5f.1–5f.4b sequence lands as one commit, mirroring the prom 6f compression.

---

## What shipped

End-to-end `create_stack` working in pure logic. New: a per-section **interceptor resolver** for N5 (the only structural difference from the prom shape).

| File | Role |
|---|---|
| `vnc/service/Vnc__Compose__Template.py` | docker-compose.yml — 3 services (`chromium` + `nginx` + `mitmproxy`). Port 443 only; chromium uses `HTTPS_PROXY=http://mitmproxy:8080`; mitmproxy reads proxy auth from `/opt/sg-vnc/mitm/proxyauth` (host file mounted ro) and the active interceptor from `/opt/sg-vnc/interceptors/runtime/active.py`. **No secrets in the YAML** — locked by test. |
| `vnc/service/Vnc__Interceptor__Resolver.py` | N5 logic. Three baked example sources inline (`header_logger`, `header_injector`, `flow_recorder`). `resolve(choice)` returns `(source, label)` for NONE / NAME / INLINE. `list_examples()` exposes baked names for the future `sp vnc interceptors` command. |
| `vnc/service/Vnc__User_Data__Builder.py` | EC2 UserData bash. Installs `docker` + `httpd-tools` + `openssl`. Writes nginx config + bcrypt htpasswd + self-signed cert + mitmproxy proxyauth file + interceptor source + compose YAML. `operator_password` is interpolated **once** as a shell variable assignment, then referenced from there for htpasswd and proxyauth. |
| `vnc/service/Vnc__Launch__Helper.py` | `run_instance(...)`. Base64 UserData, `MinCount=MaxCount=1`, `DEFAULT_INSTANCE_TYPE='t3.large'` (chromium needs RAM). |
| `vnc/service/Vnc__AWS__Client.py` (modified) | `setup()` now wires the 5th slot (`launch`). |
| `vnc/service/Vnc__Service.py` (modified) | New slots: `compose_template` / `user_data_builder` / `interceptor_resolver`. New method: `create_stack(request, creator='')` — resolves all defaults, calls the resolver, threads the resolved source + label through user-data + tags + response. |

## Departures from the `sp prom` 6f template

- **N5 interceptor resolver is a separate file** (not in service). Three shapes (NONE / NAME / INLINE) → `(source, label)`. NONE always writes a no-op script so the mitmproxy `--scripts` arg stays static across boots. INLINE with empty source raises (defensive).
- **One operator password, two consumers** — service generates once via `secrets.token_urlsafe(24)`, user-data interpolates once into `SG_VNC_OPERATOR_PASSWORD` shell var; htpasswd + proxyauth file both reference it from there. Defensive test asserts the literal value appears exactly once in the rendered bash.
- **No password in compose YAML** — locked by test on the compose template (`'PROXYAUTH=' not in out`, `'password' not in out.lower()`). Secrets travel exclusively through user-data + host-mounted files.
- **TLS at boot** — user-data generates a self-signed cert via openssl. nginx `ssl_certificate` reads `/etc/nginx/tls/cert.pem`. Future slice can swap to a baked AMI cert + Let's-Encrypt design without changing the user-data shape.
- **3 install packages** — `docker` + `httpd-tools` (htpasswd) + `openssl`. Prom only needed `docker`.
- **`t3.large` default** vs prom's `t3.medium` — chromium-VNC plus mitmproxy + nginx need ~6 GB resident.

## Tests

47 new tests, all green:

| Group | Tests |
|---|---|
| `Vnc__Compose__Template` | 11 — defaults / custom images / no leftover placeholders / canonical container names / sg-net network / chromium HTTPS_PROXY env / chromium-only browser flag / **port 443 only** / **no password in compose** (defensive) / mitmproxy command shape / placeholders match constant |
| `Vnc__Interceptor__Resolver` (incl. `EXAMPLES` + `list_examples`) | 8 — examples dict non-empty + known / every example imports mitmproxy / NONE default returns no-op / NONE explicit / NAME returns baked example + label / NAME unknown raises with help / INLINE returns operator source verbatim / INLINE empty raises |
| `Vnc__User_Data__Builder` | 14 — shape / strict bash / stack+region / compose heredoc / interceptor heredoc / no leftover placeholders / dnf installs (incl. httpd-tools + openssl) / openssl cert gen / htpasswd + proxyauth files + chmod 600 / compose-up in compose dir / **password appears exactly once** (defensive) / placeholders match constant / canonical paths under /opt/sg-vnc |
| `Vnc__Launch__Helper` | 8 — returns instance id / base64 UserData / **default `t3.large`** / `MinCount=MaxCount=1` / profile optional + attached / empty response raises / boto failure propagates |
| `Vnc__AWS__Client.setup()` | extended in-place from 4-helper to 5-helper assertion |
| `Vnc__Service.create_stack` | 6 — empty request resolves all defaults / **NAME interceptor flows through resolver + tags + user-data + response** / **password flows into user-data only (defensive)** / sg uses resolved caller_ip / overrides take priority / launch call carries correct user-data + tags |
| `Vnc__Service.setup()` | extended to verify all 8 helpers (5 read-path + 3 new) |

## Test outcome

| Suite | Before | After | Delta |
|---|---|---|---|
| `tests/unit/sgraph_ai_service_playwright__cli/vnc/` | 114 | 161 | +47 |

## Files changed

```
A  sgraph_ai_service_playwright__cli/vnc/service/Vnc__Compose__Template.py
A  sgraph_ai_service_playwright__cli/vnc/service/Vnc__Interceptor__Resolver.py
A  sgraph_ai_service_playwright__cli/vnc/service/Vnc__User_Data__Builder.py
A  sgraph_ai_service_playwright__cli/vnc/service/Vnc__Launch__Helper.py
M  sgraph_ai_service_playwright__cli/vnc/service/Vnc__AWS__Client.py
M  sgraph_ai_service_playwright__cli/vnc/service/Vnc__Service.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/service/test_Vnc__Compose__Template.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/service/test_Vnc__Interceptor__Resolver.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/service/test_Vnc__User_Data__Builder.py
A  tests/unit/sgraph_ai_service_playwright__cli/vnc/service/test_Vnc__Launch__Helper.py
M  tests/unit/sgraph_ai_service_playwright__cli/vnc/service/test_Vnc__AWS__Client.py
M  tests/unit/sgraph_ai_service_playwright__cli/vnc/service/test_Vnc__Service.py
M  team/roles/librarian/reality/v0.1.31/06__sp-cli-duality-refactor.md
```

## Failure classification

**No surprises.** The N5 resolver landed cleanly — its boundary (`(source, label)` tuple) was clear before any code was written, so the user-data builder's signature stayed simple.

## Next

Step 7g — `Routes__Vnc__Stack` + `Routes__Vnc__Flows` (FastAPI surface). The `create` body will need the same `body: dict` workaround used in `Routes__Prometheus__Stack` because `Schema__Vnc__Stack__Create__Request` carries a nested `Schema__Vnc__Interceptor__Choice`.
