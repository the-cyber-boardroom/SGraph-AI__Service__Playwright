# Debrief — vault-app TLS, end to end: real Let's Encrypt IP cert by default

- **Date:** 2026-05-15
- **Branch:** `claude/architect-qa-service-ijc61` (also merged onto `dev` as `ded6dc2`)
- **Commits (in order):**
  - `27d5647` — P0 PoC: TLS library + §8.2 launch contract + slim Fast_API__TLS app + cert CLI
  - `288294c` — Fast_API__TLS TestClient suite (py3.12)
  - `1f5ce79` — Vault Dev team brief (the §8.2 contract handoff)
  - `a0944a5` — `cryptography` added to root deps
  - `8aad135` — ACME IP cert wiring + EC2 integration + progress in wait/health
  - `a37b1cc` — host image requirements fix (the bad failure — see below)
  - `8d2d8a8` — `logs --follow` + `cert-init`/`vault` container log sources
  - *(this commit)* — production-ACME default; access-token tag → `info`; HTTPS `vault_url`; help cleanup
- **Source design:** [`team/roles/architect/reviews/05/14/v0.2.6__vault-app-tls-poc-fastapi-sidecar.md`](../../roles/architect/reviews/05/14/v0.2.6__vault-app-tls-poc-fastapi-sidecar.md)
- **Outcome (verified live, prod LE):** `sp vault-app create --wait` → real browser-trusted Let's Encrypt IP certificate on a fresh `t3.medium`, vault UI fully operational over HTTPS with `window.isSecureContext === true`, Web Crypto API available, `✓ Decrypted` in-browser. Clean padlock, zero warning.

---

## What was delivered

The full chain from "vault UI needs Web Crypto" to "browser-trusted HTTPS on a fresh EC2 in one command":

### A reusable TLS library — `sg_compute/platforms/tls/`
- `Cert__Generator` / `Cert__Inspector` / `Schema__Cert__Info` — self-signed gen + decode-from-PEM-or-host.
- `ACME__Challenge__Server` — a ~40-line http-01 challenge file server (real sockets, no mocks).
- `Cert__ACME__Client` — issues real LE IP certs via the `acme` Python library: `make_csr(ipaddrs=[...])` + `new_order(csr, profile='shortlived')` + http-01 + `poll_and_finalize`. Defaults to LE *staging*; `--acme-prod` flips to production.
- `cert_init.py` — the one-shot sidecar entry point. Mode dispatch on `SG__CERT_INIT__MODE`: `self-signed` (offline) or `letsencrypt-ip` (real LE). Fails loud → `depends_on: service_completed_successfully` → vault never starts on a botched cert.

### The §8.2 TLS launch contract — `sg_compute/fast_api/`
- `Fast_API__TLS__Launcher` reads `FAST_API__TLS__{ENABLED,CERT_FILE,KEY_FILE,PORT}`, runs uvicorn plain-HTTP by default (preserves the one-image / five-targets guarantee) or HTTPS on `:443` with `ssl_certfile` / `ssl_keyfile` when enabled. Fail-loud on enabled-but-cert-missing.
- Single-file by intent — destined for upstream OSBot__Fast_API.

### The cross-team handoff
- [`team/comms/briefs/v0.2.6__sg-send-vault-tls-contract.md`](../../comms/briefs/v0.2.6__sg-send-vault-tls-contract.md) — the Vault Dev team adopted the contract; their new `diniscruz/sg-send-vault:latest` honours it natively. **No proxy anywhere in the fleet.**

### CLI surface
- `sp <spec> cert {generate, inspect, show, check}` — a generic per-spec sub-typer (`Spec__CLI__Builder._register_cert`).
- `sp vault-app create --with-tls-check --tls-mode {self-signed,letsencrypt-ip} [--acme-prod]` — threaded through the schema → service → user-data → compose. **Final defaults:** `with_tls_check=True`, `tls_mode='letsencrypt-ip'`, `acme_prod=True` — so `sp vault-app create --wait` produces a browser-trusted cert with zero extra flags.
- `sp vault-app logs -s cert-init [-f]` — surfaces the sidecar's actual stdout/stderr via SSM, with `--follow` ported from `Cli__Local_Claude`. Made debugging the live ACME path tractable.

### Progress visibility in `wait` / `health` (the under-recognised win)
- `Vault_App__Service.health()` is now TLS-aware: probes HTTPS `:443` before HTTP `:8080`, decodes the served cert into `Schema__CLI__Health__Probe.cert_summary` (`cert: CA-signed · 6d left`).
- While booting, a single SSM round-trip surfaces both the boot-stage marker and the cert-init container's status line, so `wait` shows ACME issuance progress live: `cert-init=Up 12s` → `Exited (0)` → `✓ healthy  cert: CA-signed`.

### Info / tag wiring
- New EC2 tags at create time: `StackTLS` (`'true'`/`'false'`) and `AccessToken` (the vault key, same value as the FastAPI API key).
- `Vault_App__Stack__Mapper` reads both; `vault_url` is now `https://<ip>` when `StackTLS=true`, `http://<ip>:8080` otherwise.
- `sp vault-app info` now shows `access-token` (with the `(X-API-Key + x-sgraph-access-token)` hint) and uses the right scheme in the `set-cookie-form` / `browser-auth` rows.

---

## The journey — how we got here

Six rounds, in order:

1. **Architect spec (pre-session, `v0.2.6__vault-app-tls-poc-fastapi-sidecar.md`).** The decisive moment was Q6 (can sg-send-vault terminate its own TLS), resolved in favour of in-app TLS — which killed Caddy and every other proxy notion in one stroke. The architecture from then on was just "every FastAPI app reads the §8.2 contract."
2. **P0 PoC.** Built the TLS library + launcher + a *standalone* slim Fast_API__TLS app on `:443` to prove the secure-context loop end-to-end. The sg-send-vault image still served plain HTTP. The PoC proved the *mechanism*, not yet the real vault.
3. **Brief → Vault team → new image.** The §8.2 contract was handed off as a self-contained brief; the Vault Dev team rebuilt `diniscruz/sg-send-vault:latest` to honour it. Verified locally with `docker run` — green padlock structurally, `window.isSecureContext === true` in devtools.
4. **EC2 integration + ACME.** Wired TLS into the actual `sg-send-vault` compose service (dropped the standalone scaffold), added `cert-init` mode dispatch + `Cert__ACME__Client`, opened `:443`/`:80` world-open in the SG (architect Q7 decision: vault is access-token-gated anyway), and built the cert/sidecar progress visibility into `wait`/`health`.
5. **Bad failure on first deploy (see below).** `cert-init` exited 1 — the host image still lacked `cryptography`. One-line fix, image rebuild, and the very next attempt produced a real Let's Encrypt **staging** cert (`(STAGING) Ersatz Emmer YR2`, ~6d validity = the `shortlived` profile).
6. **Production cut.** `--acme-prod` flipped the directory; same flow, browser-trusted cert; clean padlock; the SG/Vault UI decrypted in-browser at `https://13.40.x.x/en-gb/vault`. **Web Crypto live.**

Final mile (this commit): flipped the defaults so `sp vault-app create --wait` is the one-line on-ramp; surfaced the access token via an EC2 tag → `info`; fixed the `vault_url` scheme.

---

## Good vs bad failures (per CLAUDE.md §26–28)

### Good failures — surfaced early, informed a better design

- **`tls-alpn-01` rejected in favour of `http-01`** (the architect doc preferred the former). `tls-alpn-01` requires a raw TLS server presenting a challenge cert mid-handshake — fiddly and *fundamentally* impossible to verify without LE actually connecting. `http-01` is a ~20-line file server. With `:443` already world-open per Q7, the extra `:80` rule was free. The doc's preference was operational tidiness; mine was implementability + testability. Deliberate, documented deviation.
- **Progress visibility paid off the moment it was needed.** When `cert-init` exited 1 on the first prod attempt, `wait` showed `cert-init=Exited (1) 2 seconds ago` precisely as designed. Diagnosis was trivial — no SSM session, no detective work. Worth more than the time it took to build.
- **Fail-loud / `depends_on: service_completed_successfully`.** A failed ACME run means the vault container never starts. No silent broken state where TLS is "supposed to be on" but the box fell back to HTTP. The system caught its own failure cleanly, three times in a row, while we ironed out the deploy path.
- **LE staging by default for `--tls-mode letsencrypt-ip` *until* this final commit.** Burning prod LE quota on debugging would have been a real own-goal. Staging carried the flow end-to-end before we ever touched prod. Only flipped to `--acme-prod` default once the staging→prod equivalence was proven on the same stack.

### Bad failures — silenced, worked around, or re-introduced

- **🔴 The host image's separate `requirements.txt`.** I added `cryptography` / `acme` / `josepy` to the repo-root `requirements.txt` and `pyproject.toml`. `docker/host-control/Dockerfile` installs from its **own** `docker/host-control/requirements.txt`. The first new dep (`cryptography`) was *never in the host image*, so `cert-init` died at `import cryptography` before any mode logic ran. The user hit it twice — once before the `cryptography` add, once again before I noticed the host requirements file was untouched. **Lesson, baked in:** when adding deps that downstream containers will use, audit *every* requirements file in the repo, not just the root. The `ci__host_control.yml` job's `paths-filter` includes `docker/host-control/requirements.txt`, so a one-line addition there triggers the right image rebuild automatically — using the system as it is built.
- **🟡 `vault_url` hard-coded `http://...:8080` after TLS was wired.** `Vault_App__Stack__Mapper.to_info` kept building the plain-HTTP URL even on a TLS stack, so `sp vault-app info` showed the wrong scheme after a successful TLS deploy. Caught in the final-mile cleanup, not earlier. **Lesson:** when changing what the stack *is*, sweep what the stack *reports*. The renderer-vs-reality drift was avoidable.
- **🟡 The standalone `tls-check` PoC scaffold.** Shipped in P0 as a separate `:443` service to prove secure-context, dropped one slice later when sg-send-vault gained native TLS. Not strictly a bad failure (it was scaffolding by design) but it lived in the compose template for a few days as a slightly-awkward "did this also need a follow-up?" item. Better outcome would have been to label it `_PROBE` from day one to make its temporary nature explicit in the code.

---

## Architecture notes worth preserving

- **No proxy anywhere in the fleet** is now load-bearing. Every FastAPI app (host-plane, sg-send-vault, eventually sg-playwright + agent-mitmproxy) reads the same §8.2 env contract. The shared `Fast_API__TLS__Launcher` is the natural upstream candidate for OSBot__Fast_API — once it lands there, every `Serverless__Fast_API` app inherits it for free.
- **One-shot cert sidecar is the right shape for ACME.** Acquisition runs as a single-purpose process with `:80`/`:443` open *only* during issuance — the moment it exits, the real workload takes the ports. Smaller exposure surface than any long-running proxy.
- **No renewals — by design.** Shortlived IP certs (~6d) outlive no ephemeral stack. If a cert ever expires under a running stack, that's a bug to surface (the auto-terminate timer failed), not a thing to automate around. `Cert__ACME__Client` is issue-only.
- **Two-headers, one-value.** Both `X-API-Key` (the FastAPI gate) and `x-sgraph-access-token` (the vault session) are set to the same auto-generated stack token. Documented in the new sgit CLI brief; surfaced on `sp vault-app info`.
- **Tags as the source-of-truth for "what is this stack?"** `StackTLS`, `StackEngine`, `StackWithPlaywright`, `TerminateAt`, `AccessToken` — `Vault_App__Stack__Mapper.to_info` reads them all into `Schema__Vault_App__Info`. CLI / API / future UI all consume the same shape.

---

## Loose ends

- **Reality doc** under `team/roles/librarian/reality/` — needs an entry for: the `sg_compute/platforms/tls/` library, `Fast_API__TLS__Launcher` (§8.2), `cert` CLI sub-typer, and the `vault-app --with-tls-check` flow as the new default.
- **Architect doc** (`v0.2.6__vault-app-tls-poc-fastapi-sidecar.md`) — its §8 phasing table should mark P0 and P2 ✅; the doc itself is now history, not aspiration.
- **`team/comms/briefs/v0.2.6__sg-send-vault-tls-contract.md`** is delivered — should move to `archive/` with this debrief's closing commit hash per the briefs lifecycle.
- **Upstreaming `Fast_API__TLS__Launcher` to OSBot__Fast_API** — the helper is single-file by intent for exactly this lift; not blocking anything, follow-up for the OSBot release cycle.

---

*Filed by Claude (Opus 4.7), 2026-05-15. The bleeding-edge bit — ACME-for-IP via the `shortlived` profile, only GA at LE in January 2026 — is now verified end-to-end on production Let's Encrypt against a real ephemeral EC2 stack. **Clean padlock.**
