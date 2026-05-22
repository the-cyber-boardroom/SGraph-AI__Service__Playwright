---
title: "B2 — SG/Role tokens + privilege resolver (over aws/creds)"
file: 02__B2-sg-role-and-privileges.md
author: Architect (Claude)
date: 2026-05-21 (UTC hour 15)
repo: SGraph-AI__Service__Playwright @ claude/review-tui-cli-commits-S3xCM (v0.2.36 line)
status: PLAN — pure (3.11). Extends the existing aws/creds machinery; no new auth system.
parent: 00__plans-index.md
---

# B2 — SG/Role tokens + privilege resolver

**Goal.** Give the contract its capability layer: **SG/Role tokens** (`{api}:{capability}[:{resource}]`,
time-bounded, delegable — decision #2) and a **privilege resolver** that maps a scope **down**
to its backing grant and checks the active identity has it (decision #1: presence/role check +
print-policy on miss). This is the layer the execution center (B3) calls before dispatch.

**The key reuse.** `aws/creds` already implements scoped role-assumption with TTL + audit. SG/Role
does **not** re-implement that — an SG/Role capability that touches AWS **maps to a
`Schema__Creds__Scope`** (role ARN + max TTL) and is satisfied by the existing
`Creds__STS__Client` + `Creds__Audit__Log`. Non-AWS privileges (env / vault / network) are a
simple presence check.

---

## Files to create

```
tui/tool_api/
  enums/
    Enum__Tui_Api__Priv_Kind.py        SG_ROLE · IAM_POLICY · IAM_ROLE · VAULT_KEY · ENV · NETWORK · OTHER
  schemas/
    Schema__Tui_Api__Privilege.py      kind: Enum__…__Priv_Kind · ref: str · note: str
    Schema__Tui_Api__Grant.py          scope: Schema__Tui_Api__Scope · expires_at: float = 0 · derived_from: str = ''
    List__Tui_Api__Privilege.py · List__Tui_Api__Grant.py
  service/
    Tui_Api__Token.py                  parse/format '{api}:{cap}[:{res}]'  <-> Schema__Tui_Api__Grant
    Tui_Api__Privilege__Resolver.py    holds(grant) / missing(privilege) -> hint ; AWS path delegates to aws/creds
    Tui_Api__Grant__Store.py           optional persistence (mirrors Creds__Scope__Catalogue JSON-at-~/.sg)
  tests/
    test_Tui_Api__Token.py
    test_Tui_Api__Privilege__Resolver.py
```

The contract additions (extend the B1 schemas — additive, non-breaking):
- `Schema__Tui_Api__Action` gains `privileges: List__Tui_Api__Privilege` (per-action override) and
  keeps `scope` from B1.
- `Schema__Tui_Api__Manifest` gains `privileges: List__Tui_Api__Privilege` (API-level baseline) and
  `scopes: List__Tui_Api__Scope`.

---

## Key shapes

```python
# Schema__Tui_Api__Grant — a scope granted to an identity, time-bounded (decision #2)
class Schema__Tui_Api__Grant(Type_Safe):
    scope        : Schema__Tui_Api__Scope
    expires_at   : float = 0              # 0 = session lifetime; else epoch (TTL via Creds__TTL__Parser)
    derived_from : str   = ''             # parent token id, for sub-agent delegation (decision #2)

# Tui_Api__Token — string <-> grant (the SG/Role wire form)
class Tui_Api__Token(Type_Safe):
    def parse(self, s: str) -> Schema__Tui_Api__Grant      # 'sg-aws.s3:read[:b/*]' -> Grant
    def format(self, grant) -> str
    def is_expired(self, grant, now: float) -> bool        # expires_at and now > expires_at
    def covers(self, grant, scope) -> bool                 # api match + (cap=='*' or cap match) + resource glob

# Tui_Api__Privilege__Resolver — does the active identity hold what an action needs?
class Tui_Api__Privilege__Resolver(Type_Safe):
    creds_catalogue : Creds__Scope__Catalogue = None      # reuse aws/creds
    ttl_parser      : Creds__TTL__Parser      = None
    def grants_cover(self, grants, action) -> bool:
        # the caller must hold a grant whose scope covers the action.scope, unexpired
        ...
    def missing(self, privilege: Schema__Tui_Api__Privilege) -> str:
        # presence/role check; on miss, return an actionable hint:
        #   SG_ROLE / IAM_ROLE -> 'assume scope <name> (role <arn>) — sg aws creds assume <name>'
        #   IAM_POLICY         -> the minimal policy JSON to attach (print-policy)
        #   ENV / VAULT_KEY    -> 'set <ref>' / 'unlock vault key <ref>'
        # '' means satisfied
        ...
```

### Mapping SG/Role → aws/creds (the reconciliation, decision #1)
- An action whose backing privilege is `kind=SG_ROLE` / `IAM_ROLE` carries `ref = <creds scope name>`.
- `missing()` looks the scope up via `Creds__Scope__Catalogue.scope_get(ref)`; if absent → hint to add it
  (`sg aws creds scope add …`); if present but not assumed → hint to assume
  (`sg aws creds assume <ref>`). The execution center (B3) does **not** silently assume — it refuses
  with the hint, matching the existing `_render_bedrock_client_error` actionable-error style.
- Time-bounds reuse `Creds__TTL__Parser.parse(scope.max_ttl)`; the grant's `expires_at` is
  `assumed_at + parse(max_ttl)`; `Schema__Creds__Assumption.expires_at` is the source of truth when an
  assumption exists.
- **No boto3 here** — actual STS assumption stays in `Creds__STS__Client` (osbot-aws); the resolver only
  reads the catalogue + checks presence (pure, testable without AWS).

---

## Tests (no mocks, 3.11)

- `test_Tui_Api__Token` — round-trip parse/format for `sg-aws.s3:read`, `sg-edge.slugs:write:alice`,
  whole-API `sg-aws.s3:*`; `is_expired` honours `expires_at`; `covers` matches `*` capability and
  resource globs; rejects malformed strings.
- `test_Tui_Api__Privilege__Resolver`:
  - `grants_cover` true when a granting scope covers the action scope (incl. `:*`), false when over-tier /
    expired / wrong resource.
  - `missing()` with a `Creds__Scope__Catalogue` pointed at a temp JSON (the catalogue already supports
    `catalogue_path` for tests): scope present → `''`; scope absent → a hint naming `sg aws creds scope add`.
  - `IAM_POLICY` miss returns parseable minimal-policy JSON.

---

## Acceptance (B2 done-when)

1. An SG/Role token round-trips through `Tui_Api__Token`; whole-API `{api}:*` grants work (decision #3).
2. The resolver answers "does this identity hold the scope for this action?" without touching AWS in tests.
3. On a miss, the resolver returns an **actionable hint** (the minimal policy / the `sg aws creds` command) — never a silent pass.
4. Time-bounds are honoured via `Creds__TTL__Parser`; an expired grant does not cover.
5. The AWS backing path delegates to `aws/creds` (catalogue + STS client) — no new credential store, no boto3 in the resolver.

## Effort / risk

- **Effort:** ~1 day. The creds catalogue/TTL/audit exist; B2 is the thin capability layer + mapping + tests.
- **Risk — scope semantics drift** (what `read` vs `list_objects` vs `*` mean). Mitigate: define the
  capability vocabulary in the manifest (each action declares its `scope.capability`); `covers()` is the
  only place semantics live; document in SKILL-api.
- **Open (defer to decision #2 detail):** whether SG/Role grants persist across sessions
  (`Tui_Api__Grant__Store`, mirroring the creds catalogue) or stay in-session. v1 default: in-session;
  the store is stubbed but unused until a workflow needs durable grants.

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
