# 2026-05-10 — local-claude end-to-end boot + first live Claude conversation on EC2

**Branch:** `claude/sg-compute-continuation-Ko0RY`
**Commits this session:** 8 (continues prior debrief `2026-05-10__sg-compute-cli-ux-and-bug-fixes.md`)
**Cumulative commits ahead of `dev`:** 20

> **🚀 MILESTONE:** This is the **first successful end-to-end automated build** in which a user opened a live Claude Code conversation on an EC2 instance produced by `sg lc create`, talking to a vLLM-served local model. The screenshots Dinis shared show Claude reading the file it had just written and executing `python3 reverse_string.py` against the local model — with only one residual manual step (running `curl … | bash` to install the Claude Code CLI binary on the instance, because the `claude-code-firstboot` systemd unit was buggy until the very last commit of this session).

---

## What we set out to do

Continue the Opus review of the prior session's two open issues, smoke-test the boot end-to-end on real AWS, and squash whatever surfaced.

The "whatever surfaced" turned out to be **six more bugs**, all variations of the same root cause that has haunted this branch from the start: **silent empty returns / silent missing side-effects in glue code**. Each fix took the system one step closer to a working boot. The final commit closed the loop with the first live conversation.

---

## Commits (oldest → newest)

| # | SHA | Title |
|---|-----|-------|
| 1 | `7ac4bcac` | fix(exec): populate exit_code from SSM ResponseCode; propagate advanced-options to ollama |
| 2 | `d3928704` | docs(debrief): mark Issue 2 and Issue 3 resolved |
| 3 | `8b4333fc` | fix(ssm): preserve exit_code 0 instead of coercing to -1 (Opus review catch) |
| 4 | `a786a227` | fix(logs): bump `_LOG_SOURCES` timeouts ≥ AWS SSM minimum of 30; surface send_command errors |
| 5 | `545b061a` | fix(boot): pre-create ssm-user in `Section__Base`; remove blocking `until id ssm-user` waits |
| 6 | `0730a5dc` | fix(boot): `sgit`→`sgit-ai` PyPI name; drop ssm-user docker group; bump diag/health SSM timeouts |
| 7 | `1141a870` | fix: three bugs preventing Claude Code from being found after boot |
| 8 | `abf14ea9` | feat: bake `--dangerously-skip-permissions` into local-claude launcher |

---

## Bugs fixed

### Bug D — `exit_code 0` coerced to `-1` via Python falsy-or (commit `8b4333fc`) — **GOOD FAILURE (review)**

`7ac4bcac` first wired `exit_code` through from SSM `ResponseCode`. The original line:

```python
int(inv.get('ResponseCode', -1) or -1)
```

evaluated to `-1` for **every successful command** because `0 or -1 == -1` (zero is falsy). Caught in Opus's code review of the same session's commit, before any live run.

**Fix:**
```python
rc = inv.get('ResponseCode')
return (..., int(rc) if rc is not None else -1)
```

Lesson: never use `value or default` to coerce a numeric field whose valid range includes zero. Use an explicit `is None` check.

### Bug E — AWS SSM `TimeoutSeconds < 30` silently violated (commit `a786a227`) — **MASKING BUG → GOOD FAILURE**

Dinis hit this: `sg lc logs --source boot` returned empty even on a healthy instance, while the literal equivalent `sg lc exec "tail -n 300 /var/log/ephemeral-ec2-boot.log"` returned content.

**Root cause:** boto3's `ssm.send_command` rejects `TimeoutSeconds < 30` with a client-side `ParamValidationError`. The whole `_LOG_SOURCES` table used `20` and the `diagnose()` helper used `12`. boto3's API shape metadata makes this explicit:

```python
ssm.meta.service_model.operation_model('SendCommand') \
   .input_shape.members['TimeoutSeconds'].metadata
# → {'min': 30, 'max': 2592000}
```

The exception was raised **client-side**, before any HTTP call, and the outer `try/except` in `run_command` caught it and returned `('', -1)` silently. Same shape as Bugs B and C from the previous debrief.

**Fix:**
- Every `_LOG_SOURCES` timeout bumped to `60`.
- Every `Local_Claude__Service.diagnose()` / `health()` SSM call bumped to ≥30.
- `run_command`'s exception handler now **prints to stderr** (`[run_command] send_command failed: <type>: <msg>`) so future occurrences of this class of bug surface immediately instead of vanishing.

Lesson: when a boto3 method silently does nothing, check the operation's `input_shape.members[...].metadata` for `min`/`max` constraints. The service model is authoritative; the docstrings often aren't.

### Bug F — `until id ssm-user` deadlock reappeared in two more sections (commit `545b061a`) — **BAD FAILURE (regression)**

The previous debrief's Bug A only fixed `Section__Docker.py`. Two more sections had the same blocking pattern:

- `Section__SGit_Venv.py` — `until id ssm-user >/dev/null 2>&1; do sleep 2; done`
- `Section__Claude_Code__Firstboot.py` — same pattern in `_HEADER`

Boot would stall indefinitely at one of these waits because `ssm-user` is created by SSM **Session Manager** (interactive `start-session`), not SSM **SendCommand**. When Dinis SSM-attached to a stalled instance, the act of attaching created `ssm-user` and unblocked the script — perfectly mimicking the original Bug A symptom from `Section__Docker.py`.

**Fix:**
- `Section__Base` now **pre-creates ssm-user up front**:
  ```bash
  id ssm-user >/dev/null 2>&1 || useradd ssm-user -m -d /home/ssm-user -s /bin/bash
  echo "[ephemeral-ec2] ssm-user ensured (uid=$(id -u ssm-user))"
  ```
- Removed the blocking waits from `Section__SGit_Venv.py` and `Section__Claude_Code__Firstboot.py`.

Lesson: when a piece of state is needed by multiple sections, **establish it in `Section__Base`** once instead of having every section wait for it.

### Bug G — `pip install sgit` package name wrong (commit `0730a5dc`) — **GOOD FAILURE (boot log)**

After Bug F was fixed and `Section__SGit_Venv.py` actually ran, boot failed at:

```
ERROR: Could not find a version that satisfies the requirement sgit
```

The PyPI package name is `sgit-ai`; the binary it installs is still `sgit`. Dinis verified manually with `pip3.12 install sgit-ai` → working `/home/ssm-user/.local/bin/sgit`.

**Fix:** `pip install sgit` → `pip install sgit-ai` in `Section__SGit_Venv.py`.

Under `set -euo pipefail` the failing pip aborted the whole boot script (triggering the ERR trap → `/var/lib/sg-compute-boot-failed`), so the misnamed package was masquerading as a generic "boot FAILED" until we read the boot log.

### Bug H — `claude-code-firstboot` systemd unit `enable` without `--now` (commit `1141a870`) — **BAD FAILURE**

The `_FOOTER` of `Section__Claude_Code__Firstboot` did:

```bash
systemctl enable claude-code-firstboot.service
```

`systemctl enable` only creates the wants-symlink. `WantedBy=multi-user.target` then schedules the unit for **next boot** — but `multi-user.target` is already active by the time user-data runs. Result: the install script never executed during first-boot. Claude Code was never installed on any instance produced by this builder, ever.

**Fix:** `systemctl enable --now claude-code-firstboot.service`.

This is the bug that made Dinis's `~/local-llm-claude.sh` produce `exec: claude: not found` on `clever-bohr`. He worked around it by `curl -fsSL https://claude.ai/install.sh | bash` inside the SSM session.

### Bug I — `sudo touch /var/lib/claude-code-installed` run as `ssm-user` without sudo rights (commit `1141a870`) — **BAD FAILURE**

The old systemd unit was:

```ini
[Service]
Type=oneshot
User=ssm-user
Group=ssm-user
ExecStart=/bin/bash -lc 'curl -fsSL https://claude.ai/install.sh | bash && sudo touch /var/lib/claude-code-installed'
```

SSM Agent only writes `/etc/sudoers.d/ssm-agent-users` (granting ssm-user sudo) on the **first interactive start-session**. Inside a oneshot unit, ssm-user has no sudo. The `sudo touch` would fail; the marker would never appear; the unit would be re-evaluated on every boot (no idempotency).

**Fix:** unit now runs as **root**; uses `su - ssm-user -c "..."` for the install (so the installer sees ssm-user's login shell and `$PATH`); writes the marker as root after success:

```ini
[Service]
Type=oneshot
ExecStart=/bin/bash -c 'su - ssm-user -c "curl -fsSL https://claude.ai/install.sh | bash" && touch /var/lib/claude-code-installed'
RemainAfterExit=yes
```

### Bug J — `exec claude` fails in non-login SSM sessions (commit `1141a870`) — **BAD FAILURE**

The Anthropic installer puts `claude` in `~/.local/bin/` (or `~/.npm-global/bin/`). A login shell sources `.bash_profile` which adds these to `$PATH`. An **SSM session** is non-login. So even when claude **is** installed, `~/local-llm-claude.sh` fails:

```
/home/ssm-user/local-llm-claude.sh: line 17: exec: claude: not found
```

**Fix:** prepend the canonical user-bin locations in the launcher itself:

```bash
export PATH="$HOME/.local/bin:$HOME/.npm-global/bin:$HOME/bin:$PATH"
exec claude --dangerously-skip-permissions "$@"
```

---

## Architectural / UX changes

### `Section__Base` now owns ssm-user creation (commit `545b061a`)

Three previously independent sections all needed ssm-user. Each had its own blocking wait. Now `Section__Base` ensures the user exists before any subsequent section runs:

```bash
# Pre-create ssm-user so sections that write to /home/ssm-user/ never block.
# SSM Session Manager creates this user on the first interactive session; SSM
# SendCommand (used by `sg lc exec`) does NOT. Pre-creating ensures the boot
# script can install Claude Code config / sgit venv / etc. on any instance,
# regardless of whether anyone ever opens a Session Manager session.
id ssm-user >/dev/null 2>&1 || useradd ssm-user -m -d /home/ssm-user -s /bin/bash
```

### Dropped ssm-user from the docker group (commit `0730a5dc`)

Dinis's call: the convenience of `docker ps` without `sudo` for ssm-user is not worth the side effects — adding ssm-user to the docker group grants effective root via `docker run -v /:/host`. Removed the backgrounded subshell from `Section__Docker.py` and the dependent `docker-access` diag check.

`Section__Docker.render()` now contains an inline comment explaining the security reasoning so the next agent doesn't re-add it:

```bash
usermod -aG docker ec2-user  || true
# Note: ssm-user is intentionally NOT added to the docker group
# Side effects (effective root via docker run -v /:/host) outweigh convenience.
```

### `diag` is now 8 checks, not 9 (commit `0730a5dc`)

`docker-access` removed. Order is now: `ec2-state → ssm-reachable → boot-failed → boot-ok → docker → gpu → vllm-container → vllm-api`. `_DIAG_HINTS`, the skip lists in `diagnose()`, the CLI docstring, and `test_diagnose_returns_eight_checks` were all updated together.

### All SSM timeouts unified at ≥30s (commits `a786a227`, `0730a5dc`)

Touched paths: `_LOG_SOURCES`, `Local_Claude__Service.diagnose()` ssm() default, `health()` boot-failed and curl checks, `vllm-api` curl. **The AWS minimum is now treated as a hard floor everywhere SSM SendCommand is called from this codebase.**

### `--dangerously-skip-permissions` baked into the launcher (commit `abf14ea9`)

On a private single-user EC2 instance the per-command approval prompts are noise. The launcher now skips them by default so Claude runs non-interactively:

```bash
exec claude --dangerously-skip-permissions "$@"
```

User can still pass extra args via `"$@"` if they want.

---

## The recurring theme — silent missing side-effects

Every bug in this session (and most of the prior session) traces back to the same shape: **a piece of glue code fails or no-ops, and nothing surfaces the failure.** The catalogue so far:

| Bug | Silent failure mode |
|-----|---------------------|
| Prior B | `time.sleep(3)` + single `get_command_invocation` returned `''` if still InProgress |
| Prior C | `InvocationDoesNotExist` swallowed by outer try/except → `''` |
| D | `0 or -1 = -1` silently masked successful exit codes |
| E | `ParamValidationError(TimeoutSeconds < 30)` swallowed → `('', -1)` |
| F | `until id ssm-user` blocking wait — boot just stops, no error |
| G | `pip install sgit` failed under `set -e` — boot trapped, no surface beyond `boot FAILED` |
| H | `systemctl enable` (no `--now`) — service exists but never ran |
| I | `sudo touch` as ssm-user — marker never written, unit re-runs every boot |
| J | `exec claude` in non-login shell — `PATH` missing, "command not found" looks like install failure |

**The defensive posture established this session:**

1. Outer `try/except` in transport code **must surface to stderr**, not swallow to `''`. (`run_command` does this now.)
2. Numeric coercions must use `is None` checks, never `or`.
3. AWS service-shape constraints (`TimeoutSeconds` min, name-prefix rules, etc.) are first-class — read them from the service model, don't trust prose.
4. `systemctl enable` is almost always wrong; use `enable --now` unless you specifically want a next-boot effect.
5. `User=` in a systemd unit gives that user **no sudo**. Run units as root and use `su - <user>` for the unprivileged work.
6. Launchers that `exec` an installed binary must set `$PATH` explicitly. Don't trust the surrounding shell.
7. State needed by multiple sections is established **once** in `Section__Base`, not waited-for in every section.

---

## Live verification

Dinis ran two smoke tests from his SSM-attached terminal on `clever-bohr` (after manually installing claude on that instance — Bug H was still in effect at launch time):

**Test 1** — full `diag` against a freshly booted instance:
> All 8 checks `✓`. vLLM serving the model. Boot log clean.

**Test 2** — first Claude Code conversation on the EC2 instance:
> `~/local-llm-claude.sh "write a Python function that reverses a string"`
> Claude generated `reverse_string.py`, asked for approval (since `--dangerously-skip-permissions` was only added in the very last commit), Dinis approved, claude tried `python reverse_string.py`, hit the AL2023 `python: not found` (only `python3` exists), self-corrected to `python3 reverse_string.py`, and produced:
> ```
> Original: Hello, World!
> Reversed: !dlroW ,olleH
> ```

This is the artefact that confirms the slice is real: **a model running on EC2, served by vLLM, driving Claude Code, reading and writing files on the instance, executing shell commands, recovering from its own mistakes.**

The only residual manual step on `clever-bohr` was the `curl … | bash` claude install, which is exactly what Bug H prevented from happening automatically. **The next AMI bake should produce an instance where zero manual steps are needed.**

---

## Next-session touchpoint (this is what Dinis flagged as next)

1. **Bake an AMI from a freshly created stack** that includes commits `1141a870` and `abf14ea9` (so claude-code-firstboot actually fires, and the launcher works in non-login shells).
   - `sg lc create some-name --no-with-claude-code=false --with-sgit=true ...` → wait until `diag` shows 8 ✓ → `sg lc ami bake <name> --wait` → confirm AMI is created and tagged.
   - Then `sg lc create another-name --ami <ami-id>` → on that instance, `~/local-llm-claude.sh "hello"` should work **with zero manual steps**.
2. **If the firstboot service still fails on the AMI-baked instance**, check `journalctl -u claude-code-firstboot.service` and look for either:
   - npm/node not in `su - ssm-user`'s `$PATH` — the installer needs node.
   - The Anthropic installer URL changed.
3. **Pre-warm the HuggingFace cache in the AMI** to drop first-boot from ~10 minutes to ~2 minutes. Currently vLLM has to download the model on every fresh instance.
4. **Consider trimming `Local_Claude__Service.claude_session()`.** It's now a one-liner passthrough to `connect_target()` — `sg lc claude` could call `connect_target` directly and the function deleted.

---

## Failure classification

| Bug | Class | Why |
|-----|-------|-----|
| D — exit_code 0 → -1 | **Good (review)** | Caught by Opus reviewing the same session's commit. Zero live impact. |
| E — TimeoutSeconds < 30 silent | **Masking → Good** | Was a silent empty return for the whole prior session, hidden behind Bugs B+C. Now traceable via stderr surfacing. |
| F — ssm-user wait in 2 more sections | **Bad** | Prior fix was incomplete (only touched one of three sections). Now structurally fixed by pre-creating in `Section__Base`. |
| G — sgit/sgit-ai package name | **Good** | Surfaced as an `ERROR` line in the boot log within seconds of running Section__SGit_Venv. Clean fix. |
| H — systemctl enable without --now | **Bad** | The whole firstboot install pathway was dead from day one and nobody noticed because the prior end-to-end never reached this far. Caught only by Dinis trying to actually use claude on the instance. |
| I — sudo touch as ssm-user | **Bad** | Same root as H: the install pathway never ran, so its dependencies (sudoers) were never exercised. |
| J — exec claude missing PATH | **Bad** | Same root as H and I. The launcher had never been executed in a real session. |

The headline lesson: **slices that don't reach the live happy path are full of latent bad failures.** The moment Dinis ran `~/local-llm-claude.sh` on a real instance, three bugs surfaced at once. **Build to the live conversation, not to the unit tests** — for any agent-on-EC2 work, "ssh in and run the binary" is a non-negotiable acceptance gate.
