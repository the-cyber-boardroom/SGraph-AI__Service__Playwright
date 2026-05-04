# SG/Compute — Overview & Vision

## What it is

**SG/Compute** is a Python SDK and CLI for launching, configuring, health-checking, and
auto-terminating AWS EC2 instances that run a single well-defined application spec.

Each spec is declared as a small Python module. The SDK provides all the shared machinery:
EC2 launch, security-group management, user-data assembly, health polling, and auto-terminate
timers. A new spec is typically 3–5 files.

## The brand name

Package: `sg-compute`  
PyPI: available (not yet registered as of 2026-05-01)  
Python import: `sg_compute`  
CLI prefix: `sg-compute <verb> <args>` (verbs: `node`, `pod`, `spec`, `stack`)

## Core design principles

1. **One app per node** — each EC2 node runs exactly one spec. No Kubernetes, no ECS, no
   orchestrator. Simplicity is the point.

2. **Ephemeral by default** — every instance carries an auto-terminate timer (`systemd-run`
   + `InstanceInitiatedShutdownBehavior=terminate`). The default is 1 hour; callers opt in to
   longer lifetimes explicitly.

3. **Containers where natural, bare where simpler** — Docker or Podman is always installed on
   the instance as baseline infrastructure. Whether the application process runs inside a
   container or directly on the host is a per-spec decision, not a platform constraint.

4. **Secrets never in AMIs or Git** — API keys and passwords travel only through EC2 user-data
   (gzip+base64, IAM-gated in Launch Templates) and live only in RAM on the running instance.

5. **AMI-baked for fast boot** — heavy install steps (package downloads, build artefacts) are
   baked into a spec-specific AMI. Boot from a baked AMI targets under 60 seconds to
   health-ready.

6. **SDK, not framework** — callers compose helpers; helpers do not call back into spec code.
   No base classes that must be subclassed. Dependency direction is always inward (spec →
   helpers, never helpers → spec).

## What this is not

- Not a general-purpose IaC tool (no Terraform/CloudFormation replacement)
- Not a container orchestrator
- Not a persistent-workload platform — stateful data lives in S3 or external databases, not on
  the instance disk (SQLite is acceptable for ephemeral session state)

## Relationship to SGraph-AI Service Playwright

`sg_compute` is developed inside the SGraph-AI Playwright mono-repo during its incubation
period. It is intentionally isolated in its own top-level folder (`sg_compute/`) with a
parallel test folder (`sg_compute__tests/`) so it can be extracted into its own repository
and published to PyPI without modification.

The existing CLI specs (`docker`, `podman`, `vnc`, `elastic`) are the lived experience that
informs this SDK's helper API. They are not replaced — they remain in
`sgraph_ai_service_playwright__cli/` and may eventually be migrated onto the SDK helpers.
