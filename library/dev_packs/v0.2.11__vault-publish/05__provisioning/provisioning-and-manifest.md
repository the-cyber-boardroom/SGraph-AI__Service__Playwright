# Provisioning and the Declarative Manifest

How a slug becomes a running, configured vault instance — without ever executing
arbitrary code from an untrusted source.

---

## 1. Slug → vault, deterministically

There is **no routing table**. `Slug__Resolver` runs a deterministic, server-side
derivation that converts the slug into an SG/API `(Transfer-ID, read key)` pair,
reusing the existing simple-token mechanism. The same input always yields the same
location.

The only per-slug state is the **billing record** — which already exists, because
slug validation was first introduced for billing. It carries:

- the slug → owner binding,
- the signing public key (or a reference to it) used to verify the manifest.

So "no new persistence" (principle 4) holds: derivation needs no store, and the
integrity metadata hangs off a record that already exists.

> **Cross-repo dependency.** The derivation function and the billing-record schema
> live in SG/Send. Confirming them is open question #1 and #2 in the pack README.

---

## 2. Fetching the vault folder

`Vault__Fetcher` is the only class that talks to SG/API. It fetches the vault
folder from `send.sgraph.ai` by `(Transfer-ID, read key)`. The folder is
**immutable** (locked decision #4) — once published it cannot be overwritten. It
contains:

- the **site content** the vault app serves (intentionally public — this is the
  product),
- a **provisioning manifest** — the declarative document that configures the
  instance.

These are two different trust domains. The site content is public and may be
location-predictable; that is fine. The provisioning manifest *drives our
infrastructure* and must be authenticated before it is acted on.

---

## 3. The manifest is signature-verified — before anything starts

`Manifest__Verifier` checks the manifest's signature against the signing key from
the billing record. This happens in the wake sequence **before `StartInstances` is
called**. If verification fails, the wake sequence stops and returns an error page
— no instance is started, no provisioning runs.

This is the load-bearing control. Because SG/API files are immutable *and* the
manifest is signed, an attacker who can derive a slug's location can neither
overwrite its content nor forge a manifest our infrastructure will act on. Trust is
in the payload, not the location (principle 2).

Signature verification is an **MVP requirement**, not a deferred hardening. At-rest
encryption of the manifest can come later; the signature check cannot.

---

## 4. The declarative manifest

The manifest declares *intent*, not *commands*. It is interpreted by
`Manifest__Interpreter` against an **allowlisted vocabulary** — the same
deny-by-default posture as the repo's JS expression allowlist.

Illustrative shape (the concrete schema is in `07__schemas`):

```
  vault-app manifest
    app_type        : one of an Enum__ (e.g. static-site, vault-js-app)
    content_root    : path within the vault folder to serve
    runtime         : one of an Enum__ (allowlisted runtimes only)
    env             : a typed, allowlisted set of key/value settings
    routes          : declarative route table (path → content mapping)
    health_path     : the path the warming page polls
    (no "command", no "script", no "exec" field exists in the vocabulary)
```

The interpreter maps each declared field to a concrete, bounded control-plane
operation. If the manifest declares something the vocabulary does not cover, the
interpreter rejects it — it never falls through to "just run it".

**Arbitrary scripts are the explicit last resort.** If a real use case genuinely
cannot be expressed declaratively, an `exec`-style capability may be added — but
only with Architect + AppSec sign-off and a logged decision, exactly like widening
the JS allowlist. It is never the default path, and it is never in the MVP
vocabulary.

---

## 5. Driving the control-plane

`Control_Plane__Client` provisions the instance through the FastAPI control-plane
that this repo already adds to every instance it creates. The sequence:

1. The waker generates a **random, single-use** control-plane key.
2. The key is delivered to the instance via EC2 user-data / IMDSv2 — never over any
   CloudFront-facing channel.
3. `Control_Plane__Client` calls the instance's control-plane, authenticated with
   that key, passing the **verified** declarative manifest.
4. The instance's control-plane interprets the manifest, configures the app, and
   reports healthy.
5. The control-plane **setup endpoint closes**. A per-slug instance pulls its
   content at boot and never needs re-provisioning in its lifetime — so the
   code-configuration surface exists only inside a bounded setup window, then is
   gone.

This keeps the spirit of `.claude/CLAUDE.md` #11 even though provisioning, by
nature, configures a machine: the surface is allowlisted, authenticated, single-use,
and time-bounded.

---

## 6. Boot, idle, stop

- **Boot.** Generic AMI. The instance pulls its vault content from SG/API at boot —
  nothing slug-specific is baked into a snapshot (slim-AMI principle, locked
  decision #9). It arms an idle-shutdown timer.
- **Live.** Activity re-arms the timer. CloudFront serves traffic from the instance.
- **Idle.** The timer fires; the instance stops itself. State on the NVMe/instance
  store is ephemeral and that is fine — the next wake re-fetches the immutable
  vault folder and re-provisions from scratch. Re-provisioning is deterministic
  because every input (the vault folder, the manifest) is immutable.

---

## 7. Vault updates propagate automatically

Because the instance re-fetches the vault folder on each cold boot, a vault update
becomes live the next time the instance is woken — no "republish" step. For a
long-lived warm instance, a content-refresh path (re-fetch without a full reboot)
is a Phase 3+ refinement; the MVP relies on the boot-time fetch and the idle/wake
cycle.
