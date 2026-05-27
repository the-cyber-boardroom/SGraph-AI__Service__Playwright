---
title: "Dev Brief — Port the vault-app TLS-for-IP workflow to the sg Firefox spec"
file: firefox-ssl-ip-support__plan.md
author: Dev (Claude)
date: 2026-05-27 (UTC hour 08)
repo: SGraph-AI__Service__Playwright @ claude/firefox-ssl-ip-support-lRKEI (v0.2.41 line)
status: PLAN — design only, no production code changed. For human ratification before Dev implements.
role: Dev
parent:
  - sg_compute_specs/vault_app/service/Vault_App__Compose__Template.py
  - sg_compute_specs/firefox/service/Firefox__User_Data__Builder.py
  - sg_compute/platforms/tls/cert_init.py
---

# Dev Brief — Port the vault-app TLS-for-IP workflow to the sg Firefox spec

> **Everything in section 4 (Proposed design) is PROPOSED — does not exist yet.**
> Sections 1–3 describe code that exists today (verified file:line). The whole TLS-for-IP
> workflow is undocumented in the reality doc; this brief proposes both the code and the
> reality-doc entries.

---

## 1. Grounding — what exists today

### 1.1 Reality-doc status

The SG/Compute reality domain (`team/roles/librarian/reality/sg-compute/index.md`) is the
canonical inventory for both specs. As of v0.2.41:

- **The vault-app TLS-for-IP / cert-init workflow is NOT documented in the reality doc.**
  A grep across `team/roles/librarian/reality/` for `tls_mode`, `cert-init`, `letsencrypt`,
  `self-signed` returns only incidental hits (the vnc spec's nginx :443 terminator in the
  `_archive/v0.1.31/` freeze, and `SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS` in the playwright-service
  domain). `verified-by.md:16` mentions "vault-app TLS" was *seen* in the 05/17 research pass but
  it was never written into a domain `index.md`. **Per CLAUDE.md rule 1, the cert-init workflow
  technically "does not exist" in the canonical record — but the code is real (section 2).** This
  brief therefore proposes a reality-doc update as part of the work (section 4.7).
- **The Firefox spec is documented** under `sg-compute/index.md` (FV2.6 UI migration, the
  2026-05-05 "Firefox credentials + mitm-script routes" changelog entry) and
  `primitives.md:77` (`Enum__Stack__Type.FIREFOX`). None of those entries mention TLS, certs,
  or `tls_mode`. **Firefox has no cert-init / tls_mode path today.**

Net: the reality doc confirms Firefox has no IP-cert feature, and does not (yet) describe the
vault-app cert-init mechanism we are porting. Both gaps are addressed below.

### 1.2 vault-app TLS pieces that EXIST (verified)

| Piece | File:line | What it is |
|-------|-----------|------------|
| `tls_mode` field | `sg_compute_specs/vault_app/schemas/Schema__Vault_App__Create__Request.py:28` | `str` default `'letsencrypt-ip'`; also `with_tls_check`, `acme_prod`, `tls_hostname`, `with_aws_dns` |
| `tls_hostname` / `tls_enabled` | `sg_compute_specs/vault_app/schemas/Schema__Vault_App__Info.py:25-26` | `tls_hostname` is `''` for IP-cert / self-signed |
| cert-init sidecar | `sg_compute_specs/vault_app/service/Vault_App__Compose__Template.py:140-161` (`_CERT_INIT`) | one-shot compose service, `command: python3 -m sg_compute.platforms.tls.cert_init`, binds `:80`, writes `/certs`, `restart: "no"` |
| TLS vault variant | `Vault_App__Compose__Template.py:72-94` (`_SG_SEND_VAULT_TLS`) | `depends_on: cert-init: service_completed_successfully`; mounts `certs:/certs:ro`; sets `FAST_API__TLS__*` |
| `IGNORE_HTTPS_ERRORS` | `Vault_App__Compose__Template.py:106` | set on the sg-playwright service when in the 4-container shape |
| `.env` bake + whitelist guard | `sg_compute_specs/vault_app/service/Vault_App__User_Data__Builder.py:105-118` | emits `SG__CERT_INIT__MODE` / `ACME_PROD` / `TLS_HOSTNAME`; falls back to `self-signed` if mode not in the allowed set |
| cert-init entrypoint | `sg_compute/platforms/tls/cert_init.py` | three modes; IMDS public-IP lookup; ACME http-01 on :80; stage file for observability |
| IP-SAN cert issuance | `sg_compute/platforms/tls/Cert__ACME__Client.py:54-61` | `make_csr(..., ipaddrs=[...])` + `'shortlived'` profile (LE IP certs, GA Jan 2026) |
| self-signed IP-SAN | `sg_compute/platforms/tls/Cert__Generator.py:26-30` | IP literal → `x509.IPAddress` SAN, so `https://<ip>` validates against the SAN |
| mode enum | `sg_compute/platforms/tls/Enum__Cert__Mode.py` | `SELF_SIGNED` / `LETSENCRYPT_IP` / `LETSENCRYPT_HOSTNAME` |
| CLI flags | `sg_compute_specs/vault_app/cli/Cli__Vault_App.py:276-302` | `--tls-mode`, `--with-tls-check`, `--acme-prod`, `--tls-hostname`, `--with-aws-dns`; auto-bump logic at `:170-179`; `cert-renew` command at `:707` |
| reference compose | `sg_compute_specs/vault_app/docker/compose/docker-compose.yml` | rendered output, committed as a fixture |

### 1.3 Firefox pieces that are MISSING (verified)

| Concern | State today | File:line |
|---------|-------------|-----------|
| `tls_mode` / cert flags in create request | **absent** | `sg_compute_specs/firefox/schemas/Schema__Firefox__Stack__Create__Request.py:14-25` — only `stack_name/region/caller_ip/from_ami/instance_type/password/interceptor/env_source/allowed_cidr/max_hours/enable_shell` |
| cert-init sidecar | **absent** | `Firefox__User_Data__Builder.py:33-71` (`COMPOSE_TEMPLATE`) has only `firefox` + `mitmproxy` services |
| `tls_mode` bake into `.env` | **absent** | `Firefox__User_Data__Builder.py` writes only the mitmproxy env (interceptor) to `/run/sg-firefox/env` |
| TLS-mode fields on Info | **absent** | `Schema__Firefox__Stack__Info.py:14-28` — no `tls_enabled` / `tls_mode` / `tls_hostname` |
| CLI cert flags | **absent** | `Cli__Firefox.py:64-89` (`create`) — no `--tls-mode` etc. |
| `Firefox__Compose__Template.py` | **does NOT exist** | Firefox renders its compose *inline* — see section 3.1 |

### 1.4 Important runtime difference confirmed up front

`Firefox__User_Data__Builder` does **not** use a separate `Compose__Template` class (unlike
vault-app). The compose YAML is an inline `COMPOSE_TEMPLATE` string constant inside the
builder (`Firefox__User_Data__Builder.py:33`), `.format()`-substituted in `render()`. There is
no `docker compose --env-file`; instead env is written to a tmpfs file `/run/sg-firefox/env`
(`:119-123`) that only the **mitmproxy** service reads via `env_file:`. The firefox service
gets its config via literal `environment:` keys (including `SECURE_CONNECTION: "1"`).

---

## 2. The vault-app technique, distilled (end-to-end)

The vault-app solves "serve a browser-trusted HTTPS endpoint on a bare EC2 public IP with no
DNS name" with a **one-shot cert sidecar + a shared cert volume + a depends_on gate**. The flow:

1. **Request** — `sg va create` defaults `with_tls_check=True`, `tls_mode='letsencrypt-ip'`,
   `acme_prod=True` (`Schema__Vault_App__Create__Request.py:27-29`).
2. **Service → user-data** — `Vault_App__Service.create_stack` opens `:443` world-open
   (LE validates from unpredictable IPs), tags `StackTLS=true`, and calls
   `Vault_App__User_Data__Builder.render(...)`.
3. **`.env` bake** — the builder whitelist-guards `tls_mode` (falls back to `self-signed` if
   not in the allowed set) and writes `SG__CERT_INIT__MODE` + `SG__CERT_INIT__ACME_PROD`
   (+ `TLS_HOSTNAME` in hostname mode) into `/opt/vault-app/.env`
   (`Vault_App__User_Data__Builder.py:106-112`).
4. **Compose render** — `Vault_App__Compose__Template.render(with_tls_check=True)` emits:
   - a `cert-init` service: image = the host-control Docker Hub image (carries
     `sg_compute.platforms.tls.cert_init`), `command: python3 -m sg_compute.platforms.tls.cert_init`,
     publishes `:80` (ACME http-01 challenge), mounts a named `certs` volume + the
     `/var/lib/sg-compute` host dir (stage file), `restart: "no"`.
   - the `sg-send-vault` service rewritten to bind `:443`, mount `certs:/certs:ro`, set
     `FAST_API__TLS__{ENABLED,CERT_FILE,KEY_FILE,PORT}`, and **gate** itself behind
     `depends_on: cert-init: { condition: service_completed_successfully }`.
   - a top-level `volumes: { certs: }`.
5. **Sidecar runs** — on boot, `cert_init.main()` reads `SG__CERT_INIT__MODE`:
   - `self-signed` → `Cert__Generator.generate_to_files()` (IP literal becomes an IPAddress SAN).
   - `letsencrypt-ip` → `Cert__ACME__Client.issue(ip=...)` with the `'shortlived'` profile;
     http-01 challenge served on :80 by `ACME__Challenge__Server`.
   - writes `/certs/cert.pem` + `/certs/key.pem`, records stages to
     `/var/lib/sg-compute/cert-init.stage`, exits 0.
6. **App reads cert** — because the vault `depends_on` cert-init's
   `service_completed_successfully`, it only starts once the cert exists; it reads
   `/certs/{cert,key}.pem` and terminates its own TLS on :443. A failed issuance means the
   vault never starts (fail-loud, not silent plain-HTTP).
7. **IGNORE_HTTPS_ERRORS** — only relevant in the 4-container shape: the co-located
   sg-playwright is told to ignore HTTPS errors so it can browse to the self-signed/IP-cert
   vault over the docker network.

Key property: **the app terminates its own TLS.** The sidecar only *produces cert files*; it
does not proxy traffic. That is the crux of the Firefox gap (section 3).

---

## 3. Gap analysis for Firefox — the real integration point

### 3.1 How Firefox terminates TLS today

The firefox service runs `jlesage/firefox` with `SECURE_CONNECTION: "1"`
(`Firefox__User_Data__Builder.py:43`). In that image, the web UI is noVNC served by an
internal nginx-equivalent on container port **5800**; `SECURE_CONNECTION=1` makes that
listener speak **HTTPS using a self-signed cert the image generates at first boot**. The
compose publishes container `5800` on host `443` (`VIEWER_PORT=443`,
`VIEWER_CONTAINER_PORT=5800`, `:38-39`), and `Firefox__Stack__Mapper` builds
`viewer_url = https://{ip}/` (`Firefox__Stack__Mapper.py:64`).

So **Firefox already serves HTTPS on :443 — but with the image's own throwaway self-signed
cert.** A browser hitting `https://<ip>/` gets a cert warning. There is **no reverse proxy**
in the Firefox stack today (unlike the vnc spec, which fronts chromium with an nginx :443
terminator — `_archive/v0.1.31/06__*.md:181`). mitmproxy is a *forward* proxy for the
browser's own egress (`user.js` points Firefox at `mitmproxy:8080`), unrelated to the inbound
:443 listener and not a TLS terminator for it.

### 3.2 The real integration point

The vault-app pattern assumes **the app can be told to read an externally-provided cert file**
(`FAST_API__TLS__CERT_FILE`). `jlesage/firefox` does NOT expose a FastAPI-style
"read this cert" env var the way `sg-send-vault` does. The image's noVNC TLS uses a cert at a
fixed in-container path. So there are **two viable integration shapes**, and the human must
pick (section 6, Q1):

- **Option A — cert-init + bind the cert into the firefox container (no new proxy).**
  Run the same one-shot `cert-init` sidecar to write `/certs/{cert,key}.pem` to a shared
  volume, then bind-mount that cert over the path `jlesage/firefox` reads for its
  `SECURE_CONNECTION` listener (the image documents `/config/certs/` — needs a live verify,
  Q2). Smallest change; keeps the 2-service shape; firefox still terminates TLS itself, just
  with *our* cert. **Recommended default.**
- **Option B — cert-init + an nginx :443 terminator in front (mirror the vnc spec).**
  Add nginx as a third service that owns :443, terminates TLS with `/certs/cert.pem`, and
  reverse-proxies to `firefox:5800` (downgrade firefox to `SECURE_CONNECTION: "0"` on an
  internal port). More moving parts but it is a proven in-repo pattern (vnc) and fully
  decouples us from jlesage internals. Use this if Option A's cert path is unstable across
  image versions.

Both options reuse `cert_init.py`, `Cert__ACME__Client`, `Cert__Generator`,
`Enum__Cert__Mode`, and the `depends_on: service_completed_successfully` gate **unchanged**.
The vault-app technique maps cleanly at the *cert-production* layer; the only adaptation is the
*cert-consumption* layer, because Firefox is not a FastAPI app we control.

### 3.3 Probe / SG mismatch to fix in passing (good-failure catch)

`Firefox__HTTP__Probe.firefox_ready` probes `https://<ip>:5800/`
(`Firefox__HTTP__Probe.py:14,26`) but the SG only opens **:443** and the compose publishes
**:443** (`Firefox__SG__Helper.py:13,43`). Today the external health probe targets a port the
SG never opens — it works only from inside the host or is effectively a no-op externally. When
we touch this area we should align the probe to `:443` (the published port). It already uses
`ssl.CERT_NONE`, which is correct and stays correct for self-signed/IP-cert. Flag this as a
**good failure** in the debrief.

---

## 4. Proposed design (all PROPOSED — does not exist yet)

Reuse, don't re-implement: the entire `sg_compute/platforms/tls/` package (cert_init,
Cert__ACME__Client, Cert__Generator, Enum__Cert__Mode, ACME__Challenge__Server) is
spec-agnostic and is reused as-is. The cert-init container image must carry that module — the
vault-app uses `diniscruz/sg-host-control`; the Firefox stack needs the same image available
(section 6, Q3).

### 4.1 New enum (one class per file)

**`sg_compute_specs/firefox/enums/Enum__Firefox__TLS__Mode.py`** — PROPOSED

```python
from enum import Enum

class Enum__Firefox__TLS__Mode(Enum):                 # mirrors Enum__Cert__Mode values
    SELF_SIGNED          = 'self-signed'              # offline; replaces jlesage throwaway cert
    LETSENCRYPT_IP       = 'letsencrypt-ip'           # LE IP-SAN cert, http-01 on :80
    LETSENCRYPT_HOSTNAME = 'letsencrypt-hostname'     # LE DNS-SAN cert (future / parity)
```

> Rationale (CLAUDE.md rule 3 — No Literals): the create request must not carry a raw
> `tls_mode: str`. vault-app predates strict typing and uses a raw `str` with a runtime
> whitelist; Firefox is already typed (`Safe_Str__*` fields) so we go straight to an enum.
> The enum *values* match `Enum__Cert__Mode` / cert-init env strings exactly so no translation
> layer is needed when baking the `.env`.

### 4.2 Changed schema — create request

**`sg_compute_specs/firefox/schemas/Schema__Firefox__Stack__Create__Request.py`** — ADD fields:

```python
from sg_compute_specs.firefox.enums.Enum__Firefox__TLS__Mode import Enum__Firefox__TLS__Mode

    with_tls_cert : bool                     = False                              # opt-in; default keeps today's jlesage self-signed behaviour
    tls_mode      : Enum__Firefox__TLS__Mode = Enum__Firefox__TLS__Mode.LETSENCRYPT_IP
    acme_prod     : bool                     = True                               # LE prod directory when letsencrypt-*
    tls_hostname  : Safe_Str__Text           = ''                                 # only for letsencrypt-hostname (parity; not the focus of this task)
```

> Note the inverted default vs vault-app: vault-app defaults TLS **on**; Firefox defaults TLS
> **off** (`with_tls_cert=False`) so existing behaviour is unchanged and the feature is purely
> additive (test-friendly, no regression to the FV2.6 / credentials work). Decision for the
> human — Q4.

### 4.3 Changed schema — info

**`sg_compute_specs/firefox/schemas/Schema__Firefox__Stack__Info.py`** — ADD:

```python
    tls_enabled  : bool          = False                       # from a StackTLS tag
    tls_mode     : Safe_Str__Text = ''                         # the cert-init mode actually baked
    tls_hostname : Safe_Str__Text = ''                         # '' for IP-cert / self-signed
```

`Firefox__Stack__Mapper.to_info` reads these from new tags (mirror
`Vault_App__Stack__Mapper`'s `TAG_TLS_ENABLED` / `TAG_TLS_HOSTNAME`). `viewer_url` stays
`https://{ip}/` regardless of mode (it is already HTTPS today).

### 4.4 Changed service builder — user-data

**`sg_compute_specs/firefox/service/Firefox__User_Data__Builder.py`** — the core change.

- Add a `_CERT_INIT` compose fragment (copy `Vault_App__Compose__Template._CERT_INIT`
  verbatim, including `command: python3 -m sg_compute.platforms.tls.cert_init`, `:80` publish,
  `certs` + `/var/lib/sg-compute` volumes, `restart: "no"`).
- Add a `certs:` named volume and a `volumes:` top-level block, emitted only when TLS is on.
- **Option A** firefox service edit: when `with_tls_cert`, add `- certs:/config/certs:ro`
  (path per Q2) to the firefox `volumes:` and add
  `depends_on: cert-init: { condition: service_completed_successfully }`.
  **Option B**: add an nginx service owning `:443`, set firefox to `SECURE_CONNECTION: "0"` on
  an internal port, and gate nginx behind cert-init.
- Bake the cert-init env into the boot script. Firefox writes per-service env files; the
  cleanest fit is to either (a) extend the tmpfs env write so cert-init gets an `env_file`, or
  (b) add literal `environment:` keys to the cert-init service block and substitute them in
  `render()`. Emit `SG__CERT_INIT__MODE={tls_mode.value}`,
  `SG__CERT_INIT__ACME_PROD={'true'|'false'}`, and (hostname mode only)
  `SG__CERT_INIT__TLS_HOSTNAME=...`. No whitelist guard needed — the enum already constrains
  the value (this is the typing win over vault-app).
- New `render(...)` kwargs: `with_tls_cert: bool = False`, `tls_mode: str = 'self-signed'`,
  `acme_prod: bool = False`, `tls_hostname: str = ''`.
- Extend the `PLACEHOLDERS` tuple + templates so the locked-placeholder test
  (`test_Firefox__User_Data__Builder.py:31-41`) still passes (the test asserts the tuple
  exactly — update both).

> Consider extracting the inline compose into a `Firefox__Compose__Template` class to mirror
> vault-app and keep `render()` readable. This is optional but recommended; if extracted it is
> a new one-class-per-file `service/Firefox__Compose__Template.py`. Flag as Q5.

### 4.5 Changed service — orchestrator + SG

**`sg_compute_specs/firefox/service/Firefox__Service.py`** — thread the new request fields into
`user_data_builder.render(...)` (`Firefox__Service.py:74-81`), and add the `StackTLS` /
`StackTLSHostname` tags via `Firefox__Tags__Builder`. `:443` is already opened by
`Firefox__SG__Helper`, but **letsencrypt-ip mode needs :443 world-open** (LE validates the
http-01 challenge on :80 *and* clients connect on :443 from unpredictable IPs) — vault-app
opens :443 to `0.0.0.0/0` for TLS stacks (`Vault_App__Service.py:123-124`). Firefox today
scopes :443 to the caller CIDR (`Firefox__SG__Helper.py:43`). For `letsencrypt-ip` the SG must
**also open :80** (http-01) and widen :443. Add an `extra_cidrs`-style branch to
`Firefox__SG__Helper.ensure_security_group` gated on `with_tls_cert` + mode. This is a real
behavioural change and a security-review point — see Q6.

### 4.6 Changed CLI

**`sg_compute_specs/firefox/cli/Cli__Firefox.py`** `create` — add typer options mirroring
vault-app's: `--with-tls-cert/--no-with-tls-cert`, `--tls-mode`, `--acme-prod/--no-acme-prod`,
`--tls-hostname`. Map the `--tls-mode` string onto `Enum__Firefox__TLS__Mode` and set it on the
request. (Firefox's CLI is hand-rolled typer, not `Spec__CLI__Builder`, so this is a direct
option add — no builder plumbing.) Optionally add a `cert-renew` command later (out of scope
for the first slice; note as follow-up).

### 4.7 Reality-doc updates (Librarian handoff)

Because the cert-init workflow is undocumented (section 1.1), the implementing commit must:

- Add a "Firefox TLS-for-IP" subsection to `team/roles/librarian/reality/sg-compute/specs.md`
  (or `index.md`) listing the new enum / fields / sidecar.
- Add a cross-cutting "TLS / cert-init" entry documenting `sg_compute/platforms/tls/` and the
  vault-app cert-init sidecar as the shared mechanism (it should have existed already).
- Append a `changelog.md` pointer line.

---

## 5. Test strategy (no mocks, no patches — per v3.1.1 guidance)

Everything here is pure-render or schema assertion — no AWS, no network, in-sandbox-runnable.

1. **`test_Enum__Firefox__TLS__Mode`** — assert the three members and that their `.value`
   strings equal the cert-init env strings (`self-signed` / `letsencrypt-ip` /
   `letsencrypt-hostname`) so the bake needs no translation.
2. **`test_Schema__Firefox__Stack__Create__Request`** (extend) — default `with_tls_cert is
   False`; default `tls_mode is Enum__Firefox__TLS__Mode.LETSENCRYPT_IP`; assigning a string
   auto-converts to the enum (Type_Safe behaviour); `.json()` round-trips.
3. **`test_Firefox__User_Data__Builder`** (extend) — the meat:
   - With `with_tls_cert=False` (default): rendered user-data is **byte-identical** to today
     (no `cert-init`, no `certs:` volume) — locks "purely additive".
   - With `with_tls_cert=True, tls_mode='letsencrypt-ip', acme_prod=True`: rendered text
     contains `cert-init`, `python3 -m sg_compute.platforms.tls.cert_init`,
     `SG__CERT_INIT__MODE=letsencrypt-ip`, `SG__CERT_INIT__ACME_PROD=true`, the `certs:` volume,
     a `service_completed_successfully` gate, and `:80` published.
   - `tls_mode='self-signed'` → `SG__CERT_INIT__MODE=self-signed` and **no** `:80`/ACME hints
     needed (still harmless if published — match vault-app's choice).
   - Update the `PLACEHOLDERS` lock test to the new tuple.
4. **`test_Firefox__Stack__Mapper`** (extend) — a describe-instances dict carrying
   `StackTLS=true` + `StackTLSHostname=` maps to `tls_enabled=True`, `tls_hostname=''`;
   `viewer_url` stays `https://{ip}/`.
5. **`test_Firefox__SG__Helper`** (new or extend) — with TLS + letsencrypt-ip, the authorized
   ingress includes :80 and :443 (assert on the `IpPermissions` passed to the fake ec2 client
   seam — `ec2_client` is already a test seam, `Firefox__SG__Helper.py:18`). No real AWS.
6. **Reference compose fixture** — render the TLS user-data once and commit the rendered compose
   under `sg_compute_specs/firefox/docker/compose/` (mirror vault-app's committed
   `docker-compose.yml`) so drift is caught by a fixture-comparison test.
7. **Live-only (deferred, gated):** the actual LE issuance / browser-trust check cannot run
   in-sandbox (same constraint noted in `Cert__ACME__Client.py:16-18`). Gate any such test on a
   real-AWS marker and skip cleanly when absent — deploy-via-pytest, numbered, run top-down.

Assert on **contracts** (rendered strings, schema fields, the IpPermissions argument), never on
private methods.

---

## 6. Open questions / risks for the human

- **Q1 — Option A vs Option B (the central decision).** Bind our cert into the
  `jlesage/firefox` `SECURE_CONNECTION` listener (Option A, smallest), or add an nginx :443
  terminator in front and downgrade firefox to plain HTTP internally (Option B, mirrors the vnc
  spec, more robust)? This brief recommends **A** as the default with **B** as the fallback if
  the jlesage cert path proves unstable.
- **Q2 — jlesage cert path.** Option A needs the exact in-container path / filenames the
  `jlesage/firefox` image reads its `SECURE_CONNECTION` cert+key from (the image documents
  `/config/certs/` but the filenames and whether it regenerates on mismatch need a live verify
  against `v1.18`-era tags). If the image only self-generates and ignores a mounted cert, Option
  A is dead and we must use Option B.
- **Q3 — cert-init image for the Firefox stack.** vault-app's cert-init runs
  `diniscruz/sg-host-control` (carries `sg_compute.platforms.tls.cert_init`). The Firefox stack
  pulls only `jlesage/firefox` + `mitmproxy/mitmproxy` today. Do we reuse
  `diniscruz/sg-host-control` as the cert-init image (one more Docker Hub pull at boot), or
  publish a smaller dedicated cert-init image? Reusing sg-host-control is the least work.
- **Q4 — default on or off?** vault-app defaults `with_tls_check=True`. This brief proposes
  Firefox default **off** (`with_tls_cert=False`) to stay purely additive. Confirm — if the
  intent is "Firefox should be browser-trusted by default", flip the default and accept the
  larger blast radius on existing tests.
- **Q5 — extract `Firefox__Compose__Template`?** The inline `COMPOSE_TEMPLATE` will get
  unwieldy with a conditional cert-init service + volumes. Extracting a
  `Firefox__Compose__Template` class (mirroring vault-app) is cleaner but is a wider refactor of
  a file the credentials/mitm-script work depends on. Refactor now or keep inline?
- **Q6 — SG widening for letsencrypt-ip.** LE http-01 needs :80 open to the world and :443
  reachable from LE's unpredictable validation IPs. That widens the Firefox SG from
  caller-CIDR-only to world-open on those ports while a cert is being issued (vault-app accepts
  this). The noVNC UI is still password-gated (`WEB_AUTHENTICATION=1`), but this is a
  security-domain change — confirm acceptable, and whether :80 should be closed again after
  issuance (vault-app leaves it; cert-init exits so nothing listens).
- **Q7 — hostname mode scope.** This task is about the **IP** cert. `letsencrypt-hostname` is
  included for enum parity but needs the `--with-aws-dns` Route 53 machinery vault-app has
  (`Vault_App__Auto_DNS`) which Firefox lacks. Recommend shipping IP + self-signed first and
  deferring hostname mode to a follow-up slice.
- **Risk — IP-cert validity.** LE IP certs use the `'shortlived'` profile (~6-day validity,
  `Cert__ACME__Client.py:8`). Ephemeral Firefox stacks are short-lived (default `max_hours=1`),
  so no renewal is needed — but document it so nobody is surprised by a 6-day stack with an
  expired cert. A `cert-renew`-style command (vault-app has one) is the follow-up if long-lived
  Firefox stacks become a thing.
