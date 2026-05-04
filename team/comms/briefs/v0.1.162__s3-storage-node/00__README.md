# v0.1.162 — S3 Storage Node Spec

**Status:** PROPOSED
**Version:** v0.1.162
**Date:** 2026-05-04
**From:** Developer Agent (Node Specs session)
**To:** Architect, Dev
**Type:** Feature brief — new Node Spec

---

## Goal

Introduce `sg_compute_specs/s3_server/` — a boto3-transparent S3-compatible
storage node that any S3 SDK can talk to without modification.  The node
provides a call log (every request in/out), four operation modes (Full Local,
Full Proxy, Hybrid, Selective), and a browser UI for browsing buckets/objects
and watching the live call log.

---

## Source brief

Human arch brief: `v0.27.2__arch-brief — S3-Compatible API: Full boto3
Transparency, Proxy Modes, and Call Logging` (30 Apr 2026).

---

## Why this matters

- osbot-aws, Memory-FS, SGit, and the Cyber Boardroom all call boto3 S3.
- Pointing them at this node (via `endpoint_url`) removes the AWS dependency
  for development, testing, and air-gapped deployment — zero code changes on
  the caller side.
- The call log turns unknown S3 usage patterns into a concrete implementation
  backlog: we only build what gets called.

---

## Files in this brief

| File | Audience | Content |
|------|----------|---------|
| `01__architecture.md` | Architect, Dev | Design decisions, capability additions, spec folder layout, relationship to Memory-FS, phased delivery |
| `02__node-spec-brief.md` | Dev | Concrete task list — enums, primitives, schemas, service helpers, routes, tests, Docker image |

Read `01__architecture.md` first to understand the shape before the task list.

---

## What this brief does NOT cover

- The S3 server implementation itself (HTTP request parsing, SigV4 validation,
  XML response serialisation) — that lives in a separate `sg_s3_server/`
  package, described in `01__architecture.md` §6.
- Memory-FS integration internals — pending confirmation of the Memory-FS
  storage-backend interface (see `01__architecture.md` §5).
- UI web-component design — deferred to a frontend brief once the API surface
  is locked.
- Phases 2–4 (core ops local, full local, sync backends) — gated on Phase 1
  call-log data.

---

## Open question for the human

> The brief says to leverage Memory-FS abstractions for the storage backend.
> Memory-FS is described as a separate project.  To write the `S3_Server__Backend`
> interface correctly we need to know:
>
> 1. What Python package name / import path does Memory-FS expose?
> 2. Does it already have a `put(key, data)` / `get(key)` / `list(prefix)` /
>    `delete(key)` surface, or do we need to map from a different abstraction?
> 3. Is Memory-FS available on PyPI, or is it a local/editable install?
>
> We can proceed without answers — the Phase 1 spec uses only an in-memory
> dict backend and clearly marks the Memory-FS seam with a TODO.  Fill in the
> answers before Phase 2 to unlock the Vault and real-S3 backends.
