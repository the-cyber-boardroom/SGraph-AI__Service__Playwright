---
title: "Open-7 — Bedrock alias regional overrides + check verifies default model"
file: 03__open-7-bedrock-alias-regional-overrides.md
author: Architect (Claude — Opus 4.7)
date: 2026-05-17
parent_pack: library/dev_packs/v0.2.30__sg-aws-hygiene/README.md
status: PROPOSED — Bedrock chat default alias fails in EU regions; check verb misses it
size: S — ~100 prod LOC + ~80 test LOC, ~2 hours
trigger: |
  User session 2026-05-17 (after de95ba60 + 826a2780 + Bedrock check landed):

    sg/aws/bedrock> check
      [✓]  sts identity              arn:aws:iam::...:user/SG-Bedrock
      [✓]  region supported          eu-west-2 (Bedrock GA)
      [✓]  list-models perm          bedrock:ListFoundationModels
      [✓]  models in catalogue       51 models
      [✓]  models with access        51 of 51 enabled
      [✓]  claude available          claude: 5, nova: 3, llama: 2
      [✓]  invoke perm               invoke OK — google.gemma-3-4b-it, 10→60 tokens
      [✓]  capture writer            /Users/.../.sg/aws/bedrock writable

    sg/aws/bedrock/chat> claude hi
    ValidationException: The provided model identifier is invalid.

  All 8 preflight checks pass yet the very next command fails. The
  check verifies *some* model can be invoked (it picked the cheapest
  enabled one — Gemma), but never tries the default Claude model the
  user is about to call.
---

# Open-7 — Bedrock alias regional overrides + check verifies default model

## The problem (one paragraph)

`sg aws bedrock check` is currently green-lighting environments where `sg aws bedrock chat claude hi` will immediately fail. Bedrock's bare model IDs (`anthropic.claude-3-5-haiku-20241022-v1:0`) work in `us-east-1` / `us-west-2` but in EU / APAC regions you need a cross-region **inference profile** (`eu.anthropic.claude-...` or an application ARN). The default alias in `Bedrock__Model__Aliases.py` doesn't carry regional awareness for any provider except `claude` `opus-4.7` — so any user in eu-west-2 (or eu-west-1, eu-west-3, eu-central-1, etc.) hits the same trap on their first chat.

Two-part fix: extend the `region_overrides` table to cover **every** alias that has a regional flavour, and make `sg aws bedrock check`'s smoke-test target the **default model for each provider** rather than the first/cheapest enabled model in the catalogue.

---

## Part 1 — Extend `region_overrides` in `Bedrock__Model__Aliases.py`

### Current state (only `opus-4.7` has regional overrides)

```python
'region_overrides': {
    'eu-west-1':    {'opus-4.7': 'eu.anthropic.claude-opus-4-7:0'},
    'eu-west-2':    {'opus-4.7': 'eu.anthropic.claude-opus-4-7:0'},
    'eu-west-3':    {'opus-4.7': 'eu.anthropic.claude-opus-4-7:0'},
    'eu-central-1': {'opus-4.7': 'eu.anthropic.claude-opus-4-7:0'},
    'eu-north-1':   {'opus-4.7': 'eu.anthropic.claude-opus-4-7:0'},
}
```

### What's needed

Every Anthropic Claude alias that the user might pick (`default`, `haiku-3.5`, `haiku-4.5`, `sonnet-3.5`, `sonnet-3.7`, `sonnet-4.6`, `opus-4.7`, …) needs an EU / APAC / US override where the bare ID isn't accepted. Same for Llama and Nova as those move behind inference profiles too.

Recommended approach: introduce **provider-level regional mappings** rather than per-alias entries, since most aliases follow the same `us.` / `eu.` / `apac.` prefix convention:

```python
'region_overrides': {
    # Prefix-based providers — applied to every alias that maps to an `anthropic.*` model
    'anthropic_prefix': {
        'us-east-1':    '',           # bare ID works
        'us-west-2':    '',
        'us-east-2':    'us.',
        'eu-west-1':    'eu.',
        'eu-west-2':    'eu.',
        'eu-west-3':    'eu.',
        'eu-central-1': 'eu.',
        'eu-north-1':   'eu.',
        'ap-southeast-1': 'apac.',
        'ap-southeast-2': 'apac.',
        'ap-northeast-1': 'apac.',
    },
    # Plus the existing per-alias overrides for special cases (left in as escape hatch)
    'eu-west-2': {
        '<alias>': '<explicit-arn-if-not-prefix-rule>',
    },
}
```

`Bedrock__Model__Resolver.resolve()` extends:

1. Resolve the alias to a bare model ID as today
2. Look up provider-level prefix for the resolved region
3. If a prefix exists and the model is in that provider's namespace, prepend the prefix
4. Per-alias overrides still win (escape hatch for non-conforming models)

So `claude default` in `eu-west-2` resolves: `anthropic.claude-3-5-haiku-20241022-v1:0` → `eu.anthropic.claude-3-5-haiku-20241022-v1:0`.

### Caveats

- Not every Bedrock region supports every provider. The check verb (Part 2) catches this empirically.
- Cross-region inference profiles aren't free; Anthropic/Amazon doc the per-region pricing tier. Worth a one-liner note in the alias-table header.
- `nova-*` and `llama-*` regional availability is less documented — when in doubt, leave the bare ID and let Part 2's check surface the failure.

### Effort

- ~60 LOC: extend the dict + small change to `resolve()`
- ~40 LOC tests: round-trip for `claude default` in each EU region, `nova lite` in regions that need it, `opus-4.7` doesn't regress, `default` in us-east-1 still bare
- 1-2 hours

---

## Part 2 — `sg aws bedrock check` verifies the actual default model

### What it does today (the gap that let this slip)

```python
# Bedrock__Preflight.check_invoke_perm — pseudocode
enabled_models = list_foundation_models(...)
cheapest = pick_cheapest(enabled_models)
sts_smoke = invoke(cheapest, prompt='hi', max_tokens=1)
# → reports ✓ because Gemma worked
```

This proves "AT LEAST ONE model can be invoked" but not "the model the user will actually call works". In the user's case, all 51 models reported as enabled, the smoke picked Gemma (3 cents per million tokens — cheapest), Gemma worked, every check passed green. But `sg aws bedrock chat claude hi` then fails with ValidationException because the Claude default alias points at a model ID Bedrock won't serve bare in eu-west-2.

### What it should do

```python
# Per provider in the alias table — claude, nova, llama, openai
for provider in providers_in_use:
    alias = 'default'
    model_id = resolver.resolve(provider, alias, region)         # resolves regional override (Part 1)
    try:
        invoke(model_id, prompt='ping', max_tokens=1)
    except ClientError as exc:
        # Report per-provider FAIL with the rendered hint (the same _render_bedrock_client_error
        # text used by the chat verbs) — actionable, not generic
```

Then check output becomes:

```
$ sg aws bedrock check
  ...
  [✓]  invoke perm                 cheapest probe: gemma-3-4b-it OK (10→60 tokens, $0.000003)
  [✓]  claude default invokable    eu.anthropic.claude-3-5-haiku-... — OK ($0.000004)
  [✗]  nova default invokable      amazon.nova-lite-v1:0 — ValidationException: model id invalid
       → sg aws bedrock setup --open-console (enable Nova access)
       → or `chat nova --model micro` while the default model is unavailable
  [⚠]  llama default invokable     meta.llama3-8b-instruct-v1:0 — skipped (Llama not in your enabled list)
```

Per-provider rows replace the single "invoke perm" row. The cheapest-probe stays as a sanity check but is no longer load-bearing.

### Naming

Keep `check` as the verb. Add an internal helper `_check_provider_default_invokable(provider, region)` that resolves the alias, attempts invocation, returns a `Schema__Bedrock__Check__Result` row (already typed in v0.2.29).

### Cost

Each provider check is ~1-2 tokens of input + 1 output = ~$0.000001-0.000004 per provider per check. With 3-4 providers checked, that's well under $0.0001 per `check` invocation. Negligible. Capped by the existing `Bedrock__Cost__Calculator` cap.

### Effort

- ~30 LOC: new helper + adjust the report rows
- ~30 LOC tests: per-provider check row with an in-memory client that raises ValidationException for one provider only
- 1 hour

---

## Why this didn't surface earlier

The cheapest-model heuristic in `check` made sense when written (universal sanity check; one invoke proves all the plumbing works). But Bedrock model IDs aren't uniformly invokable — some need inference profiles, some are regional, some require explicit model-access approval beyond `enabled = true`. The right gate is the **specific model the user is about to call**, not any model.

In retrospect this is the same flavour of bug as M-1 / Slice B (silently using the wrong shape and reporting success). The fix here is the same shape: make the check observable, specific, and actionable.

---

## Out of scope

- **Inference-profile auto-discovery** — Bedrock has `list_inference_profiles` API. Could auto-detect the right prefix. Defer to v0.3 once we know whether the static prefix table is good enough.
- **Per-alias regional pricing display** — useful but adds API calls. v0.3.
- **Streaming check** (verify `bedrock:InvokeModelWithResponseStream` separately) — incremental; add only if a user hits it.

---

## Acceptance

```bash
# Part 1 — regional default works for Claude
sg credentials switch eu-test-role          # active region = eu-west-2
sg aws bedrock chat claude hi               # → succeeds (resolves to eu.anthropic.claude-... not bare)

# Part 1 — bare still works in us-east-1
sg credentials switch us-test-role          # active region = us-east-1
sg aws bedrock chat claude hi               # → succeeds (bare anthropic.claude-... still served)

# Part 2 — check catches per-provider issues
sg aws bedrock check
# → 4 new rows: claude default invokable, nova default invokable, llama default invokable, openai default invokable
# → ✗ on any provider whose default doesn't work, with actionable hint

# Tests
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/bedrock/service/test_Bedrock__Model__Resolver.py -v
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/bedrock/service/test_Bedrock__Preflight.py -v
```

---

## Commit + PR template

```
fix(v0.2.30/open-7): bedrock alias regional overrides + per-provider check

Part 1 — extend Bedrock__Model__Aliases.region_overrides with provider-
level prefix mappings (eu., apac., us.) so every Claude / Nova / Llama
alias resolves to the regional inference profile when bare model IDs
aren't accepted. The Resolver applies the prefix when the model is in
the provider's namespace; per-alias overrides remain as the escape
hatch.

Part 2 — sg aws bedrock check now smoke-invokes the DEFAULT model for
each provider in use (claude/nova/llama/openai), not just the cheapest
enabled model in the catalogue. Per-provider rows replace the single
"invoke perm" row; failures render the same actionable hint as the
chat verbs.

Estimated effort: ~100 prod LOC + ~80 test LOC, ~2 hours.

Closes Open-7 in library/dev_packs/v0.2.30__sg-aws-hygiene/.
```

---

## Real-world data — eu-west-2 inventory (2026-05-17)

The user shared their actual `list-models` output for eu-west-2. The implementer should match the alias-table updates against this list, **not** against the stale defaults in `Bedrock__Model__Aliases.py`. Key Anthropic models actually available bare in eu-west-2:

```
anthropic.claude-3-haiku-20240307-v1:0
anthropic.claude-3-sonnet-20240229-v1:0
anthropic.claude-3-7-sonnet-20250219-v1:0
anthropic.claude-sonnet-4-6                  (NEW naming — no version suffix, no `:0`)
anthropic.claude-opus-4-6-v1                 (NEW model — 4-6, not 4-7)
```

**NOT available** in eu-west-2 today (alias-table entries that point at these will fail):

```
anthropic.claude-3-5-haiku-20241022-v1:0     ← current `claude default` alias 😱
anthropic.claude-haiku-4-5:0                  ← current `claude haiku-4.5` alias
anthropic.claude-sonnet-4-6:0                 ← current `claude sonnet-4.6` alias (has stale `:0` suffix)
anthropic.claude-opus-4-7:0                   ← current `claude opus-4.7` alias (Opus is at 4-6, not 4-7)
```

So the alias-table refresh has two dimensions: regional inference profile prefixes (the original Open-7 ask) **and** updating the bare model IDs to match what's actually published in 2026. Anthropic moved away from the `<provider>.<model>-<YYYYMMDD>-v1:0` naming for the newer Claude generation; the convention is now `<provider>.<model>-<major>-<minor>` (no date, no `:0`).

Action for the implementer:
1. Hard-update each `claude` alias entry against the real eu-west-2 inventory above
2. Add the regional prefix mechanism (the original Open-7 design — Part 1)
3. Add the per-provider check (Part 2)
4. Cross-check `nova` (`amazon.nova-lite-v1:0`, `amazon.nova-pro-v1:0`, `amazon.nova-micro-v1:0` all confirmed in the inventory)
5. Cross-check `llama` (`meta.llama3-8b-instruct-v1:0`, `meta.llama3-70b-instruct-v1:0` confirmed; `llama3-1` / `llama3-2` / `llama4-scout` / `llama4-maverick` aliases will need verification against the actual list-models output per region)

Other useful providers in the user's inventory worth aliasing while we're there: `google.gemma-*`, `mistral.*`, `openai.gpt-oss-*`, `qwen.*`, `deepseek.*`, `nvidia.nemotron-*`. Currently `sg aws bedrock chat any --provider X` is the only way to reach them. A `--provider gemma` / `--provider mistral` shortcut would be a nice follow-up but is out of scope for Open-7.

---

## Pointer back

- Parent pack: [`README.md`](README.md)
- The bug that triggered this (Bedrock chat ClientError): commit `389c8d95`
- Existing resolver: `sgraph_ai_service_playwright__cli/aws/bedrock/service/Bedrock__Model__Resolver.py`
- Existing alias table: `sgraph_ai_service_playwright__cli/aws/bedrock/service/Bedrock__Model__Aliases.py`
- Existing check verb (Preflight): `sgraph_ai_service_playwright__cli/aws/bedrock/service/Bedrock__Preflight.py`
- Existing error renderer (used by chat verbs already): `Verb__Bedrock__Chat__Helpers._render_bedrock_client_error`
- Open-5 sister doc that established the audit-everything pattern: [`02__open-5-repl-debug-and-broader-safe-str-audit.md`](02__open-5-repl-debug-and-broader-safe-str-audit.md)
