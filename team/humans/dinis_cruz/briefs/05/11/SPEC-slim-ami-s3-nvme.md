# SPEC — slim AMI + S3-backed artifact store + NVMe runtime cache

**Status:** proposed
**Filed:** 2026-05-11
**Resolves bug:** "local-claude AMI cold start is brutally slow" (2026-05-11)
**Affected spec:** `local-claude`, and pattern reusable for any future spec that needs large data at instance start
**Target acceptance:** cold start to `vLLM /v1/models == 200` in **< 2 min**; AMI bake **< 5 min**; root snapshot **< 8 GiB**

---

## 1. Core principle

**Anything large that lives in the AMI's EBS snapshot pays the EBS lazy-load tax on every fresh launch. Anything pulled from S3 at boot does not. Therefore: move as much data as possible out of the AMI and into S3.**

When an EBS volume is created from a snapshot, AWS does not copy snapshot data onto the new volume up front — blocks are fetched on-demand from the snapshot store the first time they are read, and that first-touch fetch is roughly 50–100x slower than steady-state EBS reads. By contrast, `s5cmd` (or `aws s3 cp`) pulling from S3 uses parallel multipart GETs that saturate the instance NIC and write to freshly-allocated EBS or NVMe blocks at line rate.

The consequence for AMI design:

> **The EBS root volume should contain only what is needed to reach the point where S3 can be reached. Everything else — model weights, container images, datasets, anything > a few hundred MB — should live in S3 and be pulled to NVMe at boot.**

This is the principle that shapes every concrete decision in this spec, and the principle that future GPU/large-data specs should inherit.

## 2. Goal

Replace the current "bake the model into the AMI" approach with a four-layer architecture:

1. **S3** — durable source of truth for *all* large artifacts: model weights, container images, datasets, anything else > a few hundred MB
2. **NVMe instance store** — ephemeral runtime cache, populated at boot from S3; backs both Docker's storage and the model cache
3. **EBS root volume** — minimal: kernel, drivers, Docker daemon binary (disabled until boot script reconfigures it), tooling, boot scripts
4. **No internet on the runtime path** — all S3 traffic goes via a VPC gateway endpoint; the instance can run in a private subnet with no IGW/NAT route at all

This eliminates the EBS-snapshot lazy-load penalty (root cause of the 10+ min cold starts), removes HuggingFace as a runtime dependency, removes any need for instances to reach the public internet, and shrinks the AMI to a size where bake-and-deploy cycles are fast.

## 3. Non-goals

- Not changing the vLLM launch command itself, only where its image and model live
- Not changing the `sg lc` CLI surface (modulo one optional new subcommand for artifact upload)
- Not changing the spec composition system; implemented as edits to existing user-data sections plus one new section
- Not optimising serving-time performance (separate concern; addressed by RAM/instance-class choice, not this spec)
- Not solving the "model > RAM" page-cache eviction risk; addressed by instance-class choice (see §11)

## 4. Architecture overview

```
┌────────────────────────────────────────────────────────────────────┐
│ Build time (one-off per artifact version)                          │
│                                                                    │
│   HF Hub ──pull──┐                                                 │
│                  │                                                 │
│   docker build ──┼──► build host ──s5cmd cp──► S3 bucket          │
│                  │                                                 │
│                  └─► docker save vllm.tar                          │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│ AMI bake (rare; only when OS / driver / tooling changes)           │
│                                                                    │
│   base AMI ──install drivers + Docker + tooling──► slim AMI        │
│              (no models, no container images)                      │
│              target snapshot: 4–6 GiB                              │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│ Runtime (every fresh launch)                                       │
│                                                                    │
│   slim AMI ──boot──► EC2 instance (private subnet, no IGW)         │
│                       │                                            │
│                       ├─► mount NVMe at /mnt/nvme                  │
│                       │                                            │
│                       ├─► configure Docker data-root on NVMe       │
│                       │   start Docker daemon                      │
│                       │                                            │
│                       ├─► parallel s5cmd cp from S3:               │
│                       │     • vllm-image.tar  → /mnt/nvme/         │
│                       │     • model shards    → /mnt/nvme/model/   │
│                       │   (~25s combined, via VPC gateway endpt)  │
│                       │                                            │
│                       ├─► docker load -i vllm-image.tar            │
│                       │   (image layers land on NVMe)              │
│                       │                                            │
│                       └─► docker run vllm:tag                      │
│                           (reads container layers + model          │
│                            from NVMe at ~3 GB/s)                   │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

Every link on the runtime path operates at hardware-or-NIC line rate. No link involves EBS snapshot lazy-load. No link involves the public internet.

## 5. The S3 artifact store

### 5.1 What goes in S3

Per the core principle: anything large enough that lazy-loading would hurt. Concretely for this spec:

- Model weights (~15 GiB per model version)
- vLLM container image as a saved tarball (~3–5 GiB per image version)
- Optional: any future dataset caches, fine-tuning checkpoints, etc.

### 5.2 Bucket layout

One bucket per environment (or one shared bucket if access patterns permit):

```
s3://sg-compute-artifacts-<env>/
    models/
        <model-family>/
            <model-version>/
                config.json
                tokenizer.json
                model-00001-of-00006.safetensors
                …
                MANIFEST.json
    images/
        vllm/
            <vllm-version>/
                vllm-image.tar
                MANIFEST.json
```

Versioning is encoded in the key so the runtime can pin a specific version and roll forward/back without bucket-policy gymnastics. S3 bucket versioning is optional and used only for accidental-delete recovery.

### 5.3 Bucket configuration

- **Region**: same region as where instances are launched. Critical for speed and cost.
- **Storage class**: `STANDARD`. Frequent reads, latency matters.
- **Encryption**: SSE-S3 (AES-256) at minimum; SSE-KMS if compliance demands it.
- **Public access**: blocked. Always private; access via IAM only.
- **Lifecycle**: optional rule to expire old model/image versions after N days.

### 5.4 Upload workflow

#### Models

A one-off script (or `sg lc artifact upload model …` subcommand — see §9.6) that, given a HF model ID:

1. Pulls the model to a scratch directory (`huggingface-cli download`)
2. Validates the file set against the model's `index.json`
3. Uploads to `s3://<bucket>/models/<family>/<version>/` using `s5cmd cp --numworkers 32`
4. Writes a `MANIFEST.json` listing files + sizes + (optional) sha256

#### Container images

A one-off script (or `sg lc artifact upload image …` subcommand) that, given a Docker image reference:

1. `docker pull <image>:<tag>` on the build host
2. `docker save <image>:<tag> -o vllm-image.tar`
3. Verifies the tarball loads cleanly (`docker load -i` into a scratch Docker, then `docker rmi`)
4. Uploads to `s3://<bucket>/images/vllm/<vllm-version>/vllm-image.tar`
5. Writes a `MANIFEST.json` with image digest + size

Both flows run once per artifact version, by a human or CI, before any instance needs them. The output is a stable S3 URI prefix that instance configs pin to.

## 6. The slim AMI

### 6.1 What is baked into the AMI

Minimum viable set to reach S3 and run a Docker container:

- Ubuntu 24.04 minimal (install with `--no-install-recommends` from the start)
- NVIDIA driver + CUDA runtime
- Docker daemon (installed but **disabled** at boot — see §6.3)
- NVIDIA container toolkit
- AWS CLI v2
- `s5cmd` static binary at `/usr/local/bin/s5cmd`
- `xfsprogs`
- `chrony` configured to use Amazon Time Sync (`169.254.169.123`) only
- Boot scripts / systemd units from `sg_compute`

### 6.2 What is explicitly NOT baked

- No HF model files
- No HF cache directory pre-populated
- No vLLM container image (neither as a Docker image in `/var/lib/docker` nor as a tarball)
- No application data
- No package manager caches (`apt clean && rm -rf /var/lib/apt/lists/*`)
- No bake-time logs (`/var/log/*` truncated)
- No cloud-init instance data from the bake host (`/var/lib/cloud/instances/*` wiped)
- No SSH host keys (regenerated on first boot)
- No `/etc/machine-id` (regenerated on first boot)
- No `snapd` (`apt purge snapd` — Ubuntu cloud images include it by default; removing it eliminates background snap refresh traffic)
- No `unattended-upgrades` (purged or timers disabled)
- No `/usr/share/doc`, `/usr/share/man` (optional but cheap; saves ~200 MB)

### 6.3 Docker daemon: installed but disabled

The Docker daemon binary is baked in, but the service is **disabled** at AMI bake time:

```bash
systemctl disable docker docker.socket
```

This matters because:

- The daemon's default `data-root` is `/var/lib/docker` on the EBS root volume
- We want it to use `/mnt/nvme/docker` instead, configured at boot
- If Docker starts at boot before the NVMe is mounted and `daemon.json` is written, it touches EBS and we'd then have to migrate or risk inconsistency
- Disabling and letting the boot script bring Docker up *after* config is written avoids all of that

The boot script is responsible for starting Docker, in the right order (§7).

### 6.4 Root volume sizing

- **Target snapshot size:** ≤ 8 GiB (down from ~50 GiB; realistic floor is 4–6 GiB)
- **Provisioned root volume at launch:** 20 GiB gp3 (down from 200 GiB)
- Volume class stays gp3 baseline (125 MB/s, 3000 IOPS). Root volume is not on the hot path after boot.

### 6.5 Bake process

1. Launch a g5.xlarge from a clean base AMI
2. Install OS deps, drivers, Docker, NVIDIA container toolkit, `s5cmd`, AWS CLI, `xfsprogs`
3. Configure `chrony` for Amazon Time Sync only
4. Purge `snapd`, `unattended-upgrades`, doc/man if desired
5. Disable Docker service: `systemctl disable docker docker.socket`
6. Drop in the `sg_compute` boot scripts / systemd units
7. Clean up: `apt clean`, wipe `/var/lib/apt/lists`, `/var/log/*`, `/var/lib/cloud/instances/*`, `/tmp/*`, `~/.cache`, SSH host keys, `/etc/machine-id`
8. Optional: zero free space to improve snapshot compression
9. Create AMI (with clean shutdown, not `--no-reboot`)
10. Tag AMI: vLLM version compatibility, CUDA version, bake date, `sg_compute` git SHA

Target bake wall-clock: **< 5 min**.

## 7. Boot sequence

After the EC2 instance launches from the slim AMI, the boot script (composed of the `sg_compute` sections) runs in this order:

```
1. Discover and mount NVMe instance store at /mnt/nvme
2. Write /etc/docker/daemon.json with data-root: /mnt/nvme/docker
3. systemctl start docker  (daemon now uses NVMe for everything)
4. In parallel:
     s5cmd cp s3://…/images/vllm/<ver>/vllm-image.tar  /mnt/nvme/
     s5cmd cp s3://…/models/<family>/<ver>/*           /mnt/nvme/model/
   wait for both
5. docker load -i /mnt/nvme/vllm-image.tar
   rm /mnt/nvme/vllm-image.tar  (the layers are now in /mnt/nvme/docker)
6. docker run vllm:<tag>  with:
     - /mnt/nvme/model bind-mounted into the container
     - HF_HOME / model path env vars pointed at it
7. Wait for vLLM /v1/models to return 200
```

### 7.1 NVMe discovery

g5.xlarge ships with one NVMe instance-store device, separate from the EBS root volume but exposed via the same NVMe protocol. Distinguish by device model string, not by path:

```bash
INSTANCE_STORE=$(
  lsblk -d -o NAME,MODEL -n \
  | awk '$2 ~ /Instance Storage/ {print "/dev/"$1; exit}'
)
[ -z "$INSTANCE_STORE" ] && { echo "FATAL: no NVMe instance store"; exit 1; }
```

EBS reports `MODEL = "Amazon Elastic Block Store"`. Instance store reports `MODEL = "Amazon EC2 NVMe Instance Storage"`. The `awk` discriminator avoids any chance of formatting the root volume.

### 7.2 Format and mount

```bash
mkfs.xfs -f -L nvme "$INSTANCE_STORE"
mkdir -p /mnt/nvme
mount -o defaults,noatime,nodiratime "$INSTANCE_STORE" /mnt/nvme
echo "LABEL=nvme /mnt/nvme xfs defaults,noatime,nodiratime,nofail 0 2" \
  >> /etc/fstab
```

xfs matches what's already in the bug report's logs. `noatime,nodiratime` saves write IOPS during model load.

### 7.3 Docker data-root on NVMe

Before starting the daemon, point it at NVMe:

```bash
mkdir -p /mnt/nvme/docker
cat > /etc/docker/daemon.json <<EOF
{
  "data-root": "/mnt/nvme/docker",
  "default-runtime": "nvidia"
}
EOF
systemctl start docker
```

From this point on, every image layer, container filesystem, and Docker volume lives on NVMe. EBS is untouched by Docker.

### 7.4 Parallel S3 fetch

The image tarball and the model are independent — pull them concurrently. They share the NIC well; total wall-clock is roughly `max(time(image), time(model))`, not the sum.

```bash
s5cmd --numworkers 32 cp \
  "s3://${BUCKET}/images/vllm/${VLLM_VER}/vllm-image.tar" \
  "/mnt/nvme/" &
PID_IMG=$!

s5cmd --numworkers 32 cp \
  "s3://${BUCKET}/models/${MODEL_FAMILY}/${MODEL_VER}/*" \
  "/mnt/nvme/model/" &
PID_MOD=$!

wait $PID_IMG $PID_MOD
```

Expected throughput on g5.xlarge (10 Gbps NIC, same-region S3 via VPC gateway endpoint):

| Workload | Size | Time at ~800 MB/s |
|---|---|---|
| vLLM image tarball | ~4 GiB | ~5s |
| Model weights | ~15 GiB | ~20s |
| Combined (parallel) | ~19 GiB | ~22s |

### 7.5 Load image and run

```bash
docker load -i /mnt/nvme/vllm-image.tar
rm /mnt/nvme/vllm-image.tar    # layers are now in /mnt/nvme/docker
docker run -d --gpus all \
  -v /mnt/nvme/model:/models:ro \
  -e HF_HOME=/models \
  -p 8000:8000 \
  vllm:${VLLM_VER} \
  --model /models/<config-path> \
  …
```

vLLM container layers are read from `/mnt/nvme/docker` at ~3 GB/s. Model files are read from `/mnt/nvme/model` at ~3 GB/s. Nothing in the runtime path reads from EBS.

### 7.6 Failure modes

- **S3 unreachable** (IAM misconfig, missing VPC endpoint route): fail fast with a clear message; the instance is useless without artifacts.
- **Partial download**: rely on MANIFEST check; retry the whole prefix once, then fail.
- **Disk full** on NVMe: indicates instance class with too-small NVMe or a wrong artifact. Fail with a `df -h` dump.
- **Docker daemon won't start**: usually a `daemon.json` syntax error or missing nvidia runtime. Fail with the daemon log.

All failure paths write a structured marker to a known log location so `sg lc diag` can surface them.

### 7.7 Lifecycle awareness

The boot script assumes the NVMe is **always empty** on boot. Instance-store data is preserved across reboot but wiped on stop/start and on hardware migration. The safest model is "treat every boot as cold cache; re-populate from S3 every time". The S3 copy is fast enough that conditional caching across reboots is not worth the complexity.

## 8. Network posture

The runtime instance does not need public internet access. With a VPC gateway endpoint for S3 in place, all artifact traffic flows over AWS's internal network.

### 8.1 Required network configuration

- **VPC gateway endpoint for S3** (mandatory, free). Routes S3 traffic without traversing IGW or NAT. The instance can live in a private subnet with no internet route at all.
- **Security group egress**: allow only the S3 prefix list (`com.amazonaws.<region>.s3`) and link-local addresses (IMDS at `169.254.169.254`, Amazon Time Sync at `169.254.169.123`). No `0.0.0.0/0` egress.
- **DNS**: VPC-provided resolver (`.2` of the VPC CIDR) or Route53 Resolver. Pinned, not free-roaming.
- **IAM**: instance profile with `s3:GetObject` and `s3:ListBucket` on the artifact bucket only. Read-only. No credentials baked into the AMI.

### 8.2 Disabled background services

The AMI ships with all of the following purged or disabled so nothing on the instance tries to phone home:

- `snapd` — purged
- `unattended-upgrades` — purged or timers disabled
- `apt-daily.timer`, `apt-daily-upgrade.timer` — disabled
- `motd-news` — disabled in `/etc/default/motd-news`
- `chrony` external pools — replaced with Amazon Time Sync

### 8.3 IAM policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::sg-compute-artifacts-<env>",
        "arn:aws:s3:::sg-compute-artifacts-<env>/*"
      ]
    }
  ]
}
```

## 9. Code changes

Mapping onto the existing layout from the bug report's "Related code" section:

### 9.1 `sg_compute/platforms/ec2/user_data/Section__Base.py`

Add NVMe discovery and mount logic. Runs early in the boot preamble, before any section that expects `/mnt/nvme` to exist.

- Locate NVMe instance-store device by model string
- `mkfs.xfs` and mount at `/mnt/nvme`
- Persist in `/etc/fstab` with `nofail`
- Emit a structured log marker on success/failure

### 9.2 `sg_compute/platforms/ec2/user_data/Section__Docker.py`

Substantially rewritten:

- Before starting Docker, write `/etc/docker/daemon.json` with `data-root: /mnt/nvme/docker`
- `systemctl start docker` (replacing whatever previously assumed it was already running)
- The bind-mount path for the model changes from the old EBS-backed HF cache path to `/mnt/nvme/model`

### 9.3 *(new)* `sg_compute/platforms/ec2/user_data/Section__S3_Artifact_Fetch.py`

New section, owned by `sg_compute` so future specs can reuse it.

Responsibilities:
- Read artifact S3 URIs from user-data parameters (model prefix + image tarball URI)
- Invoke `s5cmd cp` in parallel for both
- Optional manifest verification
- `docker load -i` the image tarball, then delete it
- Emit structured log markers with timing and byte counts
- Fail loudly on any error

Parameters consumed (from spec-level config):
- `artifact_s3_bucket`
- `model_s3_prefix` (e.g. `models/llama-3.1-70b-instruct/v1/`)
- `image_s3_key` (e.g. `images/vllm/0.6.3/vllm-image.tar`)

### 9.4 `sg_compute/platforms/ec2/user_data/Section__VLLM.py`

Only the model path env var / mount path changes (to `/mnt/nvme/model`). The actual launch command is unchanged.

### 9.5 `sg_compute_specs/local_claude/service/Local_Claude__User_Data__Builder.py`

Update section composition:

```
Section__Base                # now includes NVMe mount
Section__S3_Artifact_Fetch   # new
Section__Docker              # now configures data-root on NVMe before starting
Section__VLLM                # unchanged behavior, path changes only
```

Wire through the artifact S3 URI parameters.

### 9.6 *(new, optional)* `sg lc artifact upload …` subcommands

CLI affordances for the build-time S3 upload workflow described in §5.4. A standalone script is acceptable for v1, but a clean subcommand makes onboarding new model versions a one-liner:

```
sg lc artifact upload model <hf-model-id> --version <ver>
sg lc artifact upload image <docker-image:tag> --version <ver>
```

## 10. Cold-start timing budget

| Phase | Duration | Notes |
|---|---|---|
| EC2 launch → SSH-ready | 25–35s | Small AMI, fast boot |
| NVMe format + mount | 1–2s | xfs format on 250 GB is fast |
| Docker daemon start (data-root on NVMe) | 2–3s | Fresh start, no migration |
| Parallel `s5cmd cp` (image + model) | 20–30s | ~19 GiB combined over 10 Gbps NIC |
| `docker load` image tarball | 3–5s | NVMe-to-NVMe |
| `docker run` container start | 3–5s | Image layers on NVMe |
| vLLM checkpoint load from NVMe | 5–10s | 15 GiB at ~3 GB/s |
| vLLM warmup → `/v1/models` 200 | 10–20s | CUDA init included |
| **Total** | **~70–110s** | Comfortably under 2 min |

If any phase exceeds budget by >2x, that's a regression worth investigating.

## 11. Instance class choice

This spec assumes **g5.xlarge** (16 GiB RAM, 1 × 250 GB NVMe). The model is 15.66 GiB, exceeding usable RAM (12.61 GiB), so vLLM's auto-prefetch stays disabled and the kernel can't keep the full model in page cache.

Two compatible paths:

- **Stay on g5.xlarge.** NVMe at ~3 GB/s is fast enough that re-paging from disk under memory pressure is tolerable for dev use. This is the cheap default.
- **Upgrade to g5.2xlarge** (32 GiB RAM, 1 × 450 GB NVMe). Model fits in page cache, auto-prefetch re-enables, NVMe is larger. ~2x hourly cost. Worth it for sustained serving or production.

The choice is orthogonal to this spec; only the spec's `instance_type` parameter changes.

## 12. Acceptance criteria

- [ ] `sg lc create --ami <slim-ami-id>` reaches `vLLM /v1/models == 200` in **< 2 min** total on a cold launch (no prior instance reuse)
- [ ] `sg lc diag` shows all 8 checks green within the same window
- [ ] AMI bake completes in **< 5 min**
- [ ] Slim AMI snapshot size is **< 8 GiB**
- [ ] Re-running `sg lc create` on a different instance hits the same < 2 min window
- [ ] No HuggingFace or other public-internet network call is made on the runtime path; `tcpdump` during boot shows traffic only to S3 (via VPC endpoint) and AWS link-local services
- [ ] The instance functions correctly in a private subnet with **no IGW or NAT route**
- [ ] `du -sh /var/lib/docker` is near-zero after boot (Docker storage lives on NVMe)
- [ ] Fat AMIs (`ami-…` and `ami-0b540a6e1c7b3297e`) can be deregistered once the slim path has been validated on at least two model versions

## 13. Rollout plan

1. **Land §5 (S3 upload workflows)** independently for both models and images. Verifies bucket/IAM setup with no behavioural change to existing instances.
2. **Build the slim AMI** without wiring it to any spec yet. Manual smoke test: launch from it, manually run the boot steps, confirm vLLM comes up.
3. **Land §9 code changes** behind a config flag on `local-claude` (e.g. `use_slim_ami: false` default). Existing fat-AMI path remains usable.
4. **Flip the flag** in dev, verify acceptance criteria, run for a week.
5. **Move the instance to a private subnet** (no IGW) and verify it still works. This confirms the network posture.
6. **Flip the flag** as default; remove the flag and the fat-AMI code path in a follow-up.
7. **Deregister the fat AMIs** after 30 days of no use.

## 14. Future work and pattern reuse

- **Apply the pattern to other specs.** Any future spec needing large data at startup (ollama models, large datasets, custom training images, additional container images) plugs into `Section__S3_Artifact_Fetch` instead of inventing its own approach. The principle from §1 governs.
- **ECR alternative for container images.** S3 tarball is the v1 choice because it shares the existing S3 path, IAM, and VPC endpoint. If image management grows (tags, scanning, immutability semantics), migrate images to ECR — needs interface endpoints for `ecr.api` and `ecr.dkr` (~$7/month/AZ each) to preserve the no-public-internet posture. The boot script change is minimal: `docker pull` instead of `s5cmd cp` + `docker load`.
- **Multi-region.** If instances launch in regions other than where the artifact bucket lives, either replicate the bucket (S3 CRR) or document cross-region transfer cost. Out of scope for v1.
- **Pre-warmed AMI via Fast Snapshot Restore.** Would shave a few seconds off the EC2 boot phase. At ~$38/month/AZ for an 8 GiB AMI it's not justified yet. Revisit only if launch frequency goes above several per hour.
- **Integrity verification at scale.** The MANIFEST.json + optional sha256 check is described as optional. For real customer workloads, make it mandatory and budget ~10–20s for it.
