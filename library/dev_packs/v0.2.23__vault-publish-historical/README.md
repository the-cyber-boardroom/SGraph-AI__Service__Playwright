---
title: "Vault-Publish — Historical Snapshot (top-level `vault_publish/` package)"
file: README.md
captured_on: 2026-05-17
status: HISTORICAL — frozen reference, not on the Python path
source_branch: origin/claude/review-subdomain-workflow-bRIbm
source_commits:
  - c1848679 — feat(vault-publish): implement the vault-publish Python package
  - 23c28006 — feat(vault-publish): add runnable CLI + local FastAPI launcher
superseded_by: sg_compute_specs/vault_publish/
---

# Vault-Publish — Historical Snapshot

This is a frozen snapshot of the **original** top-level `vault_publish/` package and its `vp-server` launcher, captured from `origin/claude/review-subdomain-workflow-bRIbm` before that branch was retired.

The live code now lives at [`sg_compute_specs/vault_publish/`](../../../sg_compute_specs/vault_publish/) — moved there as part of the BV2.9 "spec inside `sg_compute_specs/`" refactor (see [v2 brief](../../../team/humans/dinis_cruz/claude-code-web/05/16/15/v0.2.23__brief__vault-publish-spec__v2/README.md)).

## Why this is kept

- Documents the original shape of the package before the move into `sg_compute_specs/`.
- Includes the `Fast_API__Vault_Publish` local-dev composer and `scripts/run_vault_publish.py` (the `vp-server` poetry script) — neither has a direct equivalent in the current `sg_compute_specs/vault_publish/` layout, which centres on the Waker Lambda (`Fast_API__Waker.py`) instead.
- The schemas, services (`Publish__Service`, `Slug__Resolver`, `Manifest__Verifier`, `Vault__Fetcher`, `Instance__Manager`, …) and the `Routes__Vault_Publish` route surface here predate the canonical home and may differ subtly.

## Don't import from here

The files live under `library/dev_packs/`, which is **not on the Python path**. They will not be picked up by imports, tests, or CI. Treat them as a reference snapshot — if you need the live code, go to `sg_compute_specs/vault_publish/`.

## Contents

```
v0.2.23__vault-publish-historical/
├── README.md                              ← this file
├── scripts/
│   └── run_vault_publish.py               ← original `vp-server` launcher
└── vault_publish/
    ├── __init__.py
    ├── cli/Cli__Vault_Publish.py
    ├── fast_api/
    │   ├── Fast_API__Vault_Publish.py     ← local-dev composer (no longer present)
    │   └── Routes__Vault_Publish.py
    ├── schemas/                           ← 40 schema / primitive / enum / collection files
    ├── service/                           ← 11 service classes + `reserved/`
    ├── version
    └── waker/Waker__Lambda__Adapter.py    ← superseded by sg_compute_specs/vault_publish/waker/Fast_API__Waker.py
```

## See also

- Live code: [`sg_compute_specs/vault_publish/`](../../../sg_compute_specs/vault_publish/)
- v2 architect brief: [`team/humans/dinis_cruz/claude-code-web/05/16/15/v0.2.23__brief__vault-publish-spec__v2/`](../../../team/humans/dinis_cruz/claude-code-web/05/16/15/v0.2.23__brief__vault-publish-spec__v2/README.md)
- v1 dev pack: [`library/dev_packs/v0.2.11__vault-publish/`](../v0.2.11__vault-publish/)
