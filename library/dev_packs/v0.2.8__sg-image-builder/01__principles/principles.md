# Principles

These principles govern every design decision in sgi. They are numbered for stable reference across the pack. When a design question arises, the answer is "which principle applies, and what does it say to do?"

The principles are derived from:
- The EBS lazy-load findings (P1, P5, P19)
- The recent local-claude debriefs and bug catalogue (P3, P14)
- The `SGraph-AI__Service__Playwright` codebase conventions (P3, P10, P11)
- The `SG_Send__Deploy` Provider/Twin pattern (P10, P11)
- The package-manager arch brief by the project lead (P15–P20)
- The user's stated workspace/vault constraints (P12–P14, P21)

---

## The 21 principles

### P1 — Storage substrate is abstract from day one

Never `s3.*` calls in service code. Storage is an abstract interface with at minimum three implementations from v1:

- `Storage__S3` — production
- `Storage__Local_Disk` — air-gap, dev iteration, the "zip the root" property
- `Storage__In_Memory` — tests

Bundle URIs use a scheme prefix (`s3://...`, `file://...`, `mem://...`). Tests run against `Storage__In_Memory`. Production runs against `Storage__S3`. Air-gap deployments use `Storage__Local_Disk` pointed at a mounted volume.

### P2 — Transparency at the consumer

The instance consuming a bundle cannot tell whether a file got there via the original installation or via a Storage copy. Same paths, same permissions, same ownership, same xattrs, same symlinks. The bundle format must preserve everything that matters for downstream behaviour.

This is the property that lets us substitute capture-from-storage for capture-from-install with zero changes to anything downstream. The consumer is the test suite; if tests can't tell the difference, no one can.

### P3 — Every operation is fully instrumented

Not just "a Python function". Each operation has:

- Its own service class (single class per file)
- Its own request/response schemas (`Type_Safe`)
- Its own unit tests (against in-memory providers, no mocks)
- Its own KPI (a measurable performance target stored in the spec)
- Its own visualisation (event emitted to the bus → optional Kibana panel)
- Its own benchmark mode (`--bench` flag produces structured timing)

This addresses the "silent empty returns" bug class from the local-claude debriefs. If every operation has a structured result, you can't accidentally drop information.

### P4 — IFD versioning on artefact paths

Bundle and recipe paths in storage are immutable once published:

```
bundles/<spec>/<bundle-name>/v0/v0.1/v0.1.0/{manifest.json, payload.tar.zst, sidecar.zip}
```

Bumping a bundle = publishing v0.1.0.1 (or v0.2.0, etc.) at a new path. Old path keeps working. Rollback = recipe references the old path. No cache-busting tricks; the path *is* the version.

### P5 — Capture, don't construct; replay, don't rerun

The build phase **observes** a real installation on a build host and records what changed. The load phase **replays** those changes onto a fresh instance. sgi never writes installation scripts that "should" produce the same state — it records actual state and ships that.

Corollary: anything that *must* be done at boot (per-instance values: hostname, IAM role, ssh host keys, machine-id) lives in a separate small section. Anything instance-invariant lives in a bundle.

### P6 — Strip is first-class; tests define what survives

Strip is a substantial workflow, not an afterthought. Four modes (`none`, `debug`, `service`, `minimal`) with the most aggressive removing anything not exercised by the spec's end-to-end test suite. The strip is **test-driven**: a file survives iff removing it causes a test to fail.

This is also a security workflow — `minimal` mode intentionally cripples the image for any purpose except its declared workload.

See [06__strip/strip-workflow.md](../06__strip/strip-workflow.md).

### P7 — Visualisation and monitoring from v1, not as an afterthought

Every operation emits structured events to the event bus. A `Events__Sink__JSONL` writes them to a workspace file by default. An `Events__Sink__Elasticsearch` ships them to Kibana for live visualisation (leveraging the existing sg-compute Elastic spec). Step-by-step execution (`--step-by-step` flag) pauses after each operation for inspection.

### P8 — Bundles content-addressed in manifest, IFD-addressed in path

The manifest contains sha256 of every file and of the payload tarball as a whole. The path encodes the human-meaningful version. The two together give:

- (a) Integrity verification without trusting the path
- (b) Stable human-readable references

A bundle is uniquely identified by `(spec, name, semver, sha256)`.

### P9 — The storage layout is a registry, not a dumping ground

The layout is designed up front with a strict schema, and lived by from day one. No "we'll structure it later". The schema is in [05__bundles/bundles-and-storage-layout.md](../05__bundles/bundles-and-storage-layout.md) and must be honoured by every Storage operation.

A `Storage__S3` and a `Storage__Local_Disk` produce identical tree structures. Migration between backends is a tree-copy.

### P10 — Execution provider abstracted; SSH is the default

Service code talks to `Exec_Provider`, not to SSH or SSM directly. Three implementations from v1:

- `Exec_Provider__SSH` — **default**. Uses osbot-utils SSH helpers. Synchronous, fast, cloud-agnostic.
- `Exec_Provider__Sg_Compute` — shells out to `sg lc exec`. Used when sgi operates on an sg-compute-managed instance.
- `Exec_Provider__Twin` — in-memory; records calls; returns canned responses. Used in all tests.

SSH is the default because it is:

- Synchronous (no SSM `InvalidInstanceId` retries, no polling, no swallowed errors)
- ~50× faster per command than SSM (sub-100ms vs 1.5–3s)
- Cloud-agnostic (works on any host with port 22)
- Offline-capable

See [04__providers/providers.md](../04__providers/providers.md) for the full Provider design.

### P11 — Bundles are Type__Twin instances

A bundle has a `Schema__Twin__Config__Bundle` (immutable manifest) and a `Schema__Twin__State__Bundle` (operational state: upload status, load count, verification results). State mutations go through `Type__Twin__Bundle.execute(action, **kwargs)` only.

This gives free audit trail and the ability to serialise the entire fleet of bundles as one consistent state. Pattern lifted from `SG_Send__Deploy`.

### P12 — No global state; workspace folder is the unit of context

Everything sgi writes lives in the cwd. No `~/.sgi/`, no `/etc/sgi/`, no machine-wide registry. To switch contexts: `cd`.

A "workspace" is any folder containing `state.json`. The user creates one with `sgi init`. Write commands require a valid workspace (no auto-init); read-only commands work anywhere.

### P13 — All sgi-written files are visible

No leading-dot filenames. The workspace folder's contents fully describe the scenario state. The user can `ls`, `cat`, edit them by hand, see them in their file browser, share them with collaborators.

Exception: `.sg_vault/` is sgit's metadata if the user has chosen to vault-ify the workspace. sgi doesn't write or read it.

### P14 — sgit is the user's tool; sgi never invokes it

sgi writes files; the user decides when to `sgit commit`, `sgit push`, `sgit share`. sgi never invokes sgit, doesn't import the sgit Python package, doesn't even know it exists.

This keeps the trust boundary clean (sgit needs vault keys; sgi never sees them) and lets the user fully control what gets shared and when.

### P15 — Reuse, don't reimplement

sgi never duplicates upstream installer logic. The build host uses `apt-get install`, `pip install`, `dnf install`, `curl … | bash`, `docker pull` — whatever the upstream maintainer ships. sgi *observes* the result. If you find yourself reimplementing what apt does, stop.

From the package-manager arch brief: "the upstream maintainers have already done that work."

### P16 — Tests are the contract

The spec's test suite is the authoritative definition of what the image must do. If tests pass, the image works. If tests pass after stripping 90% of the files, the image still works and is now 90% smaller. The more brutal the stripping, the better the tests need to be. Tests and stripping co-evolve.

### P17 — Three canonical performance moments

Every benchmark captures three numbers, always named the same way:

- **first_load** — Time from "bundle not present" to "bundle on disk"
- **boot_time** — Time from "bundle on disk" to "service ready"
- **execution** — Time per operation once running

Three numbers per spec, per environment, per workload. Stored as JSON in the workspace `benchmarks/` folder; aggregatable across runs.

### P18 — Vault-shaped sidecar accompanies every bundle

Every published bundle includes a sidecar with at minimum:

- `SKILL.md` — agent-readable: declared inputs, outputs, capabilities, failure modes
- `USAGE.md` — human-readable: when to use, common patterns, error messages decoded
- `SECURITY.md` — threat model, CVEs, hardening notes
- `tests/` — the test suite that defines "works" (P16)
- `performance/` — captured benchmarks (P17)

Stored as `sidecar.zip` in storage; expanded to a folder when extracted. In v1 this is plain zip; vaultification is a v2+ overlay.

### P19 — Offline-first

Every sgi operation works without internet given a local Storage backend. No call-home, no licence server, no telemetry, no upstream registry access during operation.

Online operation (S3, fetching updates from a remote catalog) is an optimisation. Offline operation is the baseline.

### P20 — sgi itself ships as a single zipapp

The packaging target produces an executable zipapp via `python -m zipapp`. To deploy sgi into an air-gapped environment, copy one file across the boundary, run it, done. The CLI binary, the schemas, the validation, the build tools — all in one zip.

This is a packaging requirement on the project layout: no `__main__.py`-incompatible imports, no `setup.py install`-only dependencies, no relative paths assuming a development install.

### P21 — Cloud-agnostic

No provider-specific code in core sgi. AWS lives behind providers (`Exec_Provider__SSH` is cloud-agnostic; `Exec_Provider__Sg_Compute` happens to consume an AWS-flavoured tool). A customer running sgi on bare metal, on-prem KVM, in air-gap, or against a different cloud provider hits the same code paths.

When AWS-specific helpers are needed (key pair lifecycle, security group setup), they live in a clearly-named module (`sgi/providers/aws/`) and are only used by `Exec_Provider__SSH` when launching on EC2 specifically.

---

## How to use this list

When implementing a feature:

1. Find the principles that apply (usually 2–4)
2. Check the design against each one
3. If two principles conflict, escalate — don't pick one silently

When reviewing code:

1. Cite the principle that the code is honouring (or violating)
2. Prefer the principle number — "this violates P10" — for unambiguous reference

When updating principles:

1. They are stable. Don't renumber.
2. If a principle is wrong, file an issue with rationale; don't change it in flight.
3. New principles get the next available number; deprecated ones get a strike-through and a pointer to their replacement.

## What's explicitly NOT a principle

Some things from upstream context that the pack chooses NOT to elevate to principle:

- "Use SSM not SSH" — overridden, see P10
- "Graph-driven design" — captured as metadata structure (P21 of the package-manager doc) but the query engine is v2+
- "Fractal package manager nesting" — designed not to preclude, but not v1
- "Runtime granular module loading" — sidecar declares it (P18); runtime support is v2+
