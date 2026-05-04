# Debrief — Proxy Gateway P1 + P2

**Date:** 2026-04-20
**Commits:** `721335f` (P1 — agent_mitmproxy upstream mode), `005127b` (P2 — Playwright proxy cleanup)
**Branch:** `claude/start-explorer-session-OgbPq`
**Plan doc:** `team/comms/plans/v0.1.33__proxy-gateway-p1-and-p2.md`

---

## What was built

### P1 — agent_mitmproxy upstream mode (v0.1.33)

Three new env vars: `AGENT_MITMPROXY__UPSTREAM_{URL,USER,PASS}`.

`entrypoint.sh` rewritten to build the mitmweb command conditionally and write it to `/tmp/run_mitmweb.sh`. `supervisord.conf` updated to call the wrapper script instead of embedding the command directly. This sidesteps the `%(ENV_*)s` interpolation crash when env vars are unset.

`proxy_mode` field added to `Schema__Agent_Mitmproxy__Info`; `/health/info` surfaces `direct` or `upstream` so operators can verify boot-time config without reading logs.

New test: `test__info__upstream_mode`. New file: `test_env_vars.py` (4 tests).

### P2 — Playwright proxy API cleanup (v0.1.42 service)

Deleted the CDP Fetch workaround (`Proxy__Auth__Binder`) that was needed because Chromium ignores launch-time proxy credentials. The sidecar architecture makes this moot: Playwright sees an unauthenticated local proxy on `:8080`; the sidecar handles upstream auth.

- `Schema__Proxy__Config`, `Schema__Proxy__Auth__Basic` — deleted.
- `Schema__Browser__Config`, `Schema__Browser__Launch__Result` — `proxy` field removed.
- `Browser__Launcher.build_proxy_dict()` — now reads `SG_PLAYWRIGHT__DEFAULT_PROXY_URL` from env (boot-time, not per-request); Chromium/Firefox/WebKit auth branching removed.
- `Sequence__Runner.get_or_create_page()` — reads `SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS` from env; no longer calls `proxy_auth_binder.bind()`.
- Tests: 188 pass (1 skipped, 4 pre-existing Pydantic warnings).

---

## Good failures (surfaced early, informed better design)

**supervisord interpolation crash** — the original `supervisord.conf` used `%(ENV_AGENT_MITMPROXY__PROXY_AUTH_USER)s:%(ENV_AGENT_MITMPROXY__PROXY_AUTH_PASS)s` in the command. When those vars are unset, supervisord refuses to parse the config entirely. Caught during design review before any image was built. The wrapper-script pattern (`entrypoint.sh` writes `/tmp/run_mitmweb.sh`, supervisord calls it) is the standard fix.

---

## Bad failures

None this slice.

---

## Deferred

- **P3:** `docker compose` for local dev (Playwright + sidecar + shared network).
- **P4–P6:** NLB+ASG IaC, AMI publishing, Fluent-bit log shipping.
- **Reality doc version bump:** The `v0.1.31/` folder is updated in-place; a proper version-stamped split (e.g. `v0.1.33/`) is deferred to the Librarian.
