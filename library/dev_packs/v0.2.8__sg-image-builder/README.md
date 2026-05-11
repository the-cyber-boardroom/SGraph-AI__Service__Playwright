# SG-Compute Image Builder — Brief Pack v1

**Repo target:** `https://github.com/SG-Compute/SG-Compute__Image-Builder`
**Package name:** `sg_image_builder`
**CLI alias:** `sgi`
**Version target:** v0.1.0 (first release)
**Pack date:** 2026-05-11

---

## What this is

This pack is the complete brief for building **sgi** — a CLI tool that produces ephemeral EC2 images by capturing the state of a working instance and replaying it onto a fresh one. It is **the image-building layer** of a larger package-management vision; the package manager is the next layer up and is **explicitly out of scope** for this pack.

The pack is self-contained. A new Claude Code session reading only the files in this folder has everything needed to start implementing. Cross-references between docs use relative paths.

## The problem in one paragraph

`sg lc create` already produces a working local-claude instance. It takes ~10 minutes. Custom AMIs take ~30 minutes to bake and load even slower because of EBS snapshot lazy-load. The fix is to do the slow work once on a build instance, capture the result as files in Storage, and load it back onto fresh instances at NIC line rate. The user-visible win is cold-start from ~10 minutes to ~60–90 seconds.

## What sgi does

| Verb | What it does |
|---|---|
| `capture` | Observe a real installation on a build host; record what changed on disk |
| `package` | Turn a capture into a versioned bundle (tar.zst + manifest + sidecar) |
| `publish` | Upload a bundle to Storage at its IFD-versioned path |
| `load` | Pull a bundle from Storage onto a target instance; replay file changes |
| `strip` | Remove files not required by the spec's test suite; re-test; re-publish |
| `test` | Run a spec's end-to-end test suite against a target instance |
| `benchmark` | Measure first-load, boot, execution — three canonical moments |

Plus thin verb groups for `recipe` (multi-bundle compositions), `spec` (named use cases), `instance` (workspace-local tracked instances), `storage` (browse the registry), `events` (audit), `shell` and `connect` (REPL and SSM passthrough).

## How to read this pack

Read in this order:

1. **This README** (you're reading it) — orient yourself
2. **[00__pack-overview/quick-reference.md](00__pack-overview/quick-reference.md)** — one-page reference of the core concepts
3. **[01__principles/principles.md](01__principles/principles.md)** — the 21 principles that govern every design decision
4. **[02__architecture/architecture.md](02__architecture/architecture.md)** — the codebase layout and how the pieces fit
5. **[03__cli/cli-surface.md](03__cli/cli-surface.md)** — full CLI command reference
6. **[04__providers/providers.md](04__providers/providers.md)** — Storage, Exec_Provider abstractions and their implementations
7. **[05__bundles/bundles-and-storage-layout.md](05__bundles/bundles-and-storage-layout.md)** — what's in a bundle, the IFD storage layout, the sidecar
8. **[06__strip/strip-workflow.md](06__strip/strip-workflow.md)** — the four strip modes, test-driven file removal
9. **[07__test-and-benchmark/test-and-benchmark.md](07__test-and-benchmark/test-and-benchmark.md)** — end-to-end test suites, three performance moments
10. **[08__specs-and-recipes/specs-and-recipes.md](08__specs-and-recipes/specs-and-recipes.md)** — the v1 spec ladder (9 specs from ssh_file_server to vllm_docker)
11. **[09__implementation-plan/implementation-plan.md](09__implementation-plan/implementation-plan.md)** — sequencing, milestones, acceptance criteria
12. **[10__dev-ops/dev-ops-brief.md](10__dev-ops/dev-ops-brief.md)** — CI pipeline, auto-tagging, test layers
13. **[11__librarian/librarian-brief.md](11__librarian/librarian-brief.md)** — vault setup, agentic team setup

Appendices for reference:

- **[appendices/A__layout-templates.md](appendices/A__layout-templates.md)** — concrete file/folder structures, JSON shapes
- **[appendices/B__code-conventions.md](appendices/B__code-conventions.md)** — class naming, Type_Safe usage, forbidden patterns
- **[appendices/C__glossary.md](appendices/C__glossary.md)** — every term in this pack, defined

## Conventions used in this pack

- **`sgi`** is the CLI binary; **`sg_image_builder`** is the Python package
- **`sg`, `sgc`, `sg lc`** refer to the existing sg-compute tooling — sgi may *consume* it via an `Exec_Provider`, but **sgi never modifies sg-compute code**
- **Bundle**, **recipe**, **spec**, **workspace** are technical terms defined precisely in [00__pack-overview/quick-reference.md](00__pack-overview/quick-reference.md)
- **Provider** = an abstract interface with multiple concrete implementations (e.g. `Storage`, `Exec_Provider`)
- **IFD** = Iterative Flow Development versioning (`v0/v0.1/v0.1.0/`)
- Code conventions follow `SGraph-AI__Service__Playwright`: `Type_Safe` classes, single class per file, `Word__Word__Word.py` naming, no Pydantic, no boto3 direct calls (always `osbot-aws`)

## Scope boundaries

**In scope for v1:**
- Capture → package → publish → load → test → strip → benchmark for one spec end-to-end
- Storage abstraction with S3 + local-disk + in-memory implementations
- Execution abstraction with SSH (osbot-utils) + sg-compute CLI shell-out + twin implementations
- Workspace-folder state model (no global config)
- All 9 specs from `ssh_file_server` to `vllm_docker`
- Single-zipapp distribution target

**Out of scope for v1 (designed not to preclude):**
- Graph-queryable metadata (structure supports it; queries deferred)
- Runtime granular module loading (sidecar can declare modules; runtime support deferred)
- Multi-arch / multi-OS variants (storage path supports it; only x86_64 + AL2023 populated)
- Fractal package manager nesting (storage cascade-lookup deferred)
- Vault sidecar commercial layer (strategic, not architectural)
- A "real" package manager on top — that's the next pack

**Explicitly disallowed:**
- Modifications to `sg-compute` code (changes there are filed as feedback briefs)
- Direct boto3 calls in sgi code (must go through `osbot-aws` or providers)
- Hidden config files (`~/.sgi/`, `.sgi/`, etc.) — workspace folder is the only state
- Reimplementing what an upstream package already does (apt, pip, dnf, docker — use as-is)

## Related external context

Two documents preceded this pack and should be available to any implementer who needs deeper background:

- `v0.27.32__dev-brief__ec2-image-build-cli-s3-first.md` — the original framing
- `v0.27.32__arch-brief__sg-compute-package-manager.md` — the broader package-manager vision (sgi is the foundation layer of this)

Two existing repos contain patterns sgi adopts:

- `SGraph-AI__Service__Playwright` — `Type_Safe` conventions, `Spec__CLI__Builder`, service layer patterns, `Section__*` user-data pattern
- `SG_Send__Deploy` — Provider/Twin pattern, `Type__Twin` base classes, `Operation__*` orchestration pattern

Implementers should clone both for reference before starting.
