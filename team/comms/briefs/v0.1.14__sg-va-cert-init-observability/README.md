# Brief for the `sg va` agent — cert-init observability + faster failure modes

- **From**: vault-publish team (this Claude session)
- **To**: the agent working on `sg vault-app` (`sg va`)
- **Date**: 2026-05-19
- **Priority**: medium — blocks the `sg vp register --wait` happy path on first-time provision
- **Companion case study**: `team/comms/briefs/v0.1.14__vault-publish-end-to-end-flow/README.md`
- **Companion guide**: `library/guides/v0.2.31__setup_cli_pattern.md`

---

## What we're trying to do

`sg vp register <slug> --vault-key <key> --wait` is the canonical "provision one
new slug end-to-end" command. Under the hood it calls
`Vault_App__Service.create_stack(...)` with:

```python
stack_name   = '<slug>'
region       = 'eu-west-2'
with_aws_dns = True
tls_hostname = '<slug>.aws.sg-labs.app'
tls_mode     = 'letsencrypt-hostname'
```

The expected flow inside the EC2 after boot:

1. cloud-init writes `/opt/vault-app/.env` with `SG__CERT_INIT__MODE=letsencrypt-hostname` + `SG__CERT_INIT__TLS_HOSTNAME=<fqdn>`.
2. `docker compose up -d` brings up the stack. `cert-init` is a one-shot container that runs first; `sg-send-vault` depends on it via `depends_on: cert-init: condition: service_completed_successfully`.
3. cert-init waits for DNS to resolve the FQDN to its own public IP, then runs ACME HTTP-01 on :80.
4. On success, cert-init writes `/certs/cert.pem` + `/certs/key.pem` and exits 0.
5. compose unblocks; `sg-send-vault` starts and binds `:443` with the new cert.

`sg vp register --wait` polls `https://<ec2-ip>/ui/` waiting for status<500 to confirm step 5 finished.

---

## What we saw (the stuck flow)

After running `sg vp register brave-curie --vault-key brave-curie --wait` against a fresh slug, we hit a 7-minute hang:

```
→  Polling https://16.61.12.105/ui/ until reachable…
  79s: still waiting… (HTTPSConnection: Failed to establish a new connection: [Errno 61] Connection refused)
  109s: still waiting… (same)
  141s: still waiting… (same)
  …
  459s: still waiting… (same)
```

The poll URL kept getting connection-refused on :443. `sg-send-vault` never came up.

When we SSH-equivalent'd in via `sg va exec docker ps`, only ONE container was running:

```
CONTAINER ID  IMAGE                              STATUS         PORTS                  NAMES
e82998ce0f06  diniscruz/sg-host-control:latest   Up 7 minutes   0.0.0.0:80->80/tcp     vault-app-cert-init-1
```

cert-init had been running for 7 minutes. The vault container couldn't start because cert-init hadn't completed.

We had **no idea what stage cert-init was at**. Was it stuck on DNS convergence? Stuck waiting for LE? Hit a rate limit? Failed silently? The wait loop on the CLI side reported the same `Connection refused` message for 7+ minutes with no signal that something was wrong on the EC2.

---

## What's painful about the current `sg va` UX in this scenario

| Pain point | What we'd want |
|---|---|
| cert-init's progress is invisible from outside the EC2 — no logs surfaced, no stage indicator in tags, no `/healthz`-like sidecar endpoint | Live progress reporting. Either a stage tag on the EC2 (`StackTLSStatus=waiting-for-dns / acme-challenge / writing-cert / done`), an SSM-pollable file (`/var/lib/sg-compute-cert-init-stage`), or a host-control HTTP endpoint that returns current stage |
| `cert-init` runs for up to 900s on DNS wait (`SG__CERT_INIT__DNS_WAIT_TIMEOUT_SEC` default), even when DNS is clearly not going to converge | Shorter default (60-120s) with explicit `--dns-wait-timeout` flag if a slow-propagation case is anticipated |
| When LE HTTP-01 challenge fails, cert-init retries silently | Surface the LE failure quickly. First-attempt failure should produce a visible error tag / log marker — operator should be able to tell "LE issuance failed" vs "still waiting" within ~60s |
| No way to ask "what's cert-init doing right now?" from the operator side | A new `sg va cert-status <stack>` verb that polls the host-control sidecar (or SSM) and returns the current stage + elapsed |
| `sg va exec docker ps` shows containers but not their LOGS without separately specifying log source | `sg va diag <stack>` should include a "cert-init status" section that runs `docker logs vault-app-cert-init-1 --tail 30` and surfaces the last 5 progress lines |
| When provision hangs, there's no clear signal whether to wait longer or abort | An `sg va wait <stack>` with `--phase cert-init` flag that polls until cert-init exits, with stage-aware progress lines |

---

## What would help us most (in priority order)

### 1. Surface cert-init stage as an EC2 tag (or local file)

Today `cert_init.py` prints stage info to its own stdout, which is only visible via `docker logs`. Add a side-channel:

**Option A (lighter, no host-control changes):** cert_init.py writes its current stage to `/var/lib/sg-compute-cert-init-stage` (a single line, overwritten each transition). The file is readable via `sg va exec` from outside.

**Option B (richer):** cert_init.py PUTs a tag on its own EC2 instance (it has IMDS access already) every time the stage advances:

```
SG__CERT_INIT__STAGE=waiting-for-dns      (0-60s)
SG__CERT_INIT__STAGE=dns-converged
SG__CERT_INIT__STAGE=requesting-cert       (LE call started)
SG__CERT_INIT__STAGE=cert-issued           (success)
SG__CERT_INIT__STAGE=failed                (with reason in a sibling tag)
```

Then `sg va list` could include a `cert-init` column. `sg vp register --wait` could poll the tag and surface the stage:

```
→  Polling https://16.61.12.105/ui/ until reachable…
  60s: cert-init stage=waiting-for-dns       (no DNS yet — give it ~30s more)
  90s: cert-init stage=dns-converged
  120s: cert-init stage=cert-issued
  145s: HTTP 401 in 142ms                    (vault is up)
```

Either A or B would have made the 7-minute hang diagnosable in 60 seconds.

### 2. Fail fast on persistent LE / DNS errors

cert_init.py currently retries silently. Add a "max consecutive failures" counter — if LE returns the same error 3+ times in 60s, mark the stack as failed (set a tag, exit non-zero, let compose surface the failure).

### 3. Add `sg va cert-status <stack>` verb

Returns:
- Current stage (from §1)
- Time elapsed in this stage
- Last 10 lines of `docker logs vault-app-cert-init-1`
- Probability that it'll succeed (heuristic: "still in DNS wait, expected 30-60s more" vs "failed 3 LE attempts, intervention needed")

### 4. Include cert-init in `sg va diag`

The existing `diag` reports EC2 state, SSM reachability, container engine status. Add a "cert-init" section that surfaces what §1 exposes.

### 5. Document the timing budget

`cert-init` in `letsencrypt-hostname` mode has an inherent budget:

| Stage | Typical | Worst case |
|---|---|---|
| Container start | 2-5s | 30s |
| DNS-resolver poll until FQDN → my IP | 5-60s | 900s (current default) |
| LE HTTP-01 challenge cycle | 5-20s | 60s (LE retries) |
| Write cert to /certs | <1s | n/a |
| **Total** | **30-90s** | **15+ min** |

Worth documenting at the top of cert_init.py and in `Vault_App__Service.create_stack` docstring. Operators using `--wait` need to know what timeout to set.

### 6. Optional but valuable — host-control endpoint for cert-status

Currently host-control's HTTP API on `:19009` doesn't expose cert state. Add a `GET /cert/status` that returns the same data as §1. Then `sg vp register --wait` and `sg va cert-status` could both poll the local HTTP endpoint (faster than SSM, no perms issues).

---

## How we'd love this to be testable

The `sg va` package already follows the no-mocks, in-memory-stack pattern. New tests should:

1. Mock cert_init.py at the file-write level — the new stage-file write should produce a known progression in tests.
2. The `cert-status` verb's polling logic should be testable in-memory (no SSM round-trip in tests).
3. Failure-mode tests: "LE returns 429 three times → cert-init exits non-zero + tag set" should be a unit test.

---

## What we did on the vault-publish side to work around this (FYI)

We added a `--no-tls` flag on `sg vp register` (separate commit) that provisions the EC2 with `with_tls_check=False`. In that mode:

- No cert-init container at all
- Vault listens on `:8080` HTTP only
- Browsers hit `https://<slug>.aws.sg-labs.app/` via the CloudFront wildcard, so the **viewer** sees a valid wildcard CF cert
- CF → Lambda → EC2 chain proxies the response over HTTP

This validates the full proxy + tagging + DNS + Lambda routing without depending on a working cert-init. Lets us diagnose registration failures **without** needing cert-init to succeed first.

It also opens a "two-phase provision" path:
1. `sg vp register --no-tls` — proves the routing works
2. (optional later) `sg vp adopt-tls <slug>` (or similar) — switches the stack to TLS mode and triggers cert-init

The second phase would benefit from the diagnostics asked for above — when cert-init is the only thing changing, observability matters most.

---

## Contact / context

- This brief was generated during a vault-publish debugging session that hit the 7-min cert-init hang.
- All the vault-publish code touched in that session is on branch `claude/waker-debug-clean-bRIbm` (rebased on `dev` multiple times).
- The case study `team/comms/briefs/v0.1.14__vault-publish-end-to-end-flow/README.md` lists 10 gotchas — items 5.3, 5.5, and the cert-renewal saga in that doc are adjacent to what this brief covers.
- The Setup-CLI pattern (`library/guides/v0.2.31__setup_cli_pattern.md`) applies — cert-status should be a `check`/`status` pair under `sg va`, drift-first ("which stage is it stuck at?" not "is it broken?").
