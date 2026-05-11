# CLI Surface

The complete `sgi` command surface for v1. Every command is documented with its arguments, behaviour, and the schemas it produces.

## Global conventions

**Every command accepts these global flags** (typer global options):

| Flag | Purpose |
|---|---|
| `--format <table\|json\|events>` | Output format. `table` is default. `json` produces stable structured output for piping. `events` streams the event bus for the operation. |
| `--storage <uri>` | Override workspace's default Storage URI. |
| `--exec-provider <ssh\|sg_compute\|twin>` | Override workspace's default exec provider. |
| `--region <region>` | Override workspace's default AWS region (only used by AWS-touching operations). |
| `--step-by-step` | Pause after each major operation step for inspection. |
| `--bench` | Emit structured timing data on stderr in addition to normal output. |
| `--quiet` / `-q` | Suppress progress chatter. Errors still print. |
| `--verbose` / `-v` | Print all events as they happen. |
| `--workspace <path>` | Use a workspace directory other than the cwd. Useful for scripts. |

**Exit code convention:**

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | User error (missing arg, invalid input, no workspace) |
| `2` | Transient / retryable (network, AWS throttling) |
| `3` | Infrastructure error (AWS API failure, SSH unreachable) |
| `4` | Integrity error (bundle hash mismatch, manifest malformed) |
| `5` | Test failure |

**Target resolution** — when a command takes an optional `<target>` argument:

1. If `<target>` is provided on the CLI, use it.
2. Else if `state.json` has `current` set and the instance is live → use it.
3. Else if exactly one tracked instance is live → use it (with announcement on stderr).
4. Else if multiple tracked + live → interactive prompt (suppress with `--quiet`, which then fails).
5. Else → exit with code 1: "no target instance; `sgi instance launch` or specify on CLI".

---

## Top-level structure

```
sgi
├── init                      Make current directory a workspace
├── bundle                    Capture, package, publish, load
├── recipe                    Multi-bundle composition
├── spec                      Named use cases
├── instance                  Workspace-local tracked instances
├── strip                     Test-driven file removal
├── test                      Run end-to-end test suites
├── benchmark                 Three canonical performance moments
├── storage                   Registry browsing
├── events                    Audit trail
├── shell                     Local REPL with workspace context
├── connect                   Pass through to sg lc connect
├── version                   Print version + included specs
└── doctor                    Diagnose env: creds, storage, providers
```

---

## `sgi init`

```
sgi init [--name <workspace-name>]
```

Make the current directory an sgi workspace by creating `state.json` and the subdirectory structure (`bundles/`, `recipes/`, `captures/`, `events/`, `benchmarks/`, `logs/`).

Fails if `state.json` already exists. Doesn't auto-init from any other command (P12).

---

## `sgi bundle`

The core artefact lifecycle. Two capture verbs because of different security/network profiles (P5).

### `sgi bundle capture <source-path>`

```
sgi bundle capture <source-path> [--name <bundle-name>] [--spec <spec-id>]
```

Observe a local installation: take a snapshot of `<source-path>`, wait for the user to indicate the install is done (or run a provided install command), take another snapshot, record the diff.

Produces:
- `workspace/captures/<timestamp>__<name>/diff.json`
- `workspace/captures/<timestamp>__<name>/files.txt`
- `workspace/captures/<timestamp>__<name>/meta.json`

Used for: capturing on the same machine sgi is running on. Cloud-agnostic, no AWS involved.

### `sgi bundle capture-from <target>`

```
sgi bundle capture-from [<target>] [--name <name>] [--spec <spec-id>] [--watch <path>]
```

Capture state changes on a remote instance via `Exec_Provider`. Uses target resolution. The instance must have `Exec_Provider__SSH` (or another exec provider) reachable.

Sequence:
1. SSH to target, list filesystem at `<path>` (default `/`)
2. Print "ready, perform installation now" (or run a `--script` if provided)
3. SSH again, list filesystem
4. Compute diff (with chmod/owner/xattr awareness)
5. Stream changed files from target to workspace

Used for: capturing the end-state of an install that ran on a build EC2.

### `sgi bundle package <capture-id> [--mode service]`

```
sgi bundle package <capture-id> [--mode <none|debug|service|minimal>]
                                [--name <name>]
                                [--version <semver>]
                                [--sidecar <path-or-stub>]
```

Turn a capture into a packaged bundle. Produces:
- `workspace/bundles/<name>__<version>/manifest.json`
- `workspace/bundles/<name>__<version>/payload.tar.zst`
- `workspace/bundles/<name>__<version>/sidecar.zip`

If `--mode` is anything other than `none`, runs the strip workflow (see [06__strip/strip-workflow.md](../06__strip/strip-workflow.md)) before packaging.

`--sidecar stub` generates a placeholder sidecar with empty `SKILL.md`, `USAGE.md`, `SECURITY.md`. `--sidecar <path>` uses a directory the user has prepared.

### `sgi bundle publish <local-bundle>`

```
sgi bundle publish <local-bundle-path> [--storage <uri>]
```

Upload a packaged bundle to Storage at its IFD path. The IFD path is derived from `(spec, name, version)`:

```
bundles/<spec>/<name>/v0/v0.1/v0.1.0/
    ├── manifest.json
    ├── payload.tar.zst
    ├── sidecar.zip
    └── publish.json
```

Updates `catalog.json` at the storage root.

Fails (exit 4) if a bundle already exists at that IFD path with a different sha256 — IFD paths are immutable.

### `sgi bundle list`

```
sgi bundle list [--spec <id>] [--storage <uri>]
```

List bundles in Storage. Default sort: spec, name, semver descending.

### `sgi bundle info <bundle-uri>`

```
sgi bundle info <bundle-uri>
```

Show manifest, size, sha256, publish timestamp, file count, and any recipes that reference it.

### `sgi bundle resolve <bundle-uri>`

```
sgi bundle resolve <bundle-uri>
```

Verify a bundle exists and return its concrete IFD path. Used by other tooling to convert short references to canonical paths.

### `sgi bundle verify <bundle-uri>`

```
sgi bundle verify <bundle-uri> [--deep]
```

Download the bundle from Storage and verify:
- Manifest is well-formed
- Payload sha256 matches manifest top-level hash
- With `--deep`: extract payload and verify per-file sha256s against manifest entries

### `sgi bundle load <bundle-uri> [<target>]`

```
sgi bundle load <bundle-uri> [<target>] [--verify] [--transparent]
```

Pull a bundle from Storage and load it onto a target instance. Uses target resolution.

Sequence:
1. `Load__Downloader` pulls `payload.tar.zst` from Storage to local
2. `Exec_Provider` copies the tarball to the target
3. `Load__Extractor` runs `tar xf` on the target into the manifest's declared root
4. `Load__Transparent` reapplies perms/owner/xattrs from the manifest (P2)
5. With `--verify`: hashes a sample of files against the manifest

### `sgi bundle diff <bundle-a> <bundle-b>`

```
sgi bundle diff <bundle-a-uri> <bundle-b-uri> [--files-only] [--sizes]
```

File-level diff between two bundles. Useful for understanding what changed across versions, or what `strip --mode service` removed compared to `strip --mode minimal`.

### `sgi bundle deregister <bundle-uri>`

```
sgi bundle deregister <bundle-uri> [--reason <text>]
```

Mark a bundle as unpublished (kept in Storage for rollback, hidden from `list`). Updates `catalog.json` with a deregistration entry. Does NOT delete the underlying files.

---

## `sgi recipe`

```
sgi recipe init <spec-id> [--name <name>]
sgi recipe validate <recipe-path>
sgi recipe publish <recipe-path>
sgi recipe list [--spec <id>]
sgi recipe info <recipe-uri>
sgi recipe execute <recipe-uri> [<target>] [--step-by-step]
sgi recipe diff <recipe-a> <recipe-b>
```

A recipe is an ordered list of bundle references + per-instance values (hostname, model name, etc.). Recipes themselves are IFD-versioned in storage:

```
recipes/<spec>/<recipe-name>/v0/v0.1/v0.1.0/
    ├── recipe.json
    └── publish.json
```

`execute` runs all bundle-load steps in order on the target instance, then runs the spec's test suite. With `--step-by-step`, pauses between each.

---

## `sgi spec`

```
sgi spec list
sgi spec info <spec-id>
sgi spec test-suite <spec-id>
sgi spec scaffold <spec-id>
```

Specs live in code (`sg_image_builder_specs/*`), not in storage. `list` reads from registered Python packages. `scaffold` generates a skeleton for a new spec.

---

## `sgi instance`

```
sgi instance list
sgi instance use <name>
sgi instance current
sgi instance track <name> [--spec <id>]
sgi instance forget <name>
sgi instance launch [--spec <id>] [--via <ssh|sg_compute>]
sgi instance status [<name>]
```

These commands manipulate **the workspace's view of instances**, not AWS instances directly:

- `track` adds to `state.json` tracked list (instance must already exist in the exec provider's world)
- `forget` removes from tracked list (does NOT delete the instance — use `sg lc delete` for that)
- `use` sets `current` in `state.json`
- `launch` calls the exec provider's launch path: `Exec_Provider__SSH` provisions an ephemeral EC2 directly; `Exec_Provider__Sg_Compute` shells out to `sg lc create`
- `status` queries live state via the exec provider (`Sg_Compute__Client.lc_info` or SSH ping)

---

## `sgi strip`

```
sgi strip analyse <bundle-uri> --mode <none|debug|service|minimal>
sgi strip plan <bundle-uri> --mode <m> [--out <path>]
sgi strip execute <plan-uri> [<target>]
sgi strip verify <plan-uri> [<target>]
sgi strip bake <bundle-uri> --mode <m> [--bump <semver>]
```

See [06__strip/strip-workflow.md](../06__strip/strip-workflow.md) for the full strip design. `bake` is the production workflow: load → strip → re-capture → publish as a new bundle version.

---

## `sgi test`

```
sgi test list [--spec <id>]
sgi test run <spec-id> [<target>] [--launch]
sgi test compare <run-a> <run-b>
```

`run` executes the spec's end-to-end test suite against the target. With `--launch`, provisions a fresh instance, runs tests, terminates.

---

## `sgi benchmark`

```
sgi benchmark first-load  <bundle-uri> [<target>] [--runs N]
sgi benchmark boot        <spec-id>     [<target>] [--runs N]
sgi benchmark execution   <spec-id>     [<target>] [--runs N] [--workload <name>]
sgi benchmark cold-start  <spec-id>             [--runs N] [--launch]
sgi benchmark report                            [--since <duration>] [--spec <id>]
```

The four benchmark verbs map directly to the three canonical moments + a composite (P17). `cold-start` measures the full chain: provision instance → load all bundles → service ready → first execution. `report` aggregates from `workspace/benchmarks/*.json`.

See [07__test-and-benchmark/test-and-benchmark.md](../07__test-and-benchmark/test-and-benchmark.md).

---

## `sgi storage`

```
sgi storage info
sgi storage browse [<prefix>] [--storage <uri>]
sgi storage stat <uri>
sgi storage gc --dry-run [--older-than <duration>]
sgi storage gc --execute  [--older-than <duration>]
sgi storage migrate <from-uri> <to-uri>
```

Backend-agnostic operations. `migrate` is the killer feature for air-gap: copy the entire registry tree between backends (S3 → local disk for an air-gap drop, or local disk → S3 for sync-back).

---

## `sgi events`

```
sgi events tail [--spec <id>] [--operation <id>]
sgi events query --since <duration> [--kind <kind>] [--spec <id>]
sgi events export [--jsonl] [--since <duration>] > out.jsonl
sgi events kibana
```

`tail` follows live events for an in-flight workflow. `kibana` opens the Kibana panel against the configured ES instance (leverages the existing sg-compute Elastic spec; no-op if not configured).

---

## `sgi shell`

```
sgi shell [<target>]
```

Local Python REPL with sgi context preloaded:

```python
>>> workspace                  # current workspace
>>> current_instance           # resolved target
>>> client                     # Exec_Provider, ready to use
>>> storage                    # configured Storage
>>> bundles                    # registry browser
>>> events                     # live event stream from current operations
```

Used for ad-hoc inspection ("diff this manifest against that one", "tail events from the last load").

---

## `sgi connect`

```
sgi connect [<target>]
```

Pass-through to `sg lc connect <name>` (opens an SSM session against the instance). Stays in the user's terminal until they exit the session. Uses target resolution.

Note: this command requires `sg-compute` to be installed. sgi has no separate SSM client.

---

## `sgi version` and `sgi doctor`

```
sgi version                 # version string, included specs, configured providers
sgi doctor                  # check: AWS creds reachable? storage reachable? providers wired?
```

`doctor` runs through a checklist and prints a colour-coded report. Exit code is the count of failing checks.

---

## What's NOT in v1

- `sgi config` (workspace `state.json` is the config)
- `sgi auth` (creds come from osbot-aws / environment)
- `sgi update` (sgi is a zipapp; the user updates by replacing the file)
- `sgi serve` (no daemon)
- `sgi gui` (no UI)
- Anything related to commercial sidecar marketplace (out of scope per pack overview)
