# vault — Proposed

PROPOSED — does not exist yet. Items below extend the vault surface but are not in code today.

Last updated: 2026-05-17 | Domain: `vault/`
Sources: `sg-compute/index.md` PROPOSED section + history entries, BV2.9 follow-ons.

---

## P-1 · Real vault I/O

**What:** `Vault__Spec__Writer` today uses an in-memory dict with `vault_attached=True`. Persistent vault wiring is deferred to v0.3.

**Required:**

- Choose backing store (S3 + KMS? Vault HashiCorp? AWS Secrets Manager?). Must support per-(spec_id, stack_id, handle) namespacing.
- Migration plan for existing in-memory writes (UI preferences, future per-stack receipts).
- Preserve `Schema__Vault__Write__Receipt` shape so callers don't change.

**Source:** `sg-compute/index.md` PROPOSED.

## P-2 · Vault-sourced sidecar API key

**What:** Follow-on to BV2.9. The host-control plane's API key today is provisioned via env var on the EC2 instance. Sourcing it from vault would let it rotate without re-provisioning.

**Source:** `sg-compute/index.md` PROPOSED.

## P-3 · Delete the `sgraph_ai_service_playwright__cli/vault/` shims

**What:** All 11 shim files are flagged for deletion in BV2.12 — one-release backwards compatibility window. Track and execute the removal.

**Source:** BV2.9 shim comment headers ("Delete in BV2.12").

## P-4 · `sg playwright vault re-cert --hostname <fqdn>`

**What:** Referenced in the cert-warning info block printed by `sg aws dns records add`, but does not exist. **Q9 still PENDING** (DNS-01 vs HTTP-01 for the cert sidecar).

Cross-references: [`cli/aws-dns.md`](../cli/aws-dns.md) known-gaps; `cli/proposed/index.md` P-15.

**Source:** `_archive/v0.1.31/16__sg-aws-dns-and-acm.md` known-gaps (§12 ADDENDUM).
