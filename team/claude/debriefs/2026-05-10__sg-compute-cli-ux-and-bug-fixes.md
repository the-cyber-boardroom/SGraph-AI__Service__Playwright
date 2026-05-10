# 2026-05-10 — SG/Compute CLI hardening and boot reliability

**Branch:** `claude/sg-compute-continuation-Ko0RY`
**Commits ahead of dev:** 10
**Scope:** UX polish on `sg lc {create,list,info,diag,logs,exec}`; two real bugs fixed; one bug suspected but not yet confirmed (see Open Issues).

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

## Open Issues — for next Opus review

### 🔴 Issue 1 — `sg lc logs --source X` still returns empty (post-fix)

**Reproduction (steady-maxwell, observed by the user after Bug B was fixed):**
```
sg lc logs --source cloud-init   # empty
sg lc logs --source boot          # empty
sg lc logs --source docker        # empty
sg lc exec docker ps              # works (header table, 2782ms)
sg lc exec docker logs            # works but empty stdout (5670ms)
```

**Hypothesis A — `InvocationDoesNotExist` is being swallowed by the outer try/except.**

The polling fix in `EC2__Instance__Helper.run_command` (commit `2ddb7836`) has this structure:

```python
try:
    resp = ssm.send_command(...)
    command_id = resp.get('Command', {}).get('CommandId', '')
    deadline = time.monotonic() + timeout_sec
    inv = {}
    time.sleep(1)
    while time.monotonic() < deadline:
        inv = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
        if inv.get('StatusDetails', '') not in _PENDING:
            break
        time.sleep(2)
    return inv.get('StandardOutputContent', '').strip()
except Exception:
    return ''
```

After `send_command`, there's a brief propagation window where `get_command_invocation` raises `InvocationDoesNotExist`. If the first call (after `time.sleep(1)`) hits that, the **outer** `except Exception: return ''` catches it and the entire function returns empty silently — even though the command itself might run successfully on the instance moments later. The old `time.sleep(3)` happened to give enough propagation time. `time.sleep(1)` does not on a busy instance.

Why this could explain the user's data: under boot pressure SSM is slower to propagate; `docker ps` calls happen to NOT hit the exception (or it propagates slightly faster the second time around), but consecutive `tail` / `journalctl` calls hit the window.

**Proposed fix (NOT YET IMPLEMENTED — verify on a live instance first):**

```python
try:
    resp = ssm.send_command(...)
    command_id = resp['Command']['CommandId']
    deadline = time.monotonic() + timeout_sec
    inv = {}
    time.sleep(1)
    while time.monotonic() < deadline:
        try:
            inv = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
            if inv.get('StatusDetails', '') not in _PENDING:
                break
        except Exception:
            pass                       # InvocationDoesNotExist or transient — keep polling
        time.sleep(2)
    return inv.get('StandardOutputContent', '').strip()
except Exception:
    return ''
```

The inner `try`/`except` lets propagation lag be retried; the outer `except` only catches genuine send_command failures.

**Hypothesis B — log files don't exist on this instance.**

If the boot script crashed after Docker install (e.g. nvidia-container-toolkit install failed under `set -euo pipefail`), the boot would set `/var/lib/sg-compute-boot-failed` but the log file at `/var/log/ephemeral-ec2-boot.log` might or might not contain content depending on when the failure happened relative to the `exec > >(tee -a ...)` redirect. The `tail` command then writes "cannot open" to stderr and exits non-zero with empty stdout.

**Investigation steps for next session (before touching code):**

```bash
# 1. confirm file existence
sg lc exec ls -la /var/log/ephemeral-ec2-boot.log /var/log/cloud-init-output.log

# 2. confirm size
sg lc exec wc -l /var/log/ephemeral-ec2-boot.log

# 3. confirm whether the boot is marked failed
sg lc exec test -f /var/lib/sg-compute-boot-failed && echo YES || echo NO
sg lc exec test -f /var/lib/sg-compute-boot-ok    && echo YES || echo NO

# 4. confirm journalctl works at all
sg lc exec "journalctl -n 5 --no-pager"
sg lc exec "systemctl is-active docker"
```

If files exist with content but `sg lc logs --source boot` still returns empty → Hypothesis A is confirmed, apply the inner-except fix.

If files are absent or zero-bytes → Hypothesis B is confirmed; need to revisit boot script error handling (the `trap ... ERR` may not be firing reliably, or the boot is dying before `exec > >(tee ...)`).

### 🟡 Issue 2 — `Schema__CLI__Exec__Result.exit_code` is never populated

`Spec__Service__Base.exec()` sets `stdout`, `transport`, `duration_ms` — but **not** `exit_code`. `render_exec_result` always shows `exit=0`, regardless of whether the command actually succeeded. To populate it properly, `EC2__Instance__Helper.run_command` would need to return both stdout and exit code (from the invocation's `ResponseCode`), and the signature would need to change. Not urgent but misleading.

### 🟢 Issue 3 — Advanced-options pattern not applied to other specs

The 5-tuple `(name, type, default, help, advanced=True)` was added in `Spec__CLI__Builder` and is used by local-claude only. open-design, elastic, ollama etc. still expose every option in `--help`. Mechanical follow-up.

---

## Next-session touchpoint (for the reviewing Opus instance)

When you (Opus) pick this up next:

1. **Read this file first.** It supersedes any earlier session notes about `sg lc diag` / `sg lc logs` / `Section__Docker.py` / `run_command`.
2. **Issue 1 is the priority.** Start by asking the user to run the four investigation commands listed above against whatever stack they currently have running. The fix is either (a) the inner-except patch (one file, ~3 lines) or (b) a boot-script issue further upstream. Don't apply the inner-except patch blind — confirm with the diagnostic commands first.
3. **Issue 2 is a quick win.** Read `ResponseCode` from the invocation, return a `(stdout, exit_code)` tuple from `run_command`, set both on `Schema__CLI__Exec__Result`. About 20 LOC across two files.
4. **Issue 3 is "in the spirit"** of the session but not blocking. Wait for the user to ask.
5. **The `diag` generator pattern is reusable.** If the user asks for the same live-check experience on another spec (open-design, elastic), the playbook is: convert their existing health/status function into a generator yielding `(name, 'checking', '')` then `(name, status, detail)`, and copy `_DIAG_ICONS` / `_DIAG_HINTS` from `Cli__Local_Claude.py`.

---

## Failure classification

| Bug | Class | Why |
|-----|-------|-----|
| A — Section__Docker deadlock | **Good** | Surfaced quickly by diag transparency; root cause traced via cloud-init log; clean fix. |
| B — run_command race | **Good** (now) | Was a **bad failure** for years (silent empty returns) until diag transparency exposed it. Now caught with explicit polling. |
| Issue 1 — empty logs after fix | **Bad (open)** | The fix for B may have re-introduced silent empty returns via the outer try/except in a different code path. Needs verification. |
| Issue 2 — exit_code never set | **Bad (open)** | Misleading display, no caller can trust the exit code. |

Confidence on Issue 1 root cause: ~60% Hypothesis A, ~30% Hypothesis B, ~10% something else. The investigation commands cleanly discriminate.
