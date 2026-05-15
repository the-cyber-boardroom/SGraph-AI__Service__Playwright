# Principles

The principles that govern every design decision in this pack. When a detailed
choice is ambiguous, resolve it by returning to these.

---

## 1. One service layer, three callers

`vault-publish` is not "a Lambda" or "a CLI" — it is a set of pure `Type_Safe`
service classes. The FastAPI routes, the `sg vp` CLI, and the CloudFront-invoked
waker Lambda are **all thin callers of the same classes**. No business logic lives
in a route, a Typer command, or a Lambda handler. This is the CLI/FastAPI duality
the repo already practises, extended with one more caller (the edge).

## 2. Trust the payload, not the location

The slug → vault location is deterministic and therefore *predictable*. Security
must never depend on that location being secret. It depends on two things instead:
SG/API files are **immutable** (the location cannot be overwritten) and the
provisioning manifest is **signature-verified** (content that does not verify is
discarded). A predictable address is fine when the payload is authenticated.

## 3. Declarative over imperative

The vault tells the instance *what* it wants; the instance's control-plane decides
*how*, and only from an allowlisted vocabulary. `bash setup.sh` is the pattern this
codebase was built to reject (`.claude/CLAUDE.md` #11). Arbitrary scripts are a
last resort, gated by Architect + AppSec sign-off and a logged decision — never the
default path.

## 4. No new persistence unless it earns its place

The upstream brief conceded a slug → token KV. This design removes it: derivation
is deterministic, and the only per-slug state — the billing record — already
exists. Before adding any store, ask whether an existing one can carry the data.

## 5. The wildcard does the work once

One wildcard DNS record, one wildcard certificate, one CloudFront distribution —
provisioned once and then forgotten. Per-slug provisioning latency (DNS
propagation, cert issuance) is designed *out*, not optimised. The only thing that
varies per request is the origin.

## 6. As small as possible at the edge

The waker Lambda carries the least code that can possibly work: the Lambda Web
Adapter plus the same FastAPI app the CLI uses. Edge-specific logic is confined to
request translation. The smaller the edge surface, the smaller the thing that can
break globally.

## 7. Pull at boot, bake nothing large

Per-slug instances run a generic AMI and pull their vault content from SG/API at
boot. Nothing slug-specific is baked into a snapshot. This inherits the slim-AMI
principle (`SPEC-slim-ami-s3-nvme`): an EBS snapshot that carries large data pays a
lazy-load tax on every fresh launch — so it carries none.

## 8. Reuse the patterns already in the repo

The idle-shutdown timer (`sg lc extend`), the per-instance control-plane FastAPI,
the Lambda Web Adapter single-image model, the `Spec__CLI__Builder` verb-tree
shape, the in-memory test composition — all already exist. `vault-publish` is a
new *caller* of established patterns, not a new set of patterns.

## 9. Blast radius is one instance

A compromised or malformed vault must not be able to affect anything beyond its own
per-slug instance. Private subnet, unprivileged runtime user, no AWS credentials on
the box (or a tightly-scoped instance role), security-group egress restricted to
the SG/API path, single-use control-plane key, control-plane endpoint closed after
setup. Isolation is the backstop behind the signing check.

## 10. Phase the risk, not just the features

Phase 1 proves routing with an always-on instance — no waking logic, no
provisioning-from-untrusted-input. Phase 2a adds waking in its simplest possible
form. Phase 2b optimises only what Phase 2a measured. Each phase ends with a
demonstrable result and adds exactly one new class of risk.

## 11. Region and custom-domain are additive, not foundational

`slug.region.sgraph.app` and bring-your-own-domain are real futures, but the MVP
hostname scheme and routing must not be *shaped* by them. They attach later as new
wildcard SANs and new origin entries without redesign.
