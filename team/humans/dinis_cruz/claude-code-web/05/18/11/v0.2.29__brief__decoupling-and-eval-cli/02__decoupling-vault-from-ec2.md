---
title: "02 — Decoupling vault from the ephemeral-EC2 layer"
file: 02__decoupling-vault-from-ec2.md
author: Claude (Architect)
date: 2026-05-18 (UTC hour 11)
parent: README.md
---

# 02 — Decoupling vault from the ephemeral-EC2 layer

## The observation

The waker does ~5 things:

1. Receives a request, extracts the slug from the Host header.
2. Looks up the slug → instance-id in SSM.
3. Asks EC2 about that instance's state + IP.
4. If STOPPED, starts it. If PENDING/STOPPING, waits.
5. If RUNNING + healthy, proxies the request to `<ip>:8080`.

**Steps 1–4 know nothing about vault-app.** They'd work identically
for any workload that needs cold-start-on-demand:
- A Jupyter notebook server
- A game-server backend
- A demo of a customer's app
- An LLM inference endpoint

**Step 5 is where the coupling lives.** Three vault-app specifics
are baked into the waker code:
- Health probe path: `/ui/#!/login`
- Vault URL construction: `http://{ip}:8080`
- The render of "warming" copy says "vault" instead of "service"

That coupling is small (~10 lines in `Waker__Handler` and
`Waker__Page.render`), but it's enough that the abstraction isn't
clean today.

The naming makes it worse: the sub-package is
`sg_compute_specs/vault_publish/`, the Lambda is
`sg-compute-vault-publish-waker`, the SSM prefix is
`/sg-compute/vault-publish/slugs/`. Anyone reading the code assumes
"this is about vaults" — when really 80 % of it is about ephemeral
EC2 lifecycle.

---

## Three options

### Option A — Leave it. Document the implicit decoupling.

Keep the names. Add a docstring on `Waker__Handler` listing the
three vault-app-specific points. Future workloads (if any) can
either fork the package or be added as fields on the SSM entry.

**Pros:** zero refactoring. No name churn. Everything operators have
in muscle memory still works.

**Cons:** the next person reading `Waker__Handler` assumes vault is
core to the design. The name promises more coupling than exists.
And the "future workloads" path is a fork, which is not actually
acceptable for a real second use case.

---

### Option B — Extract a generic `ephemeral-ec2` sub-package; vault-publish becomes a thin caller.

```
sg_compute_specs/
├── ephemeral_ec2/                 (new, generic)
│   ├── waker/                     (Lambda code)
│   ├── service/
│   │   ├── Slug__Registry.py
│   │   ├── Endpoint__Resolver__EC2.py
│   │   └── Workload__Probe.py     (knows how to call <health_path> on <port>)
│   └── schemas/
│       └── Schema__Workload__Entry.py   (slug, instance_id, port, health_path)
│
└── vault_publish/                 (existing, narrowed)
    ├── service/
    │   └── Vault_Publish__Service.py
    │       └── on register(): calls vault_app.create_stack(),
    │                          then ephemeral_ec2.register(workload)
    └── schemas/                   (vault-specific request types)
```

The Lambda is renamed `sg-compute-ephemeral-ec2-waker`. The CLI
keeps `sg vault-publish register sara-cv --vault-key x` for the
vault use case; a new `sg ephemeral-ec2 register …` exists for
generic use.

**Pros:**
- Clean separation. Re-use for non-vault workloads is genuine, not
  fork-and-modify.
- The waker code becomes truly workload-agnostic (no vault strings).
- Setup architecture (IAM, CF, Lambda, etc.) is unambiguously
  *infrastructure* — vault is one consumer.

**Cons:**
- Big rename. Touches dozens of files, every reality doc, every CLI
  help string, the Lambda name (which means a fresh deploy + DNS
  swap), the SSM prefix (which means migrating existing entries).
- Cost of churn for a benefit (multi-workload) we don't actually
  need today.
- Lambda function rename is operationally painful: existing
  CloudFront distribution points at the old Function URL; renaming
  the function = new URL = update CF origin = wait 15 min for
  deployment.

---

### Option C — Keep the package name; extract a `Workload` seam internally; per-slug config in SSM.

```
sg_compute_specs/vault_publish/                 (name stays)
├── waker/
│   ├── Waker__Handler.py                       (workload-agnostic)
│   └── Workload__Probe.py                      (NEW — health/port/url builder)
│
├── schemas/
│   └── Schema__Vault_Publish__Entry.py
│       ├── slug
│       ├── instance_id                         (existing)
│       ├── port              : int = 8080      (NEW)
│       ├── health_path       : str = '/ui/#!/login'  (NEW — vault default)
│       └── warming_label     : str = 'vault'   (NEW — used in warming HTML)
```

`Waker__Handler` reads `port` and `health_path` from the SSM entry,
constructs `vault_url` and probe URL accordingly. No vault strings
in waker code; the *defaults* in `register` are vault-app-shaped,
but anyone with a different workload can write a different SSM entry
and the waker just works.

**Pros:**
- No package rename. No Lambda rename. No CF re-pointing. No SSM
  prefix migration.
- The vault-app-specific stuff is config (in SSM), not code (in
  Lambda). Code reads as generic; the entries are the policy.
- Operators can register a non-vault workload tomorrow by writing a
  custom entry — no Lambda redeploy.
- The mental model becomes: "vault-publish is the *current default
  workload shape*; the runtime is workload-agnostic."

**Cons:**
- Per-slug config means more SSM data to manage. Default values
  hide most of it from operators.
- The package name `vault_publish` will become slightly misleading
  over time if non-vault workloads multiply. Manageable with a
  README note for now; rename later if real second-workload use case
  appears.

---

## Recommendation: Option C

**Cleanest separation that doesn't churn names.** The decoupling
happens inside the code, not in the file paths. Per-slug
`port` / `health_path` / `warming_label` in the SSM entry is the
mechanism — code becomes truly generic, config carries the workload
shape.

Concrete changes:

1. **Add fields** to `Schema__Vault_Publish__Entry`:
   ```python
   port           : int = 8080
   health_path    : str = '/ui/#!/login'
   warming_label  : str = 'vault'
   ```
   All three have defaults that preserve current behaviour.

2. **`Endpoint__Resolver__EC2.resolve`** uses entry.port to build
   `vault_url` (rename to `workload_url`).

3. **`Waker__Handler._health_ok`** uses entry.health_path for the
   probe URL.

4. **`Waker__Page.render`** uses entry.warming_label for the user-
   facing copy ("your vault is warming up" stays for vault entries;
   non-vault entries get their label).

5. **`Vault_Publish__Service.register`** continues to set vault
   defaults — vault-publish CLI semantically guarantees vault
   defaults. A separate `sg ephemeral-ec2 register` could expose the
   custom fields when a second workload arrives.

Estimated effort: 0.5–1 day. Reality-doc + tests for the new fields.

---

## What the new flow looks like

```
Browser request → CloudFront → Lambda waker
    │
    │ event.host = 'sara-cv.aws.sg-labs.app'
    │
    ▼
Slug__From_Host('sara-cv.aws.sg-labs.app') → 'sara-cv'
    │
    ▼
Slug__Registry.get('sara-cv')
    │     ↓ returns:
    │       Schema__Vault_Publish__Entry(
    │         slug          = 'sara-cv',
    │         instance_id   = 'i-0abc1234',
    │         port          = 8080,
    │         health_path   = '/ui/#!/login',
    │         warming_label = 'vault',
    │       )
    │
    ▼
Endpoint__Resolver__EC2.resolve(entry)
    │     ↓ returns:
    │       Schema__Endpoint__Resolution(
    │         instance_id = 'i-0abc1234',
    │         public_ip   = '1.2.3.4',
    │         state       = RUNNING,
    │         workload_url= 'http://1.2.3.4:8080',   ← built from entry.port
    │       )
    │
    ▼
Waker__Handler decides what to do.
    │
    │  Health probe = workload_url + entry.health_path
    │  Warming HTML = entry.warming_label
    │
    ▼
Response
```

Notice the waker now only references **entry.port**, **entry.health_path**, **entry.warming_label** — no hard-coded vault strings.

---

## What it doesn't change

- The setup architecture (IAM, Lambda, Function URL, CF, DNS, ACM)
  stays as-is. Setup is workload-agnostic by construction.
- The SSM prefix `/sg-compute/vault-publish/slugs/` stays. Renaming
  it later is cheap (migrate entries in a one-shot script) and
  cosmetic.
- The Lambda name `sg-compute-vault-publish-waker` stays. Could
  rename later when we want to.

## What it unblocks

- The eval CLI ([05](05__eval-cli-step-by-step.md)) can include "test
  with a fake non-vault workload" — a tiny `python -m http.server`
  registered as a slug with `port=8000, health_path='/'`. End-to-end
  proof that the decoupling held.
- A future "demo-publish" or "jupyter-publish" CLI can reuse 100 % of
  the waker + setup machinery just by writing a different entry
  shape — no Lambda redeploy, no infra changes.
