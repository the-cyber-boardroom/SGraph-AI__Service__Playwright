# Security Model

This document exists because the upstream brief, as originally written, proposed
something `.claude/CLAUDE.md` explicitly forbids: running "whatever setup-scripts
are inside the vault folder" on infrastructure we own. That is arbitrary code
execution from an externally-influenced source. This pack's design closes that
hole. AppSec must review and accept the residual-risk statement in §6 before
Phase 2a.

---

## 1. The threat

The slug → vault location is **deterministic and predictable**. Anyone who knows
the derivation can compute where any slug's data lives. The naive failure mode:
an attacker derives a slug's location, writes a malicious provisioning manifest
there, and our waker runs it on a fresh EC2 instance — arbitrary code execution on
our infrastructure, billed to us.

## 2. The defences, and why they hold

The design does **not** rely on the location being secret. It relies on two
independent properties of the payload and the channel:

### 2.1 SG/API files are immutable (locked decision #4)

A published vault folder cannot be overwritten. An attacker who derives a slug's
location cannot replace its content. The only thing they could do is *be the first
to publish* at a slug they do not own — which is governed by SG/Send's publish-side
ownership, and by the slug → owner binding in the billing record.

### 2.2 The provisioning manifest is signature-verified (locked decision #6)

Before `StartInstances` is ever called, `Manifest__Verifier` checks the manifest
signature against the signing key bound to the slug in the billing record. Content
that does not verify is discarded — no instance starts, no provisioning runs.

**Together:** the location can be public, because the payload is authenticated and
the channel is immutable. This is the "trust the payload, not the location"
principle made concrete.

## 3. Declarative, not imperative (locked decision #5)

Even a *verified* manifest is not executed as code. `Manifest__Interpreter` maps it
against an allowlisted vocabulary — there is no `command` / `script` / `exec` field
in the MVP vocabulary. The worst a malicious-but-somehow-verified manifest can do
is declare allowlisted operations. Arbitrary scripts require Architect + AppSec
sign-off and a logged decision, exactly like widening the JS allowlist.

## 4. The control-plane key (locked decision #7)

- **Random, single-use, per-instance** — not a shared env-var secret. A leaked key
  compromises one instance for one setup window, not the fleet.
- Delivered via EC2 user-data / IMDSv2 — never over any CloudFront-facing channel.
- The control-plane **setup endpoint closes after provisioning**. The
  configuration surface is allowlisted, authenticated, single-use, and
  time-bounded.

## 5. Isolation — blast radius is one instance (principle 9)

Defence in depth behind the signing check:

- per-slug instance in a **private subnet**, no public IPv4 (locked decision #8),
- unprivileged runtime user for the vault app,
- **no AWS credentials on the box**, or a tightly-scoped instance role that can do
  nothing but what the vault app needs,
- security-group egress restricted to the SG/API path and CloudFront,
- the instance cannot reach other per-slug instances.

A fully compromised vault instance can affect itself and nothing else.

## 6. Residual-risk statement (AppSec sign-off required)

With immutability + signing + declarative interpretation + isolation in place, the
residual risks are:

| Risk | Severity | Mitigation / status |
|------|----------|---------------------|
| An attacker publishes first at a slug they do not own | Medium | Governed by SG/Send publish-side ownership + the billing-record owner binding. Open question #2 — **must be confirmed before Phase 2a.** |
| An attacker overwrites a slug's content | **Closed** | SG/API files are immutable. |
| An attacker forges a manifest our infra acts on | **Closed** | Manifest is signature-verified before any side effect. |
| Arbitrary code execution via setup scripts | **Closed for MVP** | No `exec` field in the manifest vocabulary; scripts are a gated, logged exception only. |
| A verified manifest declares resource-heavy but allowlisted operations (denial-of-wallet) | Low–Medium | Bounded by the allowlist vocabulary + per-instance isolation + idle-shutdown. Quotas per owner are a Phase 3 refinement. |
| Signing-key compromise | Medium | Key custody is open question #4 — SG/Send owns the signing key lifecycle. |
| Lambda@Edge global blast radius (Phase 2b only) | Low | Phase 2b edge code is minimal by principle 6; Phase 2a has no Lambda@Edge at all. |

**AppSec sign-off gate:** Phase 2a (the first phase that provisions from
externally-sourced input) does not start until AppSec has reviewed this document
and the four open questions in the pack README are answered — specifically #2
(billing-record owner binding) and #4 (signing-key custody).

## 7. What is explicitly out of scope for MVP security

- VPC-restricted vault access and S3-direct vault access — noted as future
  hardening (locked decision #13). The immutability + signing model is the MVP bar.
- Per-owner resource quotas / denial-of-wallet limits — Phase 3.
- At-rest encryption of the manifest — Phase 2+. Signature verification is the MVP
  requirement; encryption is additive.
