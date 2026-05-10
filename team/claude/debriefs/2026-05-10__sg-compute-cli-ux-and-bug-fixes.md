# 2026-05-10 — SG/Compute CLI hardening and boot reliability

**Branch:** `claude/sg-compute-continuation-Ko0RY`
**Commits ahead of dev:** 12
**Scope:** UX polish on `sg lc {create,list,info,diag,logs,exec}`; three real bugs fixed (Bug A, Bug B, Bug C); one principle established: SSM retrieval should not use artificial sleeps.

---

## What we set out to do

The user reported that `sg lc create ...` would print a banner showing only the overrides (and `--no-wait`), but not the full set of configurable parameters. From there, the session expanded into:

1. Make the **create preview banner** truly self-documenting (auto-detect labels, full equivalent command, no line wrapping, advanced/hidden flags).
2. Make **`sg lc diag`** transparent during boot — live per-check indicator, suggested next steps with copy-paste log commands, downgrade mid-boot non-failures from fail to warn, surface the latest boot stage marker.
3. Make **`sg lc logs`** ergonomic — bump default `--tail`, add `--follow`/`-f`.
4. Make **`sg lc exec`** flexible — accept unquoted multi-word commands and auto-resolve stack name.
5. Track **time-left** for ephemeral instances — tag at create, surface in list/info.

Along the way, two real bugs were discovered (one of which had been masking the other for the whole session).

---

## Commits (oldest → newest)

| # | SHA | Title |
|---|-----|-------|
| 1 | `4b857c21` | fix(create-preview): show auto-labels for empty ami/caller-ip; expand equivalent command to all params |
| 2 | `06767ad7` | feat(diag): add 'Suggested next steps' with copy-paste log commands after failures/warnings |
| 3 | `ad2b5c48` | Merge remote-tracking branch 'origin/dev' (SG_BANNER ASCII art conflict resolved) |
| 4 | `0a8cf017` | fix(diag): downgrade mid-boot non-failures from fail→warn; improve docker-access message |
| 5 | `dcd642f1` | feat: --mh alias, no-wrap equivalent cmd, TerminateAt tag, time-left in list/info |
| 6 | `d3583152` | feat(cli): hide advanced options from --help and equivalent command by default |
| 7 | `9cf25292` | feat(diag/logs): show last boot stage marker instead of dnf noise; bump logs default tail to 300 |
| 8 | `f2ecfad1` | fix(docker/exec): background ssm-user wait; exec accepts unquoted multi-word commands |
| 9 | `5ba2e82a` | feat(logs): add --follow/-f flag to poll for new log lines (Ctrl-C to stop) |
| 10 | `2ddb7836` | fix(ssm): poll until terminal state instead of sleeping 3s then giving up |
| 11 | `dd9810be` | docs(debrief): SG/Compute CLI UX hardening session + open issues for next review |
| 12 | `94ff8230` | fix(ssm/logs): drop pre-poll sleep; tight 200ms polling; handle InvocationDoesNotExist; show SSM command |

---

## Bugs fixed

### Bug A — `Section__Docker.py` boot deadlock (commit `f2ecfad1`) — **GOOD FAILURE**

**Before:**
```bash
until id ssm-user >/dev/null 2>&1; do sleep 2; done
usermod -aG docker ssm-user
```

`ssm-user` is created by the SSM agent on the first **Session Manager** session — NOT by SSM SendCommand (which is what `sg lc exec` uses). On any instance never opened via `aws ssm start-session`, the boot script hung in this loop forever, never reaching nvidia-container-toolkit / sgit / docker pull / vLLM start.

**Fix:** moved the wait-and-group-add into a backgrounded subshell with a 5-minute timeout. The main boot script proceeds immediately. If ssm-user appears later (because someone opens a Session), it gets added to the docker group asynchronously.

**Why it's a good failure:** surfaced by the diagnostic transparency work — `diag` showed `boot-ok: warn` indefinitely, which forced investigation of the boot log → cloud-init log → identified the stalled spot.

### Bug B — `EC2__Instance__Helper.run_command` race (commit `2ddb7836`) — **MASKING BUG**

**Before:**
```python
time.sleep(3)
inv = ssm.get_command_invocation(...)
return inv.get('StandardOutputContent', '').strip()
```

If the command was still `InProgress` at the 3-second mark, `StandardOutputContent` was empty and the function silently returned `''`. This worked fine on **deadlocked (idle)** instances — `tail`, `journalctl`, `docker ps` all completed in under a second. On a **properly booting** instance running `dnf update` + GPU + Docker work, SSM commands routinely took 5–15s and **every diag check returned empty**.

The bug had been masking Bug A throughout the session: as soon as we fixed Bug A and the new instance actually started running real boot work, the diag output went completely blank.

**Fix:** poll `get_command_invocation` every 2s until status leaves `{Pending, InProgress, Delayed}`, capped by the caller-supplied `timeout_sec` (now correctly threaded through from `Spec__Service__Base.exec()`).

**Why it's the masking bug:** all diagnostic decisions were trusted to return either content or an error. Silent `''` returns invalidated every fail/warn/skip decision in `diag`.

### Bug C — `InvocationDoesNotExist` swallowed by outer try/except (commit `94ff8230`) — **GOOD FAILURE (caught immediately)**

**Discovered:** as Open Issue 1 in the previous version of this debrief; the user reported that after Bug B was fixed, `sg lc logs --source X` still returned empty even though `sg lc exec docker ps` worked.

**Cause:** the Bug B fix had this shape:

```python
try:
    resp = ssm.send_command(...)
    command_id = resp['Command']['CommandId']
    deadline = time.monotonic() + timeout_sec
    inv = {}
    time.sleep(1)                                          # ← problem 1: artificial pre-poll wait
    while time.monotonic() < deadline:
        inv = ssm.get_command_invocation(...)             # ← problem 2: raises InvocationDoesNotExist
        if inv.get('StatusDetails') not in _PENDING:       #              during propagation lag
            break
        time.sleep(2)                                      # ← problem 3: too coarse for fast tail
    return inv.get('StandardOutputContent', '').strip()
except Exception:                                          # ← problem 4: catches the propagation
    return ''                                              #              exception and returns '' silently
```

After `send_command`, AWS takes a brief moment (sometimes >1s on a busy instance) before `get_command_invocation` can find the new invocation. Until then it raises `InvocationDoesNotExist`. The outer `except` caught that and returned `''` even though the command itself would have completed successfully moments later. `docker ps` happened to skip this window; `tail` and `journalctl` consistently hit it.

**Fix:** restructured `run_command` so:
- the outer `try`/`except` only wraps `send_command` itself (so failures there still return `''`),
- the polling loop has its own inner `try`/`except` that treats `InvocationDoesNotExist` (and any transient `get_command_invocation` failure) as "keep polling",
- the artificial `time.sleep(1)` pre-poll is removed entirely,
- the poll interval is tightened from `2s` to `200ms`,
- early-exit on terminal status returns the result directly from inside the loop.

**Why it's a good failure:** the previous debrief flagged this as the prime suspect with discriminator commands listed. The user asked for the fix directly without needing those commands — and was right that artificial sleeps in log retrieval are an anti-pattern.

---

## Design principle — established this session

> **SSM retrieval should not use artificial sleeps. Log retrieval should be as close to a clean direct file read as the transport allows.**

User's words (paraphrased):
> "I really don't like any time.sleep(1) in the logs retrievals. Those should be clean and direct log file reads from the host. Also show the user which log we're reading and which command was used to read it."

Practical implications for any future SSM-using code:
- Never `sleep` **before** the first `get_command_invocation` call. Poll immediately and treat `InvocationDoesNotExist` as transient.
- Poll at sub-second intervals (200 ms is the chosen value), not seconds — boto3 calls are cheap relative to perceived latency on a CLI.
- The outer `try`/`except` may only wrap genuine fatal paths (i.e. `send_command` itself). Polling errors are not fatal.
- The CLI command that uses SSM must **show** the exact shell invocation being sent, so the user can see what was read and reproduce it manually if needed (`logs` now prints `via SSM: <cmd>` before output).

### Future direction (not in scope this session)

Within SSM SendCommand the polling is fundamental — there is no synchronous run-and-return endpoint. The only way to get truly stream-shaped log retrieval is to bypass SendCommand entirely. Two viable longer-term options:

1. **CloudWatch Logs** — boot script ships log files to a per-stack log group; CLI reads via `cloudwatch-logs:GetLogEvents` (synchronous, paginated, supports follow). Requires the CloudWatch agent on the instance and IAM grants on the role. Standard pattern for ephemeral fleets.
2. **Tiny HTTP log server on the instance + SSM port-forward** — `sg lc logs` opens an SSM tunnel, hits `GET /logs/boot?tail=300`, server returns it. More setup, more moving parts, but cleanest UX (SSE for `--follow`).

Either would obsolete the 200ms-polling pattern for log retrieval specifically. `exec` would still use SendCommand because arbitrary one-shot commands don't fit either pattern as cleanly.

---

## Feature increments (no bug; just UX)

### Create preview banner (`Spec__CLI__Renderers__Base.py`)

- `_AUTO_LABELS = {'ami': '(auto-resolve)', 'caller_ip': '(auto-detect)'}` for empty fields.
- Equivalent command lists **all** params, not just overrides — copy-paste reproduces the launch.
- `no_wrap=True` on the cyan equivalent-command line (long commands no longer hard-wrap mid-flag).
- 5-tuple `extra_create_options` format. Optional 5th element `True` marks the option as advanced:
  - `hidden=True` in the typer Option → absent from `--help`
  - Skipped from the equivalent command when at default
  - Footer counts the omitted advanced options
- local-claude marks `served_model_name`, `tool_parser`, `max_model_len`, `kv_cache_dtype`, `gpu_memory_utilization` as advanced.

### `sg lc diag` (`Local_Claude__Service.diagnose()` + `Cli__Local_Claude.diag`)

- Generator now yields `(name, 'checking', '')` sentinel before each SSM call so the CLI can show a live `···  name  checking…\r` indicator (erased with `\r\033[K` when the result arrives).
- When `boot-ok` is warn (boot still running):
  - `vllm-container` is **warn** ("not yet — docker pull pending") instead of fail.
  - `docker-access` with ssm-user-not-found is **warn** ("not yet — ssm-user not created by SSM agent yet") instead of confusing "permission denied".
- `boot-ok` warn detail now greps `/var/log/ephemeral-ec2-boot.log` for the latest `[sg-compute]` / `[ephemeral-ec2]` echo marker. Far more useful than the raw dnf tail.
- `_DIAG_HINTS` table maps each fail/warn check name → suggested `sg lc logs ... --source X` commands, deduplicated and printed under "Suggested next steps:".

### `sg lc logs`

- Default `--tail` raised 100 → 300 (boot easily exceeds 100 lines before `docker pull`).
- `--follow` / `-f` flag: polls every 4s, prints only new lines, uses last-line-seen as anchor for delta detection, Ctrl-C to stop.

### `sg lc exec`

- Changed signature from `(name: str, command: str)` to `(args: List[str])`.
- Logic: `list_stacks` once; if `len(args) > 1` and `args[0]` matches a known stack name, split there; otherwise auto-resolve and join all args as the command.
- All three forms work:
  - `exec lean-euler docker images` (explicit)
  - `exec docker images` (auto-resolve, unquoted)
  - `exec "docker ps -a"` (quoted, legacy)

### `time-left` everywhere (`Schema__Local_Claude__Info` + mapper + renderers)

- `create_stack` writes `TerminateAt=<ISO-UTC>` EC2 tag when `max_hours > 0`.
- Schema gains `terminate_at: str` and `time_remaining_sec: int`.
- Mapper parses the tag and computes seconds remaining at read time.
- `render_list` adds a `time-left` column (green / yellow / red by urgency).
- `render_info` adds `terminate-at` and `time-left` rows.

### Misc

- `--mh` short alias for `--max-hours` on every spec's `create`.
- Stale `python3.12` → `python3.13` in the `--with-sgit` help text.

---

## Open Issues — for next session

### ✅ Issue 1 — RESOLVED in `94ff8230` (kept for history)

Previously: `sg lc logs --source X` returned empty while `sg lc exec docker ps` worked. Root cause was `InvocationDoesNotExist` raised during the SSM propagation window being swallowed by the outer `try`/`except` in `run_command` and returning `''` silently. Fixed by moving polling errors into an inner `try`/`except` (transient), removing the artificial pre-poll `time.sleep(1)`, and tightening the poll interval to 200 ms. See Bug C above.

If logs still return empty on a new instance, fall back to the diagnostic commands below — they discriminate "polling regression" from "log file genuinely missing":

```bash
sg lc exec ls -la /var/log/ephemeral-ec2-boot.log /var/log/cloud-init-output.log
sg lc exec wc -l /var/log/ephemeral-ec2-boot.log
sg lc exec test -f /var/lib/sg-compute-boot-failed && echo YES || echo NO
sg lc exec test -f /var/lib/sg-compute-boot-ok    && echo YES || echo NO
sg lc exec "journalctl -n 5 --no-pager"
sg lc exec "systemctl is-active docker"
```

If those commands all return content but `sg lc logs` is still empty, the polling fix has regressed. If files are missing/empty → boot script crashed before `exec > >(tee ...)` ran; investigate the `trap ... ERR` and the order of operations in `Section__Base`.

### 🟡 Issue 2 — `Schema__CLI__Exec__Result.exit_code` is never populated

`Spec__Service__Base.exec()` sets `stdout`, `transport`, `duration_ms` — but **not** `exit_code`. `render_exec_result` always shows `exit=0`, regardless of whether the command actually succeeded. To populate it properly, `EC2__Instance__Helper.run_command` would need to return both stdout and exit code (from the invocation's `ResponseCode`), and the signature would need to change. Not urgent but misleading.

### 🟢 Issue 3 — Advanced-options pattern not applied to other specs

The 5-tuple `(name, type, default, help, advanced=True)` was added in `Spec__CLI__Builder` and is used by local-claude only. open-design, elastic, ollama etc. still expose every option in `--help`. Mechanical follow-up.

---

## Next-session touchpoint

When the next session (any model) picks this up:

1. **Read this file first.** It supersedes any earlier session notes about `sg lc diag` / `sg lc logs` / `Section__Docker.py` / `run_command`.
2. **Verify Bug C fix on a live instance.** Launch a stack, immediately run `sg lc logs --source boot` (no wait). The output should now begin with `via SSM: tail -n 300 /var/log/ephemeral-ec2-boot.log` and then show the actual boot log content. If it still comes back empty on a freshly-created instance, drop into the discriminator commands listed under Issue 1 — the polling fix has regressed, or it's a Hypothesis B (log file missing) situation.
3. **Issue 2 is a quick win.** `Spec__Service__Base.exec()` sets `stdout` but never `exit_code`. Read `ResponseCode` from the invocation in `run_command`, return a `(stdout, exit_code)` tuple, set both on `Schema__CLI__Exec__Result`. About 20 LOC across two files (`EC2__Instance__Helper.py` + `Spec__Service__Base.py`). Also `render_exec_result` colors non-zero exit codes.
4. **Issue 3 — propagate the advanced-options pattern.** open-design / elastic / ollama / podman etc. still expose every option in `--help`. Mark the rarely-touched ones (model-tuning knobs, low-level docker flags, etc.) with the 5th-element `True` flag. Mechanical.
5. **Honour the new design principle.** When adding any new SSM-backed command, do NOT introduce artificial sleeps. Poll tightly, handle `InvocationDoesNotExist` as transient, and surface the actual shell invocation to the user. The `run_command` rewrite in commit `94ff8230` is the canonical pattern.
6. **The `diag` generator pattern is reusable.** If the user asks for the same live-check experience on another spec (open-design, elastic), the playbook is: convert their existing health/status function into a generator yielding `(name, 'checking', '')` then `(name, status, detail)`, and copy `_DIAG_ICONS` / `_DIAG_HINTS` from `Cli__Local_Claude.py`.
7. **Longer-term option for log retrieval.** CloudWatch Logs or a tiny on-instance HTTP server + SSM port-forward would replace polling with true streaming. Don't pursue unless the user explicitly asks — both add operational surface area.

---

## Failure classification

| Bug | Class | Why |
|-----|-------|-----|
| A — Section__Docker deadlock | **Good** | Surfaced quickly by diag transparency; root cause traced via cloud-init log; clean fix. |
| B — run_command race | **Good** (now) | Was a **bad failure** for years (silent empty returns) until diag transparency exposed it. Caught with explicit polling. |
| C — InvocationDoesNotExist swallowed | **Good** | Caught in the same session it was introduced. Previous debrief version flagged it as the prime hypothesis; fix landed without needing diagnostic commands. |
| Issue 2 — exit_code never set | **Bad (open)** | Misleading display, no caller can trust the exit code. |
| Issue 3 — advanced-options not propagated | **Open (not a bug)** | Mechanical follow-up. |

The session's lasting lesson: **silent empty returns in SSM glue code are far more dangerous than visible exceptions**, because they break every layered diagnostic that assumes content-or-error semantics. Three of the bugs in this debrief (B, C, and the original Bug A symptom) share that root cause.
