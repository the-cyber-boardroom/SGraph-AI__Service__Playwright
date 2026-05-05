# BV — Sidecar Shell: Replace rbash with bash

**Date:** 2026-05-05
**Priority:** MEDIUM — terminal panel is broken on every EC2 node; iframe shows shell error immediately on load

---

## Problem

The sidecar WebSocket shell handler spawns `/bin/rbash` as the terminal shell:

```python
# current (pseudocode — actual location in sidecar binary / user-data)
proc = subprocess.Popen(['/bin/rbash', '-i'], ...)
```

Standard Ubuntu 22.04/24.04 EC2 AMIs do not include `/bin/rbash`. The binary does not exist → the exec call fails → the WebSocket connection closes immediately → the iframe-based terminal in `sg-compute-host-shell` shows an error on load.

---

## Fix

Change the spawned shell from `/bin/rbash` to `/bin/bash`:

```python
proc = subprocess.Popen(['/bin/bash', '-i'], ...)
```

**Security rationale for removing rbash:**
`rbash` was likely chosen to restrict the user to a limited command set. However:
1. Reaching the sidecar at all requires AWS credentials (the security group only allows access from authorised sources).
2. The sidecar runs on an EC2 instance that is inherently scoped to a single node lifecycle.
3. `rbash` on Ubuntu without additional `PATH` restriction provides minimal real security gain.
4. A broken terminal is worse than a permissive one for operational purposes.

The correct long-term hardening path is mTLS / PKI (not rbash), tracked separately.

---

## Location

The shell command is in the sidecar codebase that runs on the EC2 instance. This may be:
- Part of the user-data bootstrap script that installs the sidecar
- Inside the sidecar binary itself (a compiled Go or Python service)

Confirm the exact file by searching for `rbash` in:
- `sg_compute/` and `sg_compute_specs/*/` user-data templates
- Any sidecar source files in the repo

---

## Acceptance criteria

1. After applying the fix and rebooting/re-deploying, the terminal iframe in `sg-compute-host-shell` loads a functional bash prompt.
2. A simple command (`echo hello`) executes and returns output.
3. No `rbash` references remain in sidecar shell-invocation code.

---

## Related

- `BUG-BATCH-1__sidecar-auth-and-terminal.md` — full analysis doc (Bug 3)
- Bug 5 (terminal auth) is partially resolved by this fix (iframe becomes usable) + fully resolved by Bug 4 (auth key available)
