# Reality — SG/Compute Domain

**Status:** PLACEHOLDER — seeded in phase-1 (B1 rename). Full content lands in phase-2 (B2 foundations).
**Last updated:** 2026-05-02 | **Phase:** B1 (rename)

---

## What exists today (as of phase-1 / B1)

### Packages

| Package | Location | Description |
|---------|----------|-------------|
| `sg_compute` | `sg_compute/` | SDK — shared helpers for EC2 provisioning, health polling, user-data assembly |
| `sg_compute_specs` | `sg_compute_specs/` | Spec catalogue — pilot specs only (ollama, open_design) |
| `sg_compute__tests` | `sg_compute__tests/` | Test suite mirroring `sg_compute/` layout |

### sg_compute/helpers/ — EXISTS

| Class | Path | Description |
|-------|------|-------------|
| `EC2__Launch__Helper` | `helpers/aws/EC2__Launch__Helper.py` | RunInstances wrapper |
| `EC2__SG__Helper` | `helpers/aws/EC2__SG__Helper.py` | CreateSecurityGroup / AuthorizeIngress |
| `EC2__Tags__Builder` | `helpers/aws/EC2__Tags__Builder.py` | Standard EC2 tag list construction |
| `EC2__AMI__Helper` | `helpers/aws/EC2__AMI__Helper.py` | SSM latest AL2023 AMI lookup |
| `EC2__Instance__Helper` | `helpers/aws/EC2__Instance__Helper.py` | DescribeInstances, find-by-tag, terminate |
| `EC2__Stack__Mapper` | `helpers/aws/EC2__Stack__Mapper.py` | boto3 dict → Schema__Stack__Info |
| `Stack__Naming` | `helpers/aws/Stack__Naming.py` | Stack name helpers |
| `Section__Base` | `helpers/user_data/Section__Base.py` | Hostname, locale, common packages |
| `Section__Docker` | `helpers/user_data/Section__Docker.py` | Docker CE install |
| `Section__Node` | `helpers/user_data/Section__Node.py` | Node.js 24 + pnpm |
| `Section__Nginx` | `helpers/user_data/Section__Nginx.py` | nginx reverse-proxy (SSE-safe) |
| `Section__Env__File` | `helpers/user_data/Section__Env__File.py` | Write env file to tmpfs |
| `Section__Shutdown` | `helpers/user_data/Section__Shutdown.py` | systemd-run auto-terminate timer |
| `Health__Poller` | `helpers/health/Health__Poller.py` | Polls EC2 state + app port |
| `Health__HTTP__Probe` | `helpers/health/Health__HTTP__Probe.py` | HTTP GET with retry |
| `Caller__IP__Detector` | `helpers/networking/Caller__IP__Detector.py` | Public IP from ifconfig.me |
| `Stack__Name__Generator` | `helpers/networking/Stack__Name__Generator.py` | Adjective-noun random names |
| `Schema__Stack__Info` | `helpers/schemas/Schema__Stack__Info.py` | Base node info schema |

### sg_compute_specs/ — EXISTS (pilot specs)

| Spec | Location | Description |
|------|----------|-------------|
| `ollama` | `sg_compute_specs/ollama/` | Ollama LLM runtime on GPU EC2 |
| `open_design` | `sg_compute_specs/open_design/` | Open Design Node.js platform |

---

## PROPOSED — does not exist yet

Everything in [`team/comms/briefs/v0.1.140__sg-compute__migration/`](../../../comms/briefs/v0.1.140__sg-compute__migration/00__README.md) phase 2+:

- `sg_compute/primitives/` — Safe_Str__* and Enum__* types
- `sg_compute/core/` — Node__Manager, Pod__Manager, Spec__Loader, Spec__Resolver
- `sg_compute/platforms/ec2/` — Platform interface + EC2 implementation
- Spec manifests (`manifest.py` with `MANIFEST: Schema__Spec__Manifest__Entry`)
- `Fast_API__Compute` control plane
- `sg-compute` CLI command

---

## History

| Date | Change |
|------|--------|
| 2026-05-02 | Phase B1: `ephemeral_ec2/` renamed to `sg_compute/`; pilot specs moved to `sg_compute_specs/`; domain placeholder created |
