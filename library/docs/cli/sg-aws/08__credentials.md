---
title: "sg aws credentials — Per-role AWS credentials store"
file: 08__credentials.md
author: Architect (Claude)
date: 2026-05-17
parent: README.md
---

# 08 — `sg aws credentials`

The credentials store: name AWS access keys by **role** (e.g. `admin`, `dev`, `ci`) and switch between them per shell session. Backed by the `Credentials__Store` + `Audit__Log` introduced in v0.2.28 (Phase B/C/D). Every AWS client seam across the codebase now resolves credentials through `Sg__Aws__Session`, so switching role here is the single source of truth for which AWS account/identity every other `sg aws *` command uses.

**Not to be confused with** the upcoming `sg aws creds` namespace (v0.2.29) for **scoped temporary STS credentials**. The two coexist:

| Surface | Lifetime | What it stores | Typical use |
|---------|----------|----------------|-------------|
| `sg aws credentials` (this page) | long-lived | named role → AWS access key + secret (+ optional region) | Day-to-day shell sessions; choosing which AWS identity to act as |
| `sg aws creds` (v0.2.29, PROPOSED) | minutes-to-hours | scope name → temporary STS-assumed credentials | One specific action, one specific permission scope, expires automatically |

---

## Command shape

```
sg aws credentials list                              ← all configured roles
sg aws credentials status                            ← which role is active (this shell)
sg aws credentials whoami                            ← STS get-caller-identity for the active role
sg aws credentials show <role>                       ← inspect a role (secret redacted)
sg aws credentials test [<role>]                     ← live STS call to verify the role works

sg aws credentials add <role>     [opts]             ← add a role (creates if missing)
sg aws credentials set  <role>    [opts]             ← edit fields on an existing role
sg aws credentials switch <role>                     ← activate a role for the current shell
sg aws credentials export <role>                     ← emit `export AWS_*=...` lines (for `eval $(...)`)
sg aws credentials remove <role>                     ← remove a role (audit-logged)
sg aws credentials delete <role>  [--force]          ← alias of remove; --force skips the prompt

sg aws credentials log [-n N]                        ← tail of the audit log
sg aws credentials trace [<command>...]              ← trace which seams resolve credentials for a given command
sg aws credentials init                              ← bootstrap an empty store + audit log
```

No mutation-gate env var — the store is local-only and never executes AWS mutations on its own. Each verb that touches the on-disk store is interactively confirmed.

---

## Storage layout

```
~/.sg/aws/credentials/
├── store.json                 # the named roles
└── audit.jsonl                # append-only event log (add / switch / remove / etc.)
```

`store.json` is `0600`. Secrets are stored as plain JSON in v0.2.28; encryption-at-rest with a vault key is on the v0.2.30 roadmap (separate brief).

---

## `list`

```bash
sg aws credentials list                 # → table: role | account-id (or "unknown") | region | last-used | active?
sg aws credentials list --json
```

---

## `status` / `whoami`

```bash
sg aws credentials status               # → active role name + "set via $SG_AWS__CREDENTIALS__ACTIVE_ROLE" or "(default)"
sg aws credentials whoami               # → STS get-caller-identity for the active role: account / arn / userid
```

`whoami` makes a live `sts:GetCallerIdentity` call — useful for proving "the role I switched to is actually the one AWS sees."

---

## `show <role>`

Inspect a role without revealing the secret:

```bash
sg aws credentials show admin           # → role | access-key-id | secret (redacted: AKIA****…****abcd) | region | created-at | last-used
sg aws credentials show admin --json    # secret still redacted in JSON output
sg aws credentials show admin --reveal  # secret unredacted — interactive confirm + audit-log entry
```

---

## `add <role>` / `set <role>`

Two distinct verbs:

| Verb | Behaviour |
|------|-----------|
| `add <role>` | Refuses if `<role>` already exists. Idempotent only on new roles. |
| `set <role>` | Edits fields on an **existing** role. Refuses if `<role>` does not exist. |

Common flags:

```
--access-key-id <ID>            (or read from $AWS_ACCESS_KEY_ID)
--secret-access-key <SECRET>    (or read from $AWS_SECRET_ACCESS_KEY; or interactive prompt)
--session-token <TOKEN>         (optional — for temporary creds you want to park)
--region <region>               (optional default region for this role)
--account-id <id>               (optional — recorded for cross-reference; not used at call time)
--description "..."             (free-form note shown by `list`)
```

Examples:

```bash
# add a new role from current shell's AWS_* env vars
AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... \
  sg aws credentials add dev --region eu-west-1 --description "dev-account read-only"

# edit just the region on an existing role
sg aws credentials set dev --region us-west-2

# rotate the secret on an existing role
sg aws credentials set ci --access-key-id <new-id> --secret-access-key <new-secret>
```

---

## `switch <role>` / `export <role>`

Two ways to activate a role:

```bash
# 1. switch — sets the role for the **current shell session** via $SG_AWS__CREDENTIALS__ACTIVE_ROLE
sg aws credentials switch admin
# (the wrapper script the install puts on $PATH source-exports the role env vars)

# 2. export — emit shell export lines to eval into the current shell
eval "$(sg aws credentials export admin)"
# this exports AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN (if present) / AWS_DEFAULT_REGION
```

`switch` is the friendlier UX; `export` is the explicit one for scripts and CI.

The active role is **per-shell**, not global. Open a new shell → defaults to whatever `$SG_AWS__CREDENTIALS__ACTIVE_ROLE` was inherited (often unset → "no role active, falls back to standard AWS chain").

---

## `test [<role>]`

Live verification — performs a real `sts:GetCallerIdentity` call against the named role (or the active role if `<role>` omitted):

```bash
sg aws credentials test admin           # → role | resolved-account-id | resolved-arn | OK / FAIL with reason
sg aws credentials test                 # tests the active role
```

Useful immediately after `add` or `set`.

---

## `remove <role>` / `delete <role>`

```bash
sg aws credentials remove ci                       # [y/N] prompt
sg aws credentials remove ci --yes                 # skip prompt
sg aws credentials delete ci --force                # alias; --force skips prompt
```

The audit log records `remove` events with the role name and timestamp (no secret data).

---

## `log [-n N]` / `trace [<command>...]`

Audit visibility:

```bash
sg aws credentials log                          # last 20 events
sg aws credentials log -n 200                   # last 200
sg aws credentials log --json | jq '.[] | select(.event == "switch")'

# trace which seam would resolve credentials for a given command path
sg aws credentials trace aws lambda waker info     # → which role would be used; which seam (env var / store / IMDS)
sg aws credentials trace                         # → the resolution order for the current process
```

`trace` is the debugging verb for "why is this AWS call hitting account X instead of account Y?"

---

## `init`

```bash
sg aws credentials init             # creates ~/.sg/aws/credentials/{store.json,audit.jsonl} with safe perms
```

Idempotent — re-running on an initialised store is a no-op.

---

## The seam: `Sg__Aws__Session`

Every other `sg aws *` command resolves credentials through `Sg__Aws__Session` (added in v0.2.28 Phase D). The resolution order:

```
1. $SG_AWS__CREDENTIALS__ACTIVE_ROLE  →  lookup in store.json
2. $AWS_ACCESS_KEY_ID + $AWS_SECRET_ACCESS_KEY  (the standard AWS env vars)
3. $AWS_PROFILE  →  ~/.aws/credentials
4. IMDS  (when running on EC2)
5. AWS SSO  (`aws sso login`)
```

The first hit wins. `sg aws credentials trace` shows the resolution live.

This means switching role with `sg aws credentials switch X` immediately affects every subsequent `sg aws *` invocation in the same shell — no need to set / unset `AWS_*` env vars by hand.

---

## What backs this

```
sgraph_ai_service_playwright__cli/credentials/
├── cli/Cli__Credentials.py                 # the Typer surface above
├── service/
│   ├── Sg__Aws__Session.py                 # the canonical AWS client seam
│   ├── Credentials__Store.py
│   ├── Credentials__Resolver.py
│   ├── Audit__Log.py
│   └── ...
├── edit/Credentials__Editor.py             # the `set` edit-mode flow
├── schemas/Schema__AWS__Credentials.py
└── ...
```

The store lives in `~/.sg/aws/credentials/`; the seam lives in `Sg__Aws__Session`; every `*__AWS__Client.py` across the codebase accepts an `Sg__Aws__Session` in its constructor.
