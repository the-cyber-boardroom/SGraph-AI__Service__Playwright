# ui — Proposed

PROPOSED — does not exist yet. Items below extend the dashboard surface but are not in code today.

Last updated: 2026-05-17 | Domain: `ui/`
Sources: not-included sections of `_archive/v0.1.31/13,14,15__*.md`.

---

## P-1 · `Routes__OpenSearch__Stack` mount + OpenSearch UI cards

**What:** The OpenSearch route class exists; backend mount is the upstream blocker (see `cli/proposed P-6`). Once mounted, the UI card needs to flip `available=True`.

**Source:** Slice 13/14/15 not-included lists.

## P-2 · `Routes__Prometheus__Stack` mount + Prometheus UI cards

**What:** Same as P-1. Backend mount upstream (`cli/proposed P-7`).

**Source:** Slice 13/14/15 not-included lists.

## P-3 · `Enum__Stack__Type.PROMETHEUS`

**What:** The catalog enum lacks `PROMETHEUS`, blocking UI surfaces that switch on stack type.

**Source:** Slice 14 not-included.

## P-4 · User provisioning page (`api_site/user/`) sg-layout rewrite

**What:** The user page still uses the slice-13 polling layout; the admin page got the sg-layout rewrite in slice 15. Apply the same rewrite to `user/`.

**Source:** Slice 15 not-included.

## P-5 · Dynamic re-add of right-column panels mid-session

**What:** Toggling a right-column panel visible=true at runtime requires a page reload or clicking "Reset Layout" in Settings. Add live re-add via DOM insertion + sg-layout `addPanel`.

**Source:** Slice 15 not-included.

## P-6 · Playwright / pytest end-to-end UI smoke tests

**What:** No end-to-end UI tests today. Add Playwright-driven smokes (this service is the Playwright service, after all).

**Source:** Slice 13/14/15 not-included lists.

## P-7 · Per-instance multi-user session tracking in `sp-cli-active-sessions`

**What:** Today the active-sessions widget shows uptime per stack but does not track multiple concurrent users / sessions on the same stack.

**Source:** Slice 15 not-included.

## P-8 · Auth beyond `X-API-Key` in the UI

**What:** No OAuth, no per-user identity, no RBAC. The UI uses the single shared API key from vault. Cross-references `cli/proposed P-10`.

**Source:** Slice 13/14 not-included.

## P-9 · Region filtering passed through uniformly

**What:** `/catalog/stacks?region=...` only forwards `region` to VNC/Linux/Docker; Elastic uses its own `resolve_region`. UI surfaces are affected.

**Source:** Slice 14 not-included.
