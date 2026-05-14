# Schemas and Module Tree

All schemas extend `Type_Safe`. Zero raw primitives — `Safe_*` primitives,
`Enum__*` types, and collection subclasses only. No Pydantic. No Literals. One
class per file (`.claude/CLAUDE.md` #21). This document names the classes; the Dev
session writes them in Phase 0 → Phase 1.

---

## 1. Module tree

```
  vault_publish/
    version
    schemas/
      Safe_Str__Slug.py
      Safe_Str__Transfer_Id.py
      Safe_Str__Read_Key.py
      Enum__Vault_App__Type.py
      Enum__Vault_App__Runtime.py
      Enum__Instance__State.py
      Enum__Wake__Outcome.py
      Schema__Slug__Billing_Record.py
      Schema__Vault__Folder_Ref.py
      Schema__Vault_App__Manifest.py
      Schema__Manifest__Signature.py
      Schema__VaultPublish__Register__Request.py
      Schema__VaultPublish__Register__Response.py
      Schema__VaultPublish__Unpublish__Response.py
      Schema__VaultPublish__Status__Response.py
      Schema__VaultPublish__Wake__Request.py
      Schema__VaultPublish__Wake__Response.py
      Schema__VaultPublish__Resolve__Request.py
      Schema__VaultPublish__Resolve__Response.py
      Schema__VaultPublish__List__Response.py
      Schema__VaultPublish__Health__Response.py
      List__Slug.py
      Dict__Manifest__Env.py
    service/
      Slug__Validator.py
      Slug__Resolver.py
      Vault__Fetcher.py
      Manifest__Verifier.py
      Manifest__Interpreter.py
      Instance__Manager.py
      Control_Plane__Client.py
      Publish__Service.py
      reserved/
        Reserved__Slugs.py          # the maintained, versioned reserved-slug set
    fast_api/
      Routes__Vault_Publish.py
    cli/
      Cli__Vault_Publish.py
    waker/
      Waker__Lambda__Adapter.py     # the only edge-specific code
```

`__init__.py` files stay empty (`.claude/CLAUDE.md` #22). Callers import from the
fully-qualified per-class path.

---

## 2. Safe primitives

| Class | Constrains |
|-------|------------|
| `Safe_Str__Slug` | The slug naming rules — 3–40 chars, lowercase / digits / hyphen, no leading/trailing/double hyphen. Construction fails on an invalid value. |
| `Safe_Str__Transfer_Id` | An SG/API Transfer-ID. Charset/length per the SG/Send contract (open question #1). |
| `Safe_Str__Read_Key` | An SG/API read key. Never logged, never surfaced to the browser. |

`Safe_Str__Slug` is the type that makes "the slug rules live in exactly one place"
real — if a value is a `Safe_Str__Slug`, it is already valid.

---

## 3. Enums (no Literals)

| Class | Values (illustrative) |
|-------|-----------------------|
| `Enum__Vault_App__Type` | `static_site`, `vault_js_app` |
| `Enum__Vault_App__Runtime` | the allowlisted runtimes only |
| `Enum__Instance__State` | `stopped`, `pending`, `running`, `stopping`, `unknown` |
| `Enum__Wake__Outcome` | `already_running`, `started`, `warming`, `rejected_unverified`, `rejected_invalid_slug` |

---

## 4. Key schemas

### `Schema__Slug__Billing_Record`

The integrity anchor. The per-slug state that already exists. Fields (illustrative):
`slug : Safe_Str__Slug`, `owner_id`, `signing_public_key_ref`, `created_at`,
`updated_at`. **The schema itself is owned by SG/Send** — this repo consumes it;
open question #2 confirms the shape.

### `Schema__Vault_App__Manifest`

The declarative provisioning manifest. Fields: `app_type : Enum__Vault_App__Type`,
`content_root`, `runtime : Enum__Vault_App__Runtime`, `env : Dict__Manifest__Env`,
`routes`, `health_path`. **There is deliberately no `command` / `script` / `exec`
field** — the absence is the security property (see `06__security`).

### `Schema__Manifest__Signature`

The detached signature over the manifest. `Manifest__Verifier` checks it against
`signing_public_key_ref` from the billing record.

### Request / Response schemas

One pair per FastAPI route (see `03__cli/cli-surface.md`). Every route returns
`.json()` on its `Type_Safe` response schema — no raw dicts.

---

## 5. The reserved-slug set

`Reserved__Slugs` is a maintained, **versioned** set — not a free-form list inline
in `Slug__Validator`. It is logic + data (the maintained list), so it follows the
registry exception in `.claude/CLAUDE.md` #21 (like `STEP_SCHEMAS`): a single
module under `service/reserved/`, not a schema folder. Treat changes to it like
changes to the JS allowlist — they are policy decisions, and policy drift here is
the most common way subdomain features fail.

---

## 6. Testing the schemas (no mocks, no patches)

Per `.claude/CLAUDE.md` testing rules and `library/guides/v3.1.1__testing_guidance.md`:

- `Slug__Validator` — table-driven valid/invalid cases against the naming rules and
  the reserved set.
- `Slug__Resolver` — deterministic-derivation tests; same slug → same
  `(Transfer-ID, read key)`.
- `Manifest__Verifier` — a known-good signed manifest verifies; a tampered one is
  rejected; a manifest signed by the wrong key is rejected.
- `Manifest__Interpreter` — every allowlisted field maps to a bounded operation; an
  unknown field is rejected, never passed through.
- `Instance__Manager`, `Control_Plane__Client`, `Publish__Service` — exercised via
  in-memory composition (`register_..._in_memory()`-style), asserting on the
  contract schemas and on persisted/observable state, not on implementation
  details.
