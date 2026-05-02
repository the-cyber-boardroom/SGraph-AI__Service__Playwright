# Ephemeral EC2 — Overview & Vision

## What it is

**Ephemeral EC2** is a Python SDK and CLI for launching, configuring, health-checking, and
auto-terminating AWS EC2 instances that run a single well-defined application stack.

Each stack is declared as a small Python module. The SDK provides all the shared machinery:
EC2 launch, security-group management, user-data assembly, health polling, and auto-terminate
timers. A new stack is typically 3–5 files.

## The brand name

Package: `ephemeral-ec2`  
PyPI: available (not yet registered as of 2026-05-01)  
Python import: `ephemeral_ec2`  
CLI prefix: `ec2 <stack> <command>` (e.g. `ec2 open-design create`)

## Core design principles

1. **One app per instance** — each EC2 runs exactly one stack. No Kubernetes, no ECS, no
   orchestrator. Simplicity is the point.

2. **Ephemeral by default** — every instance carries an auto-terminate timer (`systemd-run`
   + `InstanceInitiatedShutdownBehavior=terminate`). The default is 1 hour; callers opt in to
   longer lifetimes explicitly.

3. **Containers where natural, bare where simpler** — Docker or Podman is always installed on
   the instance as baseline infrastructure. Whether the application process runs inside a
   container or directly on the host is a per-stack decision, not a platform constraint.

4. **Secrets never in AMIs or Git** — API keys and passwords travel only through EC2 user-data
   (gzip+base64, IAM-gated in Launch Templates) and live only in RAM on the running instance.

5. **AMI-baked for fast boot** — heavy install steps (package downloads, build artefacts) are
   baked into a stack-specific AMI. Boot from a baked AMI targets under 60 seconds to
   health-ready.

6. **SDK, not framework** — callers compose helpers; helpers do not call back into stack code.
   No base classes that must be subclassed. Dependency direction is always inward (stack →
   helpers, never helpers → stack).

## What this is not

- Not a general-purpose IaC tool (no Terraform/CloudFormation replacement)
- Not a container orchestrator
- Not a persistent-workload platform — stateful data lives in S3 or external databases, not on
  the instance disk (SQLite is acceptable for ephemeral session state)

## Relationship to SGraph-AI Service Playwright

`ephemeral_ec2` is developed inside the SGraph-AI Playwright mono-repo during its incubation
period. It is intentionally isolated in its own top-level folder (`ephemeral_ec2/`) with a
parallel test folder (`ephemeral_ec2__tests/`) so it can be extracted into its own repository
and published to PyPI without modification.

The existing CLI stacks (`docker`, `podman`, `vnc`, `elastic`) are the lived experience that
informs this SDK's helper API. They are not replaced — they remain in
`sgraph_ai_service_playwright__cli/` and may eventually be migrated onto the SDK helpers.
