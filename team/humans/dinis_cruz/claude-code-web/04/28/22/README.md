# Plan: `sp linux` + `sp docker` CLI sections
**Date:** 2026-04-28  
**Branch:** `claude/spell-commands-observability-vO6wV`  
**Target version:** v0.1.102 (`sp linux`) + v0.1.103 (`sp docker`)

---

## One-paragraph summary

Two new `sp` CLI sections, each a thin wrapper over a bare AL2023 EC2 instance.
`sp linux` spins up a plain Amazon Linux 2023 instance reachable via SSM — no
Docker, no open ports unless explicitly requested.  `sp docker` is identical
except its cloud-init user-data installs Docker + the compose plugin and
optionally pulls and starts a container.  Both sections are ~90% copied from
the proven `sp el` / `sp os` templates with service-specific naming, tags,
user-data, and health checks.

---

## Reading order

| Doc | Purpose |
|-----|---------|
| [`01__reuse-and-foundations.md`](01__reuse-and-foundations.md) | What can be copied verbatim vs what must be written fresh |
| [`02__folder-layout-and-schemas.md`](02__folder-layout-and-schemas.md) | Exact file trees + every schema field |
| [`03__cli-surface-and-user-data.md`](03__cli-surface-and-user-data.md) | Full CLI surface + cloud-init templates |
| [`04__phases.md`](04__phases.md) | PR-sized implementation phases for Dev |
