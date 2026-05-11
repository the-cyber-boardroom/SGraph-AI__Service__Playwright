# Strip Workflow

Strip is a first-class workflow (P6). It removes files that aren't needed by the bundle's declared purpose, with the spec's end-to-end test suite as the arbiter of "needed".

This doc covers the four modes, the analyse/plan/execute/verify sequence, the safety properties that prevent strip from breaking things silently, and how strip composes with the rest of sgi.

The mental model: **a file survives strip iff removing it causes a test to fail.**

---

## The four modes

| Mode | What it removes | Test surface required |
|---|---|---|
| `none` | Nothing | Baseline measurement only |
| `debug` | `/usr/share/doc`, `/usr/share/man`, `/var/cache/apt/`, `/var/cache/dnf/`, bake-time logs, build caches | Service test passes |
| `service` | Everything in `debug`, plus packages not exercised by service tests, plus debug binaries (gdb, strace, etc.) but **keeps** SSH, basic diag tools | Service test passes |
| `minimal` | Everything in `service`, plus anything not in the file-access log captured during end-to-end tests, **including SSH server itself if no test uses it** | End-to-end test passes (which IS the access log) |

The progression is intentional: each level removes more, each level requires a stronger test suite, each level produces a smaller and more locked-down image.

### What "needed" means per mode

| Mode | Needed = |
|---|---|
| `none` | (trivial — everything is needed) |
| `debug` | Static list — well-known removable directories |
| `service` | In the file-access log of a passing service test + on a static keep-list (init, kernel, networking, ssh) |
| `minimal` | In the file-access log of a passing end-to-end test, ONLY |

The minimal mode is the most aggressive and the most useful. It produces images that literally cannot be used for anything except the declared workload — the perfect security property for a single-purpose ephemeral instance.

---

## The analyse → plan → execute → verify cycle

Strip is too important to be a single command. Splitting it into four discrete steps lets the user (or a CI gate) inspect each output before committing to the next:

```
1. analyse  — read the bundle + run the relevant tests + record file accesses
              → produces an analysis report (which files are touched, which aren't)
2. plan     — given analysis + chosen mode, decide what to remove
              → produces a strip plan (immutable artefact, stored in workspace)
3. execute  — apply the plan on a target instance
              → produces an executed-plan record (what was removed, when, by whom)
4. verify   — re-run the test suite to confirm nothing essential was removed
              → produces a verification result
```

A plan can be saved, reviewed, shared, and applied later. The same plan can be executed against multiple instances. Plans are versioned and signed (sha256-hashed).

### `sgi strip analyse`

```
sgi strip analyse <bundle-uri> --mode <none|debug|service|minimal>
                               [--test-target <existing-target>]
                               [--launch]
```

Steps:

1. Resolve and download the bundle to a workspace directory
2. Launch (or use existing) test target
3. Load the bundle onto the target
4. Run the spec's test suite of the relevant level:
   - `debug` and `service` modes: run the spec's `tests/integration/` suite
   - `minimal` mode: run the spec's `tests/end_to_end/` suite
5. While tests run, collect a file-access log on the target. Use `inotifywait` or `audit` to record every file accessed by the workload (read, exec, mmap).
6. Diff (files in bundle) vs (files accessed during test) — anything in the bundle but not accessed is a candidate for removal.
7. Cross-check against the mode's static keep-list (we never remove `/sbin/init`, kernel modules listed in `/proc/modules`, etc., regardless of access log).
8. Output the candidate-removal list to `workspace/strip/<bundle-name>__<mode>__<timestamp>/analyse.json`.

Output schema:

```python
class Schema__Strip__Analysis(Type_Safe):
    bundle_uri       : Safe_Str
    mode             : Safe_Str
    analyzed_at      : Safe_Str
    target_instance  : Safe_Str
    files_in_bundle  : int
    files_accessed   : int                               # during the test
    candidates       : List[Schema__Strip__Candidate]    # to be removed
    keep_list_hits   : List[Safe_Str]                    # files that would have been removed but are on keep-list
    test_suite_run   : Schema__Test__Suite__Result
```

`Schema__Strip__Candidate`:

```python
class Schema__Strip__Candidate(Type_Safe):
    path             : Safe_Str
    size_bytes       : int
    reason           : Safe_Str                          # "not accessed during test" / "in debug-mode static list"
    confidence       : Safe_Str                          = 'high'             # 'high|medium|low'
```

### `sgi strip plan`

```
sgi strip plan <bundle-uri> --mode <m> [--from-analysis <analysis-uri>]
                                       [--out <path>]
                                       [--keep-pattern <glob>]
                                       [--remove-pattern <glob>]
```

Convert an analysis into a concrete plan. The user can override the analysis with `--keep-pattern` (force-keep matching paths) and `--remove-pattern` (force-remove matching paths).

Output schema:

```python
class Schema__Strip__Plan(Type_Safe):
    plan_id          : Safe_Str                          # hash-derived
    bundle_uri       : Safe_Str
    mode             : Safe_Str
    created_at       : Safe_Str
    based_on_analysis: Safe_Str

    files_to_remove  : List[Safe_Str]                    # absolute paths
    files_to_keep    : List[Safe_Str]                    # explicit keeps (from --keep-pattern)
    total_remove_bytes : int

    test_suite_to_verify : Safe_Str                      # which suite to run for verification
```

Stored in `workspace/strip/plans/<plan-id>.json`. Immutable once written.

### `sgi strip execute`

```
sgi strip execute <plan-id-or-path> [<target>]
```

Apply a plan to a target instance. For each `files_to_remove` path:

1. Verify the file is actually on the target (skip if not, log a warning)
2. Capture its sha256 first (for the executed-plan record)
3. Remove it

Output: `workspace/strip/executions/<plan-id>__<target>__<timestamp>/execution.json` with the full list of removed files + sha256s.

### `sgi strip verify`

```
sgi strip verify <plan-id-or-path> [<target>]
```

Run the verification test suite (declared in the plan) against the post-strip target. Outputs pass/fail per test, with diffs against the pre-strip baseline if available.

If verification **fails**, the user must:

1. Re-run with `--restore` to put back the removed files (the executed-plan record makes this possible — sha256s + workspace cache), OR
2. Run `sgi strip plan --update --restore <files...>` to produce a less-aggressive plan, OR
3. Strengthen the test suite and re-run analyse (P16 — tests are the contract)

### `sgi strip bake`

```
sgi strip bake <bundle-uri> --mode <m> [--bump <semver>] [--publish]
```

The production end-to-end workflow. Combines:

```
analyse → plan → load to target → execute → verify → capture-from-target → package → publish
```

If any step fails, the bake aborts and the original bundle remains the latest. If verification passes, the stripped bundle is published at a new IFD path:

```
bundles/<spec>/<bundle-name>/v0/v0.1/v0.1.0/      (the original)
bundles/<spec>/<bundle-name>/v0/v0.1/v0.1.1/      (the stripped --mode service)
bundles/<spec>/<bundle-name>/v0/v0.2/v0.2.0/      (the stripped --mode minimal)
```

Each is a separately-loadable bundle. A recipe references whichever is appropriate.

---

## Static keep-lists per mode

Some files must never be removed regardless of access log, because removing them would cause boot failure or break basic instance functionality. These are encoded as keep-list patterns per mode:

### Always-keep (all modes)

- `/sbin/init`, `/lib/systemd/systemd`
- `/boot/*` (kernel, initramfs, grub)
- `/lib/modules/<kernel-version>/*` for loaded modules (from `lsmod`)
- `/etc/passwd`, `/etc/group`, `/etc/shadow`
- `/etc/hostname`, `/etc/hosts`, `/etc/resolv.conf` symlink target
- `/etc/ssh/sshd_config` (we may remove sshd itself in minimal, but its config stays for debug if a future strip changes)
- `/lib*/ld-linux*` and `/lib*/libc.so.*` (dynamic linker)
- `/var/lib/cloud/*` for ec2-user pre-creation state
- Any file referenced from `/etc/systemd/system/multi-user.target.wants/`

### `debug` mode keep-list

The always-keep set, plus:

- `/usr/bin/sshd`, `/usr/sbin/sshd`
- `/usr/bin/curl`, `/usr/bin/wget`
- Standard shell utilities (`ls`, `cat`, `cp`, `mv`, `chmod`, `chown`, `find`, `grep`, `awk`, `sed`)

### `service` mode keep-list

The `debug` set, plus:

- The service's own binary and config
- The service's data directory (e.g. `/var/lib/postgresql/` for a postgres bundle)

### `minimal` mode keep-list

The always-keep set only. Everything else must justify itself via the access log.

The keep-lists live in `sg_image_builder/strip/modes/Strip__Mode__<name>__Keep_List.py`. They are explicit, reviewable, and versioned.

---

## Safety properties

Strip is dangerous. These properties make it safe enough to use:

**1. Strip never modifies the original bundle.** Strip operates on a copy loaded onto a target instance. The bundle in Storage is immutable (P4). `strip bake` *publishes a new* stripped bundle at a new IFD path.

**2. Plans are immutable.** Once a `Schema__Strip__Plan` is written, its `plan_id` is its sha256. Two executions of the same plan will remove the same files.

**3. Executions are recorded with restore data.** Every removed file's sha256 is recorded, and the original bytes are kept in workspace cache. `sgi strip restore <execution-id>` puts them back.

**4. Verification is mandatory before publish.** `sgi strip bake` will not publish a stripped bundle whose verification test suite fails. There is no `--force` to skip this.

**5. Keep-lists are explicit and audit-friendly.** Patterns are in code, not in config. A change to a keep-list is a code change with a PR.

**6. Mode escalation requires explicit opt-in.** No automatic upgrade from `service` to `minimal`. The user must run `sgi strip bake --mode minimal` explicitly.

---

## Composition with other commands

Strip integrates with the rest of sgi like this:

```
sgi bundle capture-from <target>            → fat bundle in workspace
sgi bundle package <capture> --mode none    → publishable v0.1.0
sgi bundle publish <bundle>                 → v0.1.0 in storage

sgi strip bake <bundle-uri> --mode debug --bump 0.1.1
                                            → v0.1.1 (stripped --mode debug) in storage

sgi strip bake <bundle-uri> --mode service --bump 0.1.2
                                            → v0.1.2 (stripped --mode service)

sgi strip bake <bundle-uri> --mode minimal --bump 0.2.0
                                            → v0.2.0 (stripped --mode minimal)

# All four versions in storage. Recipes reference whichever they want.
```

A recipe for production typically references `v0.2.0` (minimal). A recipe for development references `v0.1.1` (debug — keeps the diagnostic tools).

---

## v1 simplifications

Implementations of these can be punted if necessary, with the design preserved:

- **`debug` mode in v1 is purely static**: removes a hardcoded list, no test run needed.
- **`service` mode in v1 uses a coarse access log**: file-access tracked by `find /usr -newer <before-test-marker>` rather than full `inotify`. Less precise but simpler.
- **`minimal` mode in v1 may be experimental**: ship the analyse/plan flow but mark the resulting bundles as experimental until we have several specs validating it.

The full design above is the v1.0 target; v0.1 (the first release) can ship with `none` and `debug` only, with `service` and `minimal` following.
