# 2026-05-11 — SG/Compute extend, sudoers fix, AMI cold-start brief, slim-AMI spec review

**Status:** COMPLETE (all work merged to `dev` via `6f932c77`)
**Versions:** `sg_compute` v0.2.8 (no bump this session)
**Branch:** `claude/sg-compute-continuation-Ko0RY` — fully merged; `git log origin/dev..HEAD` is empty
**Predecessor:** [`2026-05-10__local-claude-end-to-end-boot.md`](2026-05-10__local-claude-end-to-end-boot.md)

## Commits this session

| Hash | Title |
|---|---|
| `950f1821` | `feat(cli): add sg lc extend — cancel shutdown timer and arm new one N hours from now` |
| `d4d20d71` | `fix(boot): write NOPASSWD sudoers for ssm-user; bug brief for AMI cold-start perf` |
| `d83705a4` | `added brief` — **user-authored** SPEC for slim AMI + S3 + NVMe (under `team/humans/`) |
| `6f932c77` | merge commit bringing the above into `dev` |

Earlier commit `c8d4f35f` (prior-session wrap-up debrief) was authored in this session but documents the previous arc — not counted here.

---

## TL;DR for the next agent

1. **All this session's code is on `dev`. Start from `dev`.** No carry-over branch.
2. **The cold-start performance investigation is the live open thread.** Bug brief: [`team/comms/briefs/v0.2.8__local-claude-ami-cold-start-perf.md`](../../comms/briefs/v0.2.8__local-claude-ami-cold-start-perf.md). User-authored solution spec: [`team/humans/dinis_cruz/briefs/05/11/SPEC-slim-ami-s3-nvme.md`](../../humans/dinis_cruz/briefs/05/11/SPEC-slim-ami-s3-nvme.md). The spec is the source of truth for the next slice.
3. **Before implementing the spec, the user wants benchmark numbers.** Run `ec2-boot-bench` against this project's AWS setup using the settings in §"Open: benchmark step" below. Output informs whether the slim AMI's wins compound on cold-start time or are purely a runtime concern.
4. **Two fat AMIs (~50 GiB) still exist:** `ami-0b540a6e1c7b3297e` (working) and one earlier. Do NOT deregister yet — they're useful as the "before" data point in the benchmark.
5. **`sg lc extend` is new and live.** Cancels the shutdown timer and updates the `TerminateAt` tag; see [`Cli__Local_Claude.py`](../../../sg_compute_specs/local_claude/cli/Cli__Local_Claude.py) `extend()` for usage. The sudoers fix in `Section__Base` heals existing AMIs on next boot — no re-bake required.

---

## What was done

### 1. `sg lc extend` command (`950f1821`)

New CLI verb. Cancels any transient `run-*.timer` units via SSM, arms a fresh `systemd-run --on-active=Xs /sbin/shutdown -h now`, and updates the `TerminateAt` EC2 tag so `sg lc list` time-left stays accurate.

- Added `EC2__Instance__Helper.update_tags()` (wraps boto3 `create_tags` per the narrow-boto3 exception).
- New CLI command in [`sg_compute_specs/local_claude/cli/Cli__Local_Claude.py`](../../../sg_compute_specs/local_claude/cli/Cli__Local_Claude.py).
- `--add-hours`/`--ah` flag (float, default 1.0). New expiry = `now + N hours`.
- Pattern is reusable for other specs if they bake the same timer model in `Section__Base`.

### 2. NOPASSWD sudoers fix (`d4d20d71`)

`sg lc connect` started prompting for a password on `sudo`. Root cause: the SSM Agent writes `/etc/sudoers.d/ssm-agent-users` **only** on the first interactive Session Manager session. Because we pre-create `ssm-user` in `Section__Base` (per the Bug F fix from the prior session), the agent sees "user already exists" on every subsequent boot and skips the sudoers entry.

Fix: write `/etc/sudoers.d/ssm-agent-users` explicitly in [`Section__Base.py`](../../../sg_compute/platforms/ec2/user_data/Section__Base.py) right after `useradd`. Idempotent — heals all existing AMIs on next boot.

### 3. AMI cold-start performance — diagnosis + bug brief

User observed: launches from `ami-0b540a6e1c7b3297e` hang for many minutes on `Loading safetensors checkpoint shards: 0%`. Same AMI is fast on the second start; the AMI it was baked from was instant.

Diagnosis (in [`team/comms/briefs/v0.2.8__local-claude-ami-cold-start-perf.md`](../../comms/briefs/v0.2.8__local-claude-ami-cold-start-perf.md)): **EBS lazy-load from snapshot**. New EBS volumes created from a snapshot are empty until first read; first-touch pulls each block from S3 at ~50–100x EBS steady-state latency. The model is 15.66 GiB on a 16 GiB-RAM instance, so vLLM's auto-prefetch stays off and every shard read pays the S3 fetch cost.

Brief includes six ranked solutions. The user authored a four-layer architecture SPEC ([`team/humans/dinis_cruz/briefs/05/11/SPEC-slim-ami-s3-nvme.md`](../../humans/dinis_cruz/briefs/05/11/SPEC-slim-ami-s3-nvme.md)) — slim AMI + S3 artifact store + NVMe runtime cache + private-subnet posture. **That spec supersedes the brief's "proposed solutions" section.**

### 4. SPEC review

Reviewed [`SPEC-slim-ami-s3-nvme.md`](../../humans/dinis_cruz/briefs/05/11/SPEC-slim-ami-s3-nvme.md) and flagged five points before implementation begins:
1. **§7.2 fstab + instance store** — confirm `mkfs.xfs` runs on every fresh boot (instance store wiped on stop/start).
2. **§7.3 `default-runtime: nvidia`** — affects every `docker run`; non-GPU sidecars need `--runtime=runc`.
3. **§9.3 parameter source** — pin the schema additions (`artifact_bucket`, `model_s3_prefix`, `image_s3_key`) before the section is written.
4. **§13 step 5** — private-subnet move needs SSM interface endpoints (`ssm`, `ssmmessages`, `ec2messages` — ~$7/month/AZ each) listed alongside the S3 gateway endpoint, or `sg lc connect`/`exec` break.
5. **§13 missing item** — branch/PR boundaries for steps 1–6 (~6 PRs of work).

Spec is implementable as written; the five points are tightening, not blockers.

### 5. Benchmark setup for `ec2-boot-bench` (no code shipped this session)

Drafted the YAML config + pre-flight commands the user can run before implementing the spec. Project settings extracted from the codebase:

- Region: `eu-west-2`
- Instance profile: `playwright-ec2` (already has `AmazonSSMManagedInstanceCore` + ECR perms)
- Instance type (current default): `g5.xlarge`
- Subnet/SG: project uses **default VPC subnet** (no override in [`EC2__Launch__Helper.run_instance`](../../../sg_compute/platforms/ec2/helpers/EC2__Launch__Helper.py)) and per-stack SG keyed on caller IP — bench needs its own dedicated SG.

Five-comparison sweep matrix in the conversation transcript. The load-bearing comparison is **fat AMI vs AL2023** — confirms or denies whether lazy-load also slows the path-to-SSM-ready, which determines whether the slim AMI wins on cold-start time or only on model-load time.

---

## Failure classification

### Good failures

- **Sudoers missing → caught immediately.** User flagged `sudo: 1 incorrect password attempt` on the first `sg lc connect` after Bug A/I were fixed. Mechanism understood within one exchange; idempotent boot-time fix landed without needing to re-bake. Same class as Bugs H/I/J from the prior session (silent missing side-effect of a config file).
- **AMI cold-start surfaced by trying to use the AMI.** The previous session's milestone test was on the *bake* instance (which had a fully-warmed EBS volume); the regression only appeared on a *fresh* launch from the AMI. Visible immediately, root cause identified within minutes via the "Auto-prefetch disabled" log line.

### Bad failures

- **None this session.** The cold-start slowness is a design limitation surfaced by working code, not a bug introduced and silenced. The AMI itself is correct; what's wrong is the architecture choice of putting the model on EBS.

---

## Lessons learned

- **`/etc/sudoers.d/ssm-agent-users` is owned by the SSM Agent, not the OS.** Any time `ssm-user` exists before the first Session Manager session, the agent will not create the file. Pre-creating the user (a 2026-05-10 fix) is incompatible with relying on the agent for sudoers, so the boot script must own both.
- **EBS volumes from snapshot are lazy-loaded.** Documented AWS behaviour, but not obvious until it bites. The first-touch S3 fetch dominates any volume-class tuning (gp3 IOPS, io2 throughput) because the bottleneck is in the snapshot-restore path, not the EBS device. **Implication:** anything large that goes into an AMI pays this tax on every fresh launch.
- **g5.xlarge ships with 250 GB NVMe instance store** at ~3 GB/s, free with the instance. Wiped on stop/start, survives reboot. The right place for ephemeral data like model weights.
- **AWS SSM SendCommand requires `TimeoutSeconds ≥ 30`.** The previous-session Bug E. Still relevant — `extend()` uses 30s.
- **`systemd-run --on-active=Xs` creates `run-*.timer` transient units in `/run/systemd/transient/`** (tmpfs). They are not preserved across reboot, so the timer cannot be baked into an AMI — it must be re-armed by user-data on every boot. `max_hours` is per-launch, not per-AMI.

---

## Files changed this session

### New files
- `team/comms/briefs/v0.2.8__local-claude-ami-cold-start-perf.md` — performance bug brief (six ranked solutions; user-authored SPEC supersedes the proposed-solutions section)

### Modified files
- `sg_compute/platforms/ec2/helpers/EC2__Instance__Helper.py` — `update_tags()` added
- `sg_compute/platforms/ec2/user_data/Section__Base.py` — NOPASSWD sudoers + comment
- `sg_compute_specs/local_claude/cli/Cli__Local_Claude.py` — `extend` command

### Pulled in via merge (user-authored)
- `team/humans/dinis_cruz/briefs/05/11/SPEC-slim-ami-s3-nvme.md` — 501-line architecture spec (HUMAN-ONLY tree; do NOT edit)

### Tests
- No new tests this session. The new CLI verb and the boot-script line are both exercised by live-AWS smoke (no in-memory stack pattern reaches these layers).

---

## Test status

Not run this session. Both changes are on the live-AWS path:
- `sg lc extend` exercises real SSM SendCommand + EC2 `CreateTags` against a running instance.
- Sudoers fix runs inside the user-data script on boot.

The unit-test suites under `tests/` are unaffected by either change (no Python code path inside the FastAPI app changed). Pre-existing test status from the prior session's debrief still applies.

---

## Open questions

| # | Question | Recommendation | Alternatives |
|---|---|---|---|
| 1 | Run `ec2-boot-bench` before or in parallel with implementing the SPEC? | **Before.** The fat-vs-slim AMI comparison directly informs whether the slim AMI is a 2x or 5x cold-start improvement, which affects sequencing of the rollout plan in SPEC §13. | Run in parallel — risk: rework if data invalidates a sub-decision. |
| 2 | Which SPEC point should be tightened first — schema additions (§9.3) or network bill-of-materials (§13/§8)? | **Schema.** It's the contract that the new section + CLI wire to; everything else can land after. | Network first — only if the private-subnet move is itself the first PR. |
| 3 | Slim-AMI work behind a flag (`use_slim_ami: false` default per SPEC §13.3) or as a hard cutover? | **Flag, per the spec.** Keeps existing fat AMIs usable while the slim path is validated. | Cutover — only if the user is willing to lose the existing AMIs as a fallback. |

---

## Follow-ups (sized for next session)

### Must-do before merging this branch
- Nothing — branch already merged to `dev` via `6f932c77`.

### Open: benchmark step

**Run `ec2-boot-bench` against this project's setup.** Pre-flight + config + sweep matrix were drafted in the conversation transcript (the most recent assistant reply before this debrief). Required AWS-side steps:

1. Create a dedicated `ec2-boot-bench` SG in the default VPC (egress-only).
2. Pick a default subnet in `eu-west-2a` (or run per AZ).
3. Look up AL2023 AMI ID via SSM Parameter Store.
4. Use the existing `playwright-ec2` instance profile.

Five comparisons worth running (full table in transcript). The **load-bearing** one is **fat AMI (`ami-0b540a6e1c7b3297e`) vs AL2023** at `g5.xlarge`, ≥10 runs each. Output decides whether SPEC §10's "cold-start to vLLM 200" budget of <2 min is dominated by AWS provisioning floor or by avoidable boot-script work.

Output of the bench should be captured into a follow-up brief under `team/comms/briefs/` so the SPEC's acceptance criteria can be calibrated.

### Next big slice — implement the slim-AMI SPEC

Source of truth: [`team/humans/dinis_cruz/briefs/05/11/SPEC-slim-ami-s3-nvme.md`](../../humans/dinis_cruz/briefs/05/11/SPEC-slim-ami-s3-nvme.md). No plan file written yet — the spec is the plan. Suggested PR sequence per SPEC §13:

1. S3 bucket setup + upload scripts (§5)
2. Slim AMI bake (§6), no spec integration yet
3. `Section__S3_Artifact_Fetch.py` + schema additions (§9.3 — locked by open question #2)
4. Wire to `local-claude` behind `use_slim_ami` flag
5. Flip to default, then remove the fat-AMI path

### Smaller items / opportunistic cleanup

- The `extend` command could grow a `--at` absolute-time form (`--at 2026-05-11T18:00Z`) — low priority, only if user asks.
- `sg lc list` shows `time-left` in green/yellow/red; consider a similar visual on `info` for consistency.
- The fat AMIs (`ami-0b540a6e1c7b3297e` and the earlier one) should be deregistered once the slim path is validated — but keep them until the bench data is collected (§"Open: benchmark step").

---

## Where to start (if continuing this work)

Reading order for the next agent:

1. This file (you're here).
2. The user's **SPEC**: [`team/humans/dinis_cruz/briefs/05/11/SPEC-slim-ami-s3-nvme.md`](../../humans/dinis_cruz/briefs/05/11/SPEC-slim-ami-s3-nvme.md) — source of truth for the next slice.
3. The **bug brief**: [`team/comms/briefs/v0.2.8__local-claude-ami-cold-start-perf.md`](../../comms/briefs/v0.2.8__local-claude-ami-cold-start-perf.md) — for the diagnosis context. Note: its "proposed solutions" section is **superseded** by the SPEC; read for the diagnosis only.
4. The **prior-session debrief**: [`2026-05-10__local-claude-end-to-end-boot.md`](2026-05-10__local-claude-end-to-end-boot.md) — bugs D–J context, ssm-user lifecycle, milestone of first live Claude conversation on EC2.
5. **Code touchpoints**:
   - `sg_compute/platforms/ec2/user_data/Section__Base.py` — ssm-user creation, sudoers, timer block
   - `sg_compute/platforms/ec2/user_data/Section__Docker.py` — will be rewritten per SPEC §9.2
   - `sg_compute_specs/local_claude/service/Local_Claude__User_Data__Builder.py` — section composition (SPEC §9.5)
   - `sg_compute_specs/local_claude/schemas/Schema__Local_Claude__Create__Request.py` — where SPEC §9.3 schema fields land

**Don't bother reading** unless directly relevant:
- The earlier `2026-05-10__sg-compute-cli-ux-and-bug-fixes.md` debrief — fully superseded by the end-to-end-boot debrief.
- The `Spec__CLI__Builder.py` — already-stable contract for the standard verbs; the spec doesn't touch it.

**Critical files to NOT touch unless deliberately changing the contract:**
- `team/humans/dinis_cruz/` — HUMAN-ONLY (CLAUDE.md rule 23/24).
- `EC2__Instance__Helper.run_command` — the 200ms-polling, transient-error-handling logic was hard-won across three bugs in the prior session. Documented design principle: "no artificial sleeps in SSM retrieval."

---

## What to take into account next session

- **AWS region:** `eu-west-2`. All instance work is here. Spot capacity for `g5.xlarge` has been intermittent (saw `InsufficientInstanceCapacity` in the last session); plan for occasional fail-launches when benchmarking spot.
- **Existing AMIs to NOT deregister yet:** `ami-0b540a6e1c7b3297e` and the earlier fat AMI. Both are useful for the benchmark.
- **The user's SPEC file is HUMAN-OWNED.** Tightening points raised in the review (§4 above) should land as a separate doc under `team/comms/briefs/` or as commits on the spec only if the user invites it — not by editing the human-owned file.
- **`sg lc extend` updates an EC2 tag.** It's an EC2 API write, not just SSM. The `playwright-ec2` instance profile is not relevant here — the **caller's** IAM (running the CLI) needs `ec2:CreateTags`.
- **Branch convention:** rule 30 (`claude/{description}-{session-id}`) and rule 31 (no direct push to `dev`) still apply. This session's branch is merged; the next session starts from `dev`.
- **No reality-doc update was made.** Per the handover guide, that's the Librarian's role. Flag for the next Librarian session: `Section__Base` and `EC2__Instance__Helper` both gained surface area this session.
