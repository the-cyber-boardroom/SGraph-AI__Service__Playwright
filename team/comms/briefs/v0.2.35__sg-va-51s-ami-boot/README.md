# Milestone — `sg va create --ami` → healthy HTTPS vault in 51s

- **Status**: shipped
- **Date**: 2026-05-19
- **Version**: v0.2.35
- **Spec**: `vault-app` (just-vault shape, self-signed TLS, t3.medium spot)
- **Companion brief**: `team/comms/briefs/v0.1.14__sg-va-cert-init-observability/` (cert-init stage progression visible in the timeline below)
- **Companion bug**: `team/comms/briefs/v0.2.8__local-claude-ami-cold-start-perf.md` (why the AMI-bake pattern works for vault-app but not for local-claude)

---

## TL;DR

A freshly-launched `sg vault-app` stack from a baked AMI reached **a CA-signed HTTPS vault on `:443` in 51 seconds**, from `aws ec2 RunInstances` to a `200 / 401` over TLS. That's ~3-5x faster than the non-AMI path and good enough that `sg vp register --wait` can size its timeout around minutes-not-tens-of-minutes.

```
sg va create --ami ami-076ba06f91d7ea338 --wait
    ✓ healthy  state=running  51s  (51272ms)
    cert: CA-signed · 6d left

Stage timings
  t+26s    Docker ready
  t+38s    cert-init Up 6 seconds
  t+50s    HTTPS up — HTTP 401
```

The chain that delivers this:
1. **Pre-baked AMI** ships Docker + compose plugin + all four Docker Hub image layers warm on the snapshot.
2. **Docker Hub image pulls** (post-ECR migration) keep the cold-pull case cheap when the AMI does miss.
3. **just-vault stack** is 2 containers (cert-init + sg-send-vault); no playwright sidecars to start in parallel.
4. **Self-signed TLS** keeps cert-init under ~10s (no DNS wait, no ACME HTTP-01 round-trips).
5. **The new `cert-init` row in `sg va check`** surfaces stage progression live so a slow boot is diagnosable in seconds, not minutes.

---

## The 51-second timeline (verified, 2026-05-19)

```
sg va create --ami ami-076ba06f91d7ea338 --wait
  Submitting to AWS …
  instance-id : i-0f9e10848b044255d
  submitted in: 4.2s                                    ← RunInstances returns

  Waiting for vault-app stack 'deft-planck' to be healthy …
    state=pending  awaiting public IP…                  ← EC2 still allocating
    state=running  ip=35.179.178.100  waiting on boot…  ← instance running, no boot marker yet
    state=running  ip=35.179.178.100  stage=Docker ready
    state=running  ip=35.179.178.100  cert-init=Up 6 seconds  stage=Docker ready
    ✓ healthy  HTTP 401  https://35.179.178.100  (auth-gated — expected)  cert: CA-signed · 6d left

  Stage timings
  t+26s    Docker ready                ← +26s from t0  (AMI shortcut — no dnf/curl/systemctl install steps)
  t+38s    cert-init Up 6 seconds      ← +12s         (cert-init container + self-signed cert generation)
  t+50s    HTTPS up — HTTP 401         ← +12s         (sg-send-vault binds :443 with the cert cert-init wrote)

  ✓  healthy  state=running  51s  (51272ms)
```

**What "healthy" means here**: the FastAPI's `/info/health` returned `HTTP 401` over **TLS** on `:443`. 401 is the expected auth-gated response — proves the vault is up and the cert handshake works. CA-signed = the self-signed cert is locally trusted at this stack's scope; "6d left" = the cert lifetime cert-init wrote.

---

## Why this is fast (and where the time goes)

### The AMI shortcut

A fresh-AL2023 boot of the same stack would do:

| Stage | Fresh AL2023 | From baked AMI |
|---|---|---|
| EC2 launch + cloud-init | ~15s | ~15s |
| `dnf install -y docker` | ~25-35s | **skipped** (baked) |
| Download docker-compose plugin from GitHub | ~5-10s | **skipped** (baked) |
| `systemctl enable --now docker` | ~3s | ~3s |
| Pull `diniscruz/sg-host-control` (cert-init image) | ~15-25s | **skipped** (baked) |
| Pull `diniscruz/sg-send-vault` | ~15-25s | **skipped** (baked) |
| cert-init self-signed cert generation | ~5s | ~5s |
| sg-send-vault startup, bind `:443` | ~10s | ~10s |
| **Total (typical)** | **90-130s** | **~50s** |
| Total (worst case — slow image pull) | 3-4 min | ~50-60s |

The AMI bake eliminates the engine install + image pull entirely. What's left is the cost of the EC2 launch + container start, which we can't compress further without skipping the launch (e.g. keeping a stack warm).

### Why this AMI workflow works (where local-claude's didn't)

The vault-app AMI is small. The bake captures:
- AL2023 root filesystem (~3 GiB)
- Docker + compose plugin (~200 MiB)
- 4 Docker Hub image layers — `sg-host-control`, `sg-send-vault`, `sg-playwright`, `mitmproxy/mitmproxy` (~600 MiB compressed)

Total snapshot: ~5-6 GiB. EBS lazy-load from snapshot reads each first-touch block from S3 (~50-100× slower than steady-state EBS), but at this size the cost is amortised across the boot in a way that doesn't dominate.

The local-claude AMI bake hit the opposite problem (see `team/comms/briefs/v0.2.8__local-claude-ami-cold-start-perf.md`): a 50-GiB snapshot containing a 15-GiB safetensors model — vLLM is the first reader, every shard pays the S3-fetch cost, and total first-load went from "<1 min" to "10+ min". The rule of thumb that emerges:

> **Bake the AMI when the cached payload is < ~10 GiB AND the first reader doesn't need to read most of it sequentially. Skip the bake when the payload is a multi-GiB blob that the first launch will scan end-to-end.**

### The non-AMI parts of the speed-up

These aren't AMI tricks; they're recent platform work that's also visible in the 51s number:

| Recent change | Saves | Where |
|---|---|---|
| ECR → Docker Hub image migration | ~5-10s (no `aws ecr get-login-password` round-trip) | `Vault_App__Compose__Template`, `Vault_App__User_Data__Builder` |
| `mitmproxy/mitmproxy:latest` from Docker Hub instead of a custom ECR image | ~10-20s on with-playwright stacks | `Playwright__Compose__Template`, `Vault_App__Compose__Template` |
| cert-init stage file + 180s DNS-wait default (was 900s) | bounds the worst case at ~5min instead of 15min | `sg_compute/platforms/tls/cert_init.py` |
| `sg va check` shows cert-init stage live | makes "stuck cert-init" diagnosable in seconds | `Cli__Vault_App`, `Vault_App__Service.diagnose` |

---

## Operator guidance — how to repeat this

### 1. Bake the AMI

From a stack that's already running and healthy:

```bash
sg va create --max-hours 0.5                # plain just-vault stack on AL2023 base
sg va check                                 # confirm all rows ✓ OK before baking
sg va ami bake                              # bakes the running stack's root volume
sg va ami wait                              # blocks until the AMI is 'available'
sg va ami list                              # capture the new ami-... id
```

What `ami bake` does under the hood (`AMI__Service.bake`):
- Stops the source instance (cleanly — flushes Docker layers to disk)
- Calls `ec2:CreateImage` with the source stack name in the description
- Re-starts the source instance (so the source stack keeps running)

The bake itself takes 3-8 minutes (mostly the snapshot copy in the background). `ami wait` polls until the AMI's `State == available`.

### 2. Launch from the AMI

```bash
sg va create --ami ami-076ba06f91d7ea338 --wait
```

The `--wait` flag drives the new diagnose-based wait loop — it re-runs `sg va check` every 10s and prints the stage progression so the operator sees boot stages, not silent polling.

For the with-TLS-hostname path (LE cert):

```bash
sg va create --ami <id> \
  --with-aws-dns                            # parallel Route 53 A-record upsert + INSYNC wait
  --tls-mode letsencrypt-hostname \
  --tls-hostname my-slug.aws.sg-labs.app \
  --wait
```

Realistic timing with TLS-hostname and AMI:
- ~26s Docker ready (AMI savings)
- ~5-10s cert-init container start
- ~5-30s DNS-wait (usually returns on first poll because `--with-aws-dns` ran the INSYNC poll in parallel during boot)
- ~10-20s LE HTTP-01 challenge round-trip
- ~10s sg-send-vault start + :443 bind
- **= ~70-100s total**, vs ~3-5 min without AMI

### 3. Re-bake cadence

Re-bake the AMI **after** any of the following:
- Pushing a new image tag to `diniscruz/sg-send-vault` (vault binary update)
- Pushing a new image tag to `diniscruz/sg-host-control` (cert-init + host-plane code change)
- Pushing a new image tag to `diniscruz/sg-playwright` (only if your AMI is for with-playwright stacks)
- Any change to `sg_compute.platforms.tls.cert_init` (the cert-init container's entrypoint code is *inside* the host-control image)
- Any change to the compose template that adds new image dependencies

If you skip a re-bake after one of the above, fresh launches from the stale AMI will *still work* — compose will pull the new image when it doesn't match the cached digest — but you lose the speed-up.

### 4. Clean up old AMIs

AMIs cost ~$0.05/GiB-month for the snapshot. A ~6 GiB vault-app AMI is ~$0.30/month — cheap but they accumulate.

```bash
sg va ami list                              # see all baked AMIs for this spec
sg va ami delete <ami-id>                   # deregisters the AMI + its snapshot
```

Rule of thumb: keep the latest 2 bakes (current + previous, for rollback); deregister the rest.

### 5. When NOT to use a baked AMI

Skip the bake (use the base AL2023 image, the default) when:
- You're iterating on the cloud-init script — every change requires a re-bake to be visible from the AMI path
- You're debugging the engine install / image pull stages — the AMI path skips them, so any bug there is invisible
- The image you'd bake against is itself unstable (e.g. an :unstable tag from a feature branch)
- Single launch + immediate delete — bake amortisation doesn't kick in

---

## What this unlocks

- **`sg vp register --wait`** can drop its polling timeout from "minutes" to "~2 minutes" on the AMI path. The cert-init brief asked for a tighter feedback loop on this command; AMI + the new stage-file row close most of the gap.
- **CI smoke tests** that spin up a vault and tear it down become viable as a < 2-min check (was ~5-min, which pushed people toward mocking instead).
- **`sg va recreate`** (delete + relaunch) on a baked AMI is a sub-1-minute round-trip — fast enough that operators reach for it instead of trying to live-fix a wedged stack.
- **Cost**: spot t3.medium at the published rate is ~$0.012/h; a 1-hour debug session is ~$0.01. The 51s boot makes the cost-per-test trivial.

---

## What we'd still want (open follow-ups)

- **Warm-AMI cache** — auto-rebake whenever a new image tag is pushed to Docker Hub (GitHub Actions job)
- **AMI provenance tags** — embed the git SHA and image digests at bake time so `sg va ami list` shows what's actually inside each AMI
- **`sg va recreate --reuse-instance`** — wipe + redeploy compose on an existing instance without an EC2 round-trip (~10s round-trip target)
- **Multi-region AMIs** — `aws ec2 CopyImage` to the regions we deploy in, indexed by region tag

These don't block the 51s number — they make it easier to keep hitting it.

---

## Related code

| Concern | Path |
|---|---|
| AMI resolution helper | `sg_compute_specs/vault_app/service/Vault_App__AMI__Helper.py` |
| AMI bake / list / wait service | `sg_compute/core/ami/service/AMI__Service.py` |
| AMI CLI sub-typer (`sg va ami …`) | `sg_compute/cli/base/Spec__CLI__Builder.py:411` (`_register_ami`) |
| User-data builder (skips engine install when AMI present) | `sg_compute_specs/vault_app/service/Vault_App__User_Data__Builder.py` |
| Compose template (Docker Hub images, post-ECR) | `sg_compute_specs/vault_app/service/Vault_App__Compose__Template.py` |
| cert-init entry + stage file | `sg_compute/platforms/tls/cert_init.py` |
| `sg va check` cert-init row | `sg_compute_specs/vault_app/service/Vault_App__Service.py` (`diagnose` method) |

---

## Related guides

- `library/guides/v0.2.31__setup_cli_pattern.md` — the `check / status / create / update / delete` pattern that shaped the new `sg va check` + `sg va wait`
- `team/comms/briefs/v0.1.14__sg-va-cert-init-observability/README.md` — the cert-init stage-file work this milestone exercises
- `team/comms/briefs/v0.2.8__local-claude-ami-cold-start-perf.md` — why AMIs work here but not on the GPU spec
