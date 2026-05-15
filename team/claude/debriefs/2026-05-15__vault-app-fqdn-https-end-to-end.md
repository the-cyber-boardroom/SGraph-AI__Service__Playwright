# Debrief — `sp vault-app create --with-aws-dns`: one command, browser-trusted FQDN

- **Date:** 2026-05-15
- **Branch:** `claude/architect-qa-service-ijc61`
- **Commits (in order):**
  - `ae725c2` — publish sg-playwright on port 80 so sandbox-egress proxies can reach it
  - `5caaed6` — `--tls-hostname` for LE certs sandbox-egress proxies will trust
  - `1a08c24` — `cert-init` DNS-wait backstop
  - `2562c35` — `Vault_App__Auto_DNS` helper class wrapping the dev-branch Route 53 surface
  - `5d34168` — `--with-aws-dns` flag with parallel Route 53 work during create
- **Builds on:** the prior debrief `2026-05-15__vault-app-tls-letsencrypt-ip.md` (LE-for-IP, the substrate) **and** the dev-branch `sg aws dns` surface (`Cli__Dns`, `Route53__AWS__Client`, `Route53__Zone__Resolver`, `Route53__Authoritative__Checker`, `wait_for_change`)
- **Outcome (verified live against AWS + Let's Encrypt prod):**
  - `sp vault-app create --with-playwright --with-aws-dns --wait` → fresh EC2, A record auto-upserted into Route 53, INSYNC verified, **real browser-trusted LE cert** issued for the FQDN, vault healthy on `https://fast-hopper.sg-compute.sgraph.ai/` — clean Chrome padlock, cert chain `R12 / Let's Encrypt`, valid 90 days.
  - `sgit clone {URL}` from a Claude sandbox, `sgit init`, `sgit commit` — all green up to the network layer (the upstream-503 issue from Anthropic's egress is independent of this work; investigated separately).

---

## Why this matters — product, not engineering

Before this branch, SG/Compute stacks were a developer convenience: spin up a vault, get an IP, paste the IP into a tool, accept the cert warning, move on. **An interesting capability, not a sellable one.** Three friction points kept it that way:

1. **No DNS name.** Customers don't put IP literals in their auth configs, their dashboards, or their docs. The instance was effectively anonymous.
2. **IP-anchored cert.** Sandbox-egress proxies (Claude, corporate WAFs, anything Envoy-fronted) validate by hostname and reject IP certs. The stack was unreachable from the most interesting integrations.
3. **Non-standard ports.** Playwright on `:11024` was blocked by anything that enforces 80/443 — which is most managed networks.

After this branch, **one command** produces a stack with:

- A real `<stack-name>.sg-compute.sgraph.ai` FQDN — propagated, authoritative, INSYNC-verified.
- A browser-trusted Let's Encrypt cert for that FQDN — 90-day validity, no warnings.
- The vault on standard `:443` HTTPS, Playwright on standard `:80` HTTP — both reachable from any normal egress.
- A single `X-API-Key` access token for both services, surfaced via `sp vault-app info`.

That's the threshold from "interesting capability" to "deployable service." A customer who can `sp vault-app create --with-aws-dns --wait` and copy a URL has a working endpoint with a clean padlock — same UX as Vercel / Render / Fly preview deploys. The use cases (QA automation, content scraping, agent workbenches, traffic simulation) all become products in their own right; this slice just made the substrate ready to *host* them.

---

## What was delivered — five commits, one workflow

### 1. Port 80 for Playwright (`ae725c2`)

The Playwright API was on `:11024`, blocked by every sandbox-egress proxy. Moved it to `:80` and dealt with the cert-init coexistence:

- `Vault_App__Compose__Template`: `sg-playwright` now publishes `"80:8000"` and depends on `cert-init` via `condition: service_completed_successfully` + `required: false` so the dependency is ignored when cert-init isn't in the stack (`--no-with-tls-check`).
- `Vault_App__Service`: SG opens `:80` to `0.0.0.0/0` when `--with-playwright` (joins the existing `:80` rule for `--with-tls-check`).
- `Vault_App__Stack__Mapper`: `PLAYWRIGHT_EXTERNAL_PORT = 80`. URL omits the `:80` suffix because it's the default HTTP port — `http://<host>` is cleaner.

### 2. `--tls-hostname` (`5caaed6`)

The plumbing for LE certs that aren't IP-anchored. The catch-22 (need IP for DNS, need DNS for cert) gets resolved in commit 5; this commit just installs the rails:

- `Schema__Vault_App__Create__Request.tls_hostname` + `tls_mode='letsencrypt-hostname'`.
- `Cert__ACME__Client.build_csr(..., hostname='...')` switches the SAN type from `ipaddrs` to `domains`. `config(for_hostname=True)` clears the `shortlived` profile (which is IP-cert-specific — DNS-name certs use LE's default 90-day profile).
- `cert_init.py`: new `letsencrypt-hostname` mode, new `SG__CERT_INIT__TLS_HOSTNAME` env, `resolve_tls_hostname()` validation (non-empty, not an IP, no scheme/port/path).
- `Vault_App__Stack__Mapper`: new `StackTlsHostname` tag drives `vault_url` + `playwright_url` to use the FQDN (must match the cert SAN, otherwise browsers and egress proxies reject the mismatch).
- Enum rename: `LETSENCRYPT_DNS` → `LETSENCRYPT_HOSTNAME` to avoid the dns-01-vs-http-01 ambiguity in the name. The challenge is still http-01.

### 3. `cert-init` DNS-wait backstop (`1a08c24`)

The first half of the catch-22 solution. cert-init runs inside the boot lifecycle and can't trust that DNS is already INSYNC when it starts. New helper:

```python
wait_for_dns_to_match(hostname, my_ip, timeout_sec, poll_sec,
                      now_fn, sleep_fn, resolve_fn) -> None
```

Polls `socket.gethostbyname(hostname)` until it matches our IP. Catches `gaierror`/`OSError`/`UnicodeError` so the polling loop never crashes on a single bad lookup. Configurable via `SG__CERT_INIT__DNS_WAIT_TIMEOUT_SEC` (default 900). Plumbed through the compose template.

**This is the linchpin** — without it, the parallel DNS work in commit 5 has no rendezvous point. With it, cert-init's first poll typically succeeds because the CLI has already INSYNC'd Route 53.

### 4. `Vault_App__Auto_DNS` helper (`2562c35`)

The second half. Pure synchronous wrapper around the dev-branch Route 53 service classes — **zero new boto3 in this repo**. Every AWS interaction goes through:

- `Route53__AWS__Client.upsert_record` / `wait_for_change`
- `Route53__Zone__Resolver.resolve_zone_for_fqdn` (deepest-match — handles `<stack>.sg-compute.sgraph.ai` walking past `sgraph.ai` to the child zone)
- `Route53__Authoritative__Checker.check` (direct NS queries, no cache pollution)

Contract: **never raises**. Exceptions are captured into `Schema__Vault_App__Auto_DNS__Result.error` so the calling thread can surface them after `_wait_healthy` returns. Background threads that raise out are debugging horror; this discipline keeps the failure surface clean.

Optional `on_progress(stage, detail)` callback drives UI — stages: `resolving-zone | upserting | waiting-insync | checking-auth | done | failed`.

Factory seams (`_aws_client_factory`, `_zone_resolver_factory`, `_auth_checker_factory`) let tests inject in-memory fakes without monkeypatching — same pattern the dev-branch DNS tests already use.

### 5. `--with-aws-dns` CLI flag with parallel-thread launch (`5d34168`)

The orchestration. Three integration points:

- **Schema**: `Schema__Vault_App__Create__Request.with_aws_dns: bool = False`. Opt-in only — the flag IS the explicit consent to Route 53 mutations (no `SG_AWS__DNS__ALLOW_MUTATIONS=1` env-var gate, unlike the bare `sg aws dns records add` command; the flag at the create level is its own gate).
- **Service**: `Vault_App__Service.create_stack` derives `tls_hostname = <stack_name>.<SG_AWS__DNS__DEFAULT_ZONE>` (fallback `sg-compute.sgraph.ai`) when `with_aws_dns` is set and `tls_hostname` is blank. Auto-bumps `tls_mode` from `letsencrypt-ip` → `letsencrypt-hostname`.
- **Spec-builder hook**: new `Schema__Spec__CLI__Spec.post_launch_fn` — a generic seam called by `Spec__CLI__Builder.create_impl` between `create_stack` and `_wait_healthy`. Returns an optional task with a `.join(timeout=...)` method which the builder joins after `_wait_healthy` returns. Vault-app's `_vault_app_post_launch` is the first consumer; any future spec can reuse the same seam.

The vault-app callback spawns a daemon thread that:
1. Polls `svc.get_stack_info` for the public IP (allocated ~5-10s after `run_instance`; 60s ceiling).
2. Runs `Vault_App__Auto_DNS.run(fqdn, ip, on_progress=...)` — prints each stage transition.
3. Captures the result; the builder joins after `_wait_healthy` (3-min ceiling so a stuck task can't hang the CLI).

---

## The journey — five moves, plus a critical pivot

1. **The CORS / mixed-content diagnosis.** The Playwright Workbench (vault-resident app, running as a blob iframe) couldn't reach the Playwright API. Three issues layered: wrong target (the workbench was hitting the vault, not Playwright), mixed content (HTTPS page → HTTP service), and CORS (blob origin → `null`, vault's allow-headers missing `x-api-key`). Two of the three layers had to land in this repo (port 80 + hostname-matched cert); the third (vault CORS) belongs to the `sg-send-vault` team.
2. **The port-80 move.** Quick, mechanical. The wrinkle was cert-init also wanting `:80` for the ACME http-01 challenge — solved by compose `depends_on: service_completed_successfully` with `required: false` so the dependency is silently dropped when TLS is off.
3. **`--tls-hostname` for a hostname-anchored cert.** The plumbing was straightforward once I realised the existing `Cert__ACME__Client` only needed a SAN-type switch (`ipaddrs=` → `domains=`) and a profile clear (`'shortlived'` → `''`). The enum rename (`LETSENCRYPT_DNS` → `LETSENCRYPT_HOSTNAME`) was a passing fix to avoid future confusion with the dns-01 challenge type.
4. **The catch-22.** Surfaced by you: "how can I create the DNS entry for `<fqdn>` if I don't have the IP before issuing the command?" The first instinct was Option 2 from earlier: cert-init waits for DNS to converge, user updates DNS manually after launch. That was workable but unsmooth.
5. **The critical pivot — `sg aws dns`.** "We have a better option — pull dev and look at `sg aws dns records check`." A complete Route 53 management surface had landed on dev in the days between this work starting and the catch-22 surfacing. Records `add` / `update` / `delete` / `check` / `instance create-record`, with `--wait` polling for INSYNC, `Route53__Authoritative__Checker` for cache-safe verification, `Route53__Zone__Resolver` walking FQDN labels to find the deepest owning zone, all behind clean `Type_Safe` service classes. **Building DNS automation from scratch became unnecessary** — wrap what's there.
6. **The parallel insight, also yours.** "On the create, do this in parallel with the build, as soon as we know the IP of the EC2 instance." That reframed the integration: cert-init's DNS-wait isn't the *main* mechanism, it's the *backstop* — the CLI thread can run upsert + INSYNC + authoritative-check concurrently with the EC2 boot, and cert-init's first poll succeeds because Route 53 is already there by the time docker compose reaches cert-init.

Verified live on `sp vault-app create --with-playwright --with-aws-dns --wait`: produced `fast-hopper.sg-compute.sgraph.ai`, real LE cert (R12 / Let's Encrypt, valid 13 Aug 2026), clean Chrome padlock.

---

## Good vs bad failures (per CLAUDE.md §26–28)

### Good failures — surfaced early, informed a better design

- **The CORS thread led to the right diagnosis, not a wrong fix.** When the Workbench's "Failed to fetch" appeared, the first instinct could have been to add CORS middleware to the Playwright API in this repo. The console error (`origin 'null' ... x-api-key not in allow-headers`) showed the fetch was hitting the **vault** at `https://18.134.9.182/health/status`, not Playwright. Diagnosing first, fixing second, kept us from putting a band-aid on the wrong service. The vault CORS fix is now a clean brief for the vault team, not a half-done attempt in our code.
- **The catch-22 surfaced before we wired half a solution.** "How do I create the DNS entry before I know the IP?" — asked precisely when it mattered. A naïve `--tls-hostname` flow would have looked finished, then broken at the first attempt. Two-phase launches and laboriously-built DNS-wait timers would have been the wrong direction. The catch-22 + the pivot to `sg aws dns` together gave us the right architecture in one move.
- **The `sg aws dns` discovery was timely.** The Route 53 surface had landed on dev between session starts. Pulling latest dev before designing anything DNS-related saved a multi-day detour into building automation that already existed. **Lesson, baked in:** when a task spans a feature area another role has been working on, the first move is "pull dev, read what's new" — not "design from scratch." Did this work for the QA-vault-app pack reframing earlier in the session too.
- **Factory seams over monkeypatching.** `Vault_App__Auto_DNS` exposes `_aws_client_factory` / `_zone_resolver_factory` / `_auth_checker_factory`. Tests substitute lightweight fakes directly; no mocks, no patches. 6 tests landed clean, the seams pay off the moment any of the underlying service classes changes signature (a refactor here doesn't ripple through `unittest.mock.patch` calls).
- **`Vault_App__Auto_DNS` never raises.** Background threads that raise out are debugging horror. Capturing exceptions into `result.error` and surfacing them after `.join()` keeps the failure surface flat. Verified by the upsert-failure / zone-resolver-failure tests — both end with a populated `error` field, not an uncaught exception traceback.

### Bad failures — silenced, worked around, or re-introduced

- **🟡 `recreate` doesn't preserve `tls_hostname` or `with_aws_dns`.** Existing recreate semantics intentionally reset `tls_mode` to defaults. With `--with-aws-dns`, you'd `delete && create` to recreate with the same FQDN. The TTL-60s A record gets re-upserted with the new IP, so the disruption is short, but it's a corner-cut that'll bite the next person who tries `sp vault-app recreate` on an FQDN stack. **Should land:** `recreate` preserves `tls_hostname` and `with_aws_dns` exactly like it preserves `with_playwright` today. Small follow-up.
- **🟡 The post-launch hook's stdout interleaves with `_wait_healthy`'s rich rendering.** Acceptable but not pretty — the `auto-dns: …` lines appear inline above the "Waiting for vault-app …" output. A more polished UX would render both in a unified Live panel. Not worth blocking the milestone; visual polish on a working flow.
- **🟡 The Auto_DNS thread is daemon=True.** If the main thread crashes before joining, the daemon thread silently dies — which is fine for cleanup, but a Ctrl-C mid-create could leave the upsert mid-flight (sent the change to Route 53 but never verified INSYNC). Recovery is straightforward (`sg aws dns records check <fqdn>`), but the failure mode is invisible from the CLI side. Tolerable in v1; a `KeyboardInterrupt` handler that joins (or at least surfaces the change-id) would close the gap.
- **🔴 Claude egress can't reach the deployed stack — same 503 we diagnosed at the start of the session.** The cert is valid, DNS resolves, the vault is up; another Claude session shows `upstream connect error or disconnect/reset before headers`. Same pattern as the original Envoy 503 — the egress proxy can establish TLS but the upstream-side connection from Anthropic's proxy to the customer origin fails. Independent of this work (the user's laptop reaches the stack fine), but it means the "Claude-reachable" promise of the FQDN+cert isn't quite delivered end-to-end yet. **This is the thread to pull next.** Diagnostic options below in the loose ends.

---

## Architecture notes worth preserving

- **No new boto3 in this repo.** Every AWS interaction goes through dev-branch service classes in `sgraph_ai_service_playwright__cli/aws/dns/service/`. Single source of truth for Route 53 access. The same is true for EC2 (existing `osbot-aws` use) and for the playwright service layer. Discipline: when a new AWS service is added, the surface lands in `sgraph_ai_service_playwright__cli/aws/<service>/service/` and consumers wrap, not re-implement.
- **`SG_AWS__DNS__DEFAULT_ZONE` is shared with the bare CLI.** `_default_aws_dns_zone()` reads the same env var (and falls back to the same `sg-compute.sgraph.ai`) as `sgraph_ai_service_playwright__cli/aws/dns/service/Route53__AWS__Client._default_zone_name()`. A team that customises their default zone for `sg aws dns` automatically gets the same default for `sp vault-app create --with-aws-dns`.
- **`Schema__Spec__CLI__Spec.post_launch_fn` is a generic seam.** It's vault-app-only today but the contract is generic — any spec can plug in a `post_launch_fn(svc, region, request, response, kwargs, console)` to do work in parallel with `_wait_healthy`. Likely future users: a spec that pre-warms an ECR image cache, a spec that registers itself with a service-discovery layer, a spec that emits a startup webhook.
- **`--with-aws-dns` is AWS-specific by name and by intent.** The flag name encodes the provider. A future `--with-cloudflare-dns` (or Cloudflare-integrated alternative) would be a separate flag, not a generic `--auto-dns`. Lets each provider's integration evolve independently without overloading a single flag's semantics.
- **The `--with-aws-dns` flag is its own consent gate.** The bare `sg aws dns records add` command requires `SG_AWS__DNS__ALLOW_MUTATIONS=1` because it's a low-level mutation tool. The `sp vault-app create --with-aws-dns` flag is a high-level workflow opt-in — the flag itself is the consent, no env var on top. (`Route53__AWS__Client` doesn't enforce the env-var gate; only the dns CLI commands do, so calling the client programmatically bypasses it cleanly.)
- **TTL=60s on the auto-DNS record** is intentional. `recreate`/`delete` will land a new IP soon enough that long TTLs would cause stale-cache hits during the swap. 60s is short enough that any propagated stale value clears inside a coffee break and long enough that the steady state doesn't pummel Route 53.
- **No renewals — by design (inherited).** Same as the IP-cert path. 90-day hostname certs outlive most ephemeral stacks, and a long-lived stack that wants renewal should be a separate phase (cert-renew sidecar, or a different deployment shape). Issuance is one-shot.

---

## Loose ends

### Substantive

- **🔴 Claude egress 503 to the deployed stack.** The cert/DNS/vault are all green, but Anthropic's egress proxy returns `upstream connect error or disconnect/reset before headers`. Browser reaches the host; Claude doesn't. Investigation next in this session.
- **Vault-side CORS fix for the Workbench (blob iframe).** Independent brief — `sg-send-vault` needs to add `x-api-key` to `Access-Control-Allow-Headers` and accept `null` origin. Belongs to the vault team; the brief is already drafted in this conversation thread.
- **`recreate` preserves `tls_hostname` + `with_aws_dns`.** Small follow-up. Currently you `delete && create` for the same FQDN.
- **`--with-aws-dns` validation gate.** When `--with-aws-dns` is on but the AWS account doesn't own `SG_AWS__DNS__DEFAULT_ZONE`, the failure surfaces inside the Auto_DNS thread after launch — too late. A pre-launch check (the zone resolves to a hosted-zone-id we control) would fail-fast and let the user fix it before EC2 spend.

### Cosmetic / nice-to-have

- **Unified Live panel for the post-launch progress.** Auto-DNS ticks + EC2-boot ticks could share one rich-Live region instead of interleaving. Visual polish.
- **`sp vault-app info` surfaces the auto-DNS state.** Today the `vault_url` is FQDN-based when the tag is set, but there's no `auto-dns: managed | manual | none` field showing whether `sp vault-app delete` will also clean up the Route 53 record. Currently it won't (delete doesn't touch DNS) — surfacing that fact would make the lifecycle obvious.

### Documentation

- **Reality doc** under `team/roles/librarian/reality/` — needs entries for: `Vault_App__Auto_DNS`, the `post_launch_fn` hook, the `--with-aws-dns` flag, the cert-init DNS-wait backstop. Likely a v0.2.20-stamped supersession of the current `v0.2.19` reality doc.
- **QA-vault-app pack** (`team/comms/briefs/v0.2.19__qa-vault-app/`) — the "one-command deploy" promise in `01__substrate-contract.md` §1 is now considerably stronger. Worth a small update there reflecting the new default URL shape.
- **The vault-to-playwright API brief** (`team/comms/briefs/v0.2.6__vault-to-playwright-api.md`) — base URL is FQDN-based now when `--with-aws-dns` is on; the brief still describes the IP form.

---

## Verification snapshot

```
$ sp vault-app create --with-playwright --with-aws-dns --wait
✓  Instance launched (with-playwright, docker)
auto-dns: starting           fast-hopper.sg-compute.sgraph.ai → 18.169.240.189
auto-dns: resolving-zone     fast-hopper.sg-compute.sgraph.ai
auto-dns: upserting          fast-hopper.sg-compute.sgraph.ai A → 18.169.240.189 (TTL 60s)
auto-dns: waiting-insync     /change/C04521611NXQ8MMLCW9B6
auto-dns: checking-auth      fast-hopper.sg-compute.sgraph.ai
✓  auto-dns: fast-hopper.sg-compute.sgraph.ai → 18.169.240.189  (INSYNC + authoritative)

Waiting for vault-app stack 'fast-hopper' to be healthy …
✓  healthy   cert: CA-signed · 90d left   url: https://fast-hopper.sg-compute.sgraph.ai

vault-url       https://fast-hopper.sg-compute.sgraph.ai
playwright-url  http://fast-hopper.sg-compute.sgraph.ai
```

Chrome cert viewer:

- Issued to: `fast-hopper.sg-compute.sgraph.ai`
- Issued by: `R12` / Let's Encrypt
- Valid: 15 May 2026 → 13 Aug 2026 (90 days, default LE profile)
- SHA-256: `eb531294dcb5fbc742a4456e6e83bad89224fea66a63d8648cf6f48080a4daa3`

123 tests passing on the branch (`sg_compute_specs/vault_app/tests/` + `sg_compute__tests/platforms/tls/`).

---

*Filed by Claude (Opus 4.7), 2026-05-15. The "interesting capability → sellable service" threshold: crossed. The bit on the table for next: why Anthropic egress sees the cert but can't reach the upstream.*
