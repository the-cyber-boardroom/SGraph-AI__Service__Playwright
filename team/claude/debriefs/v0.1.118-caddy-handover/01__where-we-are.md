# 01 — Where we are

## Current branch + version

- **Branch:** `claude/refactor-playwright-stack-split-Zo3Ju`
- **Version file:** `sgraph_ai_service_playwright/version` → `v0.1.118` (auto-bumped by CI on merge to `dev`)
- **Test status:** `1998 passed, 1 skipped` on the unit suite (one collection error in `tests/unit/agent_mitmproxy/test_Routes__CA.py` — pre-existing; missing `cryptography` dep — ignore via `--ignore`).

## Recent commits on this branch (last 12, newest first)

```
b9123d1  feat(vnc): swap nginx for caddy + caddy-security (branded login slice 1)
c3466ed  docs(briefs): v0.1.118 — branded login alternatives for sp vnc
a21ea0d  docs(briefs): v0.1.118 — admin UI VNC iframe pane
615cdec  fix(vnc): pin mitmproxy to 10.4.2 to dodge 11.x CSRF/host-rebind 403
0ac8f3b  fix(vnc): probe mitmweb at /flows, not /api/flows
f2d900b  fix(vnc): generate proxyauth as bcrypt htpasswd, not plaintext
d994b7b  fix(vnc): add SELinux :z label to compose bind mounts (AL2023)
9ff7d5b  fix(vnc): chmod 0644 proxyauth + htpasswd so non-root containers can read
1535547  feat(vnc): add --open flag to sp vnc create for public SG ingress
b0c9412  fix(vnc): relax Safe_Str__Vnc__Password — allow any printable ASCII except '
f382365  fix: pass instance_profile_name=playwright-ec2 for vnc/prom/os create_stack
0aa9b4a  chore(tests): drop all __init__.py files from tests/ (PyCharm + pytest conflict)
```

## What works end-to-end RIGHT NOW

### `sp vnc` (verified live on EC2)
- `sp vnc create --password 1234 --wait --open` — provisions an EC2 in eu-west-2, builds Caddy with caddy-security via xcaddy, boots chromium + mitmproxy + caddy.
- `sp vnc list / info / delete / connect / health / wait / flows / interceptors`.
- The `--open` flag widens SG ingress on 443 to `0.0.0.0/0` (justified: behind bcrypt-protected login).
- `sp vnc connect` opens an SSM shell (requires `instance_profile_name=playwright-ec2`, which the IAM profile fix covered).

### Other sp subgroups (smoke-tested via unit suite)
- `sp linux`, `sp docker_stack`, `sp prom`, `sp os`, `sp el`, `sp pw`, `sp catalog`, `sp doctor`.
- All follow the same Tier-1 / Tier-2A / Tier-2B pattern.

### FastAPI surface
- `Fast_API__SP__CLI` exposes routes under `/{section}/...` for each subgroup.
- VNC routes are NOT yet wired into `Fast_API__SP__CLI` (see open thread #4 in `02__open-threads.md`). The Tier-1 service exists; the Tier-2B routes module exists; just not registered.

## Recent debug history (so you don't re-discover these)

When the Caddy work was getting started we burned a few hours debugging a chain
of mitmproxy / nginx issues on the previous nginx setup. All of these are
fixed now, but the **pattern matters**:

1. **EC2 user-data only runs once at boot.** A change to a template file is
   useless on an existing instance — you must `sp vnc delete && sp vnc create`
   to test it.
2. **AL2023 + bind mounts:** non-root containers need `chmod 0644` on bind-
   mounted files (we tried 0600 and broke nginx + mitmproxy). SELinux is
   `Permissive` by default but we still pass `:z` on bind mounts as defensive
   practice.
3. **mitmproxy `--proxyauth=@FILE`** uses `passlib.HtpasswdFile` and rejects
   plaintext — the file MUST be bcrypt-formatted (`htpasswd -bcB`).
4. **mitmproxy 11+ added DNS-rebind protection** that 403s every request to
   the web UI from non-loopback origins. We pinned `mitmproxy:10.4.2`.
5. **The mitmweb REST endpoint is `/flows`, NOT `/api/flows`.**
6. **Caddy `tls internal` works without a hostname** if you use the `:443`
   site label (no host prefix).
7. **First-boot Caddy build** adds ~2-3 min on a t3.large. Subsequent compose
   restarts reuse the cached layer.

## Known regressions introduced by the Caddy swap (acceptable for slice 1)

| Regression | Why | Where it gets fixed |
|---|---|---|
| `flow_count` in `sp vnc health` always reports 0 or `-1` | `/mitmweb/flows` is gated by Caddy auth; probe doesn't carry a JWT cookie | `02__open-threads.md` thread #2 |
| Login page is the default caddy-security styling | Slice 1 was scope-limited to "swap, ship, iterate" | `02__open-threads.md` thread #1 |
| No deploy-via-pytest test that the new caddy build actually succeeds on AL2023 | Manual smoke test only | `02__open-threads.md` thread #3 |
| The handover briefs `v0.1.118__admin-ui-vnc-iframe-pane/` and `v0.1.118__vnc-branded-login/` reference the OLD nginx auth approach in places | Briefs were written before the Caddy swap shipped | Either update or delete; depends on whether the admin-UI team has acted on them |
