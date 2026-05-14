# CLI and API Surface

`vault-publish` exposes the same operations through three surfaces — the `sg vp`
CLI, the FastAPI routes, and (for the wake path) the waker Lambda. All three are
thin callers of `Publish__Service`.

> **Note on `sgit publish`.** The upstream brief's `sgit publish --slug ...`
> command lives in the **SG/Send** repo, not here. It is a *client* of the
> `vault-publish` API. This repo provides the API + the `sg vp` admin/operator
> CLI; SG/Send's `sgit` calls into it.

---

## 1. The `sg vp` verb tree

Built with the repo's `Spec__CLI__Builder` shape — same auto-help, same
`--dry-run`, same rendered-table output conventions as `sg lc`.

| Command | What it does | Backing service call |
|---------|--------------|----------------------|
| `sg vp register --slug <name> --vault <transfer-id>` | Validate the slug, create/confirm the billing record + owner binding + signing-key reference. Does not start anything. | `Publish__Service.register` |
| `sg vp unpublish --slug <name>` | Remove the slug association. The live URL stops resolving to a vault. | `Publish__Service.unpublish` |
| `sg vp status --slug <name>` | Show slug → vault derivation, instance state, last wake, idle-timer state. | `Publish__Service.status` |
| `sg vp wake --slug <name>` | Manually run the wake sequence (operator/debug use). | `Publish__Service.wake` |
| `sg vp resolve --slug <name>` | Show the derived `(Transfer-ID, read key)` and the fetched manifest summary — does not provision. Debug aid. | `Slug__Resolver` + `Vault__Fetcher` |
| `sg vp list` | List registered slugs for the caller (or all, for an operator). | `Publish__Service.list` |
| `sg vp health` | Check the four infra layers: DNS, cert, distribution, waker Lambda. | `Publish__Service.health` |

`--slug` values are validated by `Slug__Validator` before any other work — the
same validation the API uses (one rule set, one class).

---

## 2. FastAPI routes

Owned by a `Routes__Vault_Publish` class. Pure delegation — no logic in the route.
Every route returns `.json()` on a `Type_Safe` response schema.

| Method + path | Purpose | Request → Response schema |
|---------------|---------|---------------------------|
| `POST /vault-publish/register` | Register / validate a slug; create the billing record. | `Schema__VaultPublish__Register__Request` → `__Response` |
| `DELETE /vault-publish/unpublish/{slug}` | Remove the slug association. | `{slug}` → `Schema__VaultPublish__Unpublish__Response` |
| `GET /vault-publish/status/{slug}` | Slug derivation + instance state. | `{slug}` → `Schema__VaultPublish__Status__Response` |
| `POST /vault-publish/wake` | Run the wake sequence for a slug. **This is the route the waker Lambda calls.** | `Schema__VaultPublish__Wake__Request` → `__Response` |
| `POST /vault-publish/resolve` | Derive `(Transfer-ID, read key)` + summarise the manifest. No side effects. | `Schema__VaultPublish__Resolve__Request` → `__Response` |
| `GET /vault-publish/list` | List registered slugs. | — → `Schema__VaultPublish__List__Response` |
| `GET /vault-publish/health` | Infra-layer health. | — → `Schema__VaultPublish__Health__Response` |

---

## 3. The waker Lambda's surface

The waker Lambda runs this **same FastAPI app**. CloudFront (Phase 2a) sends every
request to the Lambda Function URL; the edge-translation layer maps the inbound
request to `POST /vault-publish/wake` (cold) or proxies to the live instance
(warm). No new routes — the Lambda is a *caller*, not a new surface.

---

## 4. Slug naming rules

Enforced by `Slug__Validator`, expressed as `Safe_Str__Slug` plus the reserved /
profanity lists. The rules (from the upstream brief, unchanged):

- 3–40 characters
- lowercase letters, digits, hyphens only
- cannot start or end with a hyphen
- no double hyphens
- reserved slugs blocked: `www`, `api`, `admin`, `docs`, `app`, `mail`, and a
  maintained list of common service names
- basic profanity filter
- trademark-sensitive names reserved for verified claims

The reserved list is **not** a free-form list in code — it is a maintained,
versioned set (see `07__schemas`). Policy drift on this list is the most common way
subdomain features go wrong; treat it like the JS allowlist boundary.

Invalid slugs are rejected with a clear, specific error — "slug must not contain
double hyphens", not "invalid slug".
