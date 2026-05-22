---
title: "B3 — the execution center (modes, sequencing, mutation gate, audit)"
file: 03__B3-execution-center.md
author: Architect (Claude)
date: 2026-05-21 (UTC hour 15)
repo: SGraph-AI__Service__Playwright @ claude/review-tui-cli-commits-S3xCM (v0.2.36 line)
status: PLAN — pure (3.11). The controlled core every tool call goes through.
parent: 00__plans-index.md
---

# B3 — the execution center

**Goal.** A single `Tui_Api__Execution_Center` that mediates **every** dispatch (whether a
human typed `tui api invoke` or — later — the chat model requested a tool). It validates
params, checks **sequencing/preconditions** (decision #3), enforces **SG/Role** (via B2),
gates **mutations** (dry-run / confirm / `..._ALLOW_MUTATIONS`), records an **audit** entry
with cost, and returns a `Schema__Tui_Api__Result`. After B3, `tui api invoke` routes through
the center instead of calling the provider directly.

---

## Files to create

```
tui/tool_api/
  enums/
    Enum__Tui_Api__Exec_Mode.py        AUTO · CONFIRM · DRY_RUN
    Enum__Tui_Api__Cond_Op.py          EQ · NEQ · IN · NOT_IN · EXISTS · ABSENT
  schemas/
    Schema__Tui_Api__Precondition.py   state_path: str · op: Enum__…__Cond_Op · value: str · note: str
    Schema__Tui_Api__Call.py           action_ref·params(sanitised)·scope_used·mode·result_ok·error·duration_ms·cost_usd·identity·ts
    List__Tui_Api__Precondition.py · List__Tui_Api__Call.py
  service/
    Tui_Api__Precondition__Check.py    evaluate(preconditions, provider.state()) -> (ok, failing_note)
    Tui_Api__Param__Sanitiser.py       mask secret-ish keys (token/secret/key/password) for the audit
    Tui_Api__Execution_Center.py       execute(...) — the pipeline below
  tests/
    test_Tui_Api__Precondition__Check.py
    test_Tui_Api__Execution_Center.py
```

Contract additions (additive): `Schema__Tui_Api__Action` gains
`preconditions: List__Tui_Api__Precondition`, `supports_dry_run: bool`, `est_cost_usd: float`.
`Schema__Tui_Api__Result` gains `dry_run: bool`, `preview: dict`, `cost_usd: float`.
`Tui_Api__Provider` gains `actions_available(grants) -> List[Action]` (filtered by
preconditions + scope) and an optional `dry_run(action, params) -> preview`.

---

## The pipeline

```python
class Tui_Api__Execution_Center(Type_Safe):
    mode       : Enum__Tui_Api__Exec_Mode = AUTO
    registry   : Tui_Api__Registry
    resolver   : Tui_Api__Privilege__Resolver       # B2
    checker    : Tui_Api__Precondition__Check
    sanitiser  : Tui_Api__Param__Sanitiser
    log        : List__Tui_Api__Call                 # ring buffer (getLog() analogue)

    def execute(self, slug, action_name, params, grants,
                on_preview=None, on_confirm=None) -> Schema__Tui_Api__Result:
        provider = self.registry.get(slug)
        action   = provider.action(action_name)
        # 1. params: build the Type_Safe params class -> validates; reject early on TypeError/ValueError
        # 2. sequencing: checker.evaluate(action.preconditions, provider.state()); refuse with note if not
        # 3. SG/Role: resolver.grants_cover(grants, action); else refuse with resolver.missing(...) hint
        # 4. preview: if mode==DRY_RUN OR (tier>=WRITE and not env ..._ALLOW_MUTATIONS):
        #       preview = provider.dry_run(action, params); if DRY_RUN -> return Result(dry_run=True, preview=...)
        # 5. confirm gate: if mode==CONFIRM OR tier in (WRITE,CRUD,DESTRUCTIVE):
        #       if on_confirm and not on_confirm(action, params, preview): return refused Result
        # 6. dispatch: result = provider.dispatch(action_name, params)
        # 7. audit: append Schema__Tui_Api__Call(params=sanitiser.mask(params), scope_used=action.scope,
        #            mode, result_ok=result.ok, duration_ms, cost_usd=result.cost_usd, identity, ts)
        return result
```

Defaults (decision: §10 #1 / brief 2): `AUTO` for READ_ONLY, `CONFIRM` for WRITE/CRUD,
CONFIRM-with-typed-confirm for DESTRUCTIVE. Mutations stay behind the existing
`..._ALLOW_MUTATIONS` env convention used by `sg aws s3`/`cf`.

> **Reuse — do not re-invent the gate.** The mutation gate and confirm already exist:
> `sgraph_ai_service_playwright__cli/aws/_shared/Mutation__Gate.py` → `require_mutation_gate(env_var)`
> (the `..._ALLOW_MUTATIONS` check used by `sg aws s3`/`cf`) and
> `aws/_shared/Aws__Confirm.py` → `confirm_or_abort(message, yes, dry_run)`. Step 4/5 of the
> pipeline call these (the center wires its `on_confirm` callback to `confirm_or_abort`), so the
> TUI API uses the *same* mutation discipline the rest of `sg aws` already enforces.

### Sequencing (decision #3 — flat, no DAG)
```python
class Tui_Api__Precondition__Check(Type_Safe):
    def evaluate(self, preconditions, state: dict) -> tuple:   # (ok: bool, failing_note: str)
        for pc in preconditions:
            actual = self._dig(state, pc.state_path)           # dotted-path lookup, e.g. 'slug.state'
            if not self._op(pc.op, actual, pc.value):
                return (False, pc.note)
        return (True, '')
```
`provider.actions_available(grants)` returns only actions whose preconditions hold **and**
whose scope is covered — so discovery (and later the model's toolConfig) never sees an
out-of-sequence or over-tier action.

---

## Tests (no mocks, 3.11)

- `test_Tui_Api__Precondition__Check` — EQ/IN/EXISTS over a sample `state` dict; failing
  precondition returns its `note`; empty preconditions → ok.
- `test_Tui_Api__Execution_Center`, using the B1 S3 in-memory provider + a tiny mutating fake
  provider:
  - READ_ONLY AUTO: `list_objects` dispatches, returns ok, appends one audit Call with cost.
  - param invalid → refused before dispatch (no audit of a dispatch).
  - SG/Role miss → refused with the resolver hint; no dispatch.
  - WRITE without `ALLOW_MUTATIONS` → returns a **preview** (dry_run), provider's real mutate
    NOT called (assert the fake's store unchanged).
  - WRITE with CONFIRM and `on_confirm` returning False → refused, store unchanged.
  - precondition fail (e.g. terminate requires state==live) → refused with the note.
  - audit: params with a `secret`/`token` key are masked in the Call record.

---

## Acceptance (B3 done-when)

1. Every dispatch goes through `execute()`; nothing reaches a provider's mutate without passing the gate.
2. Out-of-sequence actions are **invisible** to `actions_available` and refused by `execute` with the precondition note.
3. WRITE+ actions preview (dry-run) and require confirm / `ALLOW_MUTATIONS`; nothing mutates silently.
4. SG/Role is enforced (B2); a miss yields the actionable hint.
5. Every call lands in the audit ring buffer with params sanitised + cost attached.
6. `sg <area> tui api invoke` now routes through the center (with `--dry-run` flag honoured).

## Effort / risk

- **Effort:** ~1.5–2 days (the pipeline + sequencing + sanitiser + thorough tests).
- **Risk — confirm/preview UX belongs to the caller.** The center takes `on_preview`/`on_confirm`
  callbacks so the CLI prints + prompts and (later) the Textual layer shows a modal — the center stays
  pure and headless-testable.
- **Risk — `dry_run` not implementable for some providers.** `supports_dry_run=False` actions skip the
  preview and rely on CONFIRM + `ALLOW_MUTATIONS` only; documented per action.

---

This document is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
