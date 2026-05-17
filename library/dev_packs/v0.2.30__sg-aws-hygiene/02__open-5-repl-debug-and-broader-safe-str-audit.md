---
title: "Open-5 — REPL `--debug` hoist + broader Safe_Str default-regex audit"
file: 02__open-5-repl-debug-and-broader-safe-str-audit.md
author: Architect (Claude — Opus 4.7)
date: 2026-05-17
parent_pack: library/dev_packs/v0.2.30__sg-aws-hygiene/README.md
status: PROPOSED — two small follow-ups discovered after Open-4 Part B landed
size: S — ~150 prod LOC + ~80 test LOC, ~1 day net
trigger: |
  User reported (2026-05-17, after de95ba60 + bf90192f + 35e4026e landed on dev):

    sg/aws/credentials> add iam-admin AKIA<EXAMPLE> "<secret-with-/-and-+>" ...
    [ok] role 'iam-admin' added/updated
    sg/aws/credentials> test iam-admin
    STS call failed: ... SignatureDoesNotMatch ...

    sg/aws/credentials> test --debug iam-admin
    Error: No such option: --debug

  Two distinct issues. The first is most likely user-side (stale `sg` binary
  before de95ba60 landed); the second is real — the REPL doesn't hoist
  `--debug` to the level where the top-level callback expects it.
---

# Open-5 — REPL `--debug` hoist + broader Safe_Str audit

Two small follow-ups discovered after Open-4 Part B (`35e4026e` — wired `--debug` at `sg` and `sg aws` top levels) landed on dev. Neither blocks the existing Open-1/2/3/4 work; both close real UX gaps.

---

## Part 1 — REPL `--debug` hoist

### The problem

After `35e4026e`, this works:

```bash
$ sg --debug aws credentials test iam-admin     # ✓ top-level callback fires; tracebacks shown
$ sg aws --debug credentials test iam-admin     # ✓ aws-level callback fires
```

But inside the REPL, the user-natural form fails:

```
sg/aws/credentials> test --debug iam-admin
Usage: sg aws credentials test [OPTIONS] [ROLE]
Try 'sg aws credentials test --help' for help.
╭─ Error ──────────────────────────────────────────────────────────╮
│ No such option: --debug                                          │
╰──────────────────────────────────────────────────────────────────╯
```

### Why

The REPL's `_resolve()` function in `sg_compute/cli/Cli__SG__Repl.py` stops at the first `-`-prefixed token and treats the rest as trailing args:

```python
for i, word in enumerate(words):
    if word.startswith('-') or not _is_group(sg_app, current):
        return current, list(words[i:])
```

So `test --debug iam-admin` from the REPL's `aws/credentials` path becomes:

```
sg_app(['aws', 'credentials', 'test', '--debug', 'iam-admin'])
```

Click then parses `--debug` at the `test` verb level — but `--debug` is a callback option on `sg` (top) and `sg aws` (subapp), NOT on the `test` verb. No such option.

### Fix shapes (pick one)

**(A) Hoist `--debug` to the front of the assembled args** — simplest, preserves the user-natural typing:

```python
# Cli__SG__Repl.py — in the run loop after `parts = line.split()`
debug_flag = any(p in ('--debug', '-D') for p in parts)
if debug_flag:
    parts = [p for p in parts if p not in ('--debug', '-D')]
# ... existing _resolve / _invoke ...
full_args = (['--debug'] if debug_flag else []) + repl.path + trailing_args
_invoke(sg_app, full_args)
```

Result: `test --debug iam-admin` becomes `sg --debug aws credentials test iam-admin` under the hood.

**(B) Session-level pseudo-command `debug on` / `debug off`** — REPL-natural, persists across commands:

```python
# Cli__SG__Repl.py — in the run loop, before _resolve
if cmd == 'debug' and len(parts) == 2 and parts[1] in ('on', 'off'):
    from sg_compute.cli.base.Spec__CLI__Errors import set_debug
    set_debug(parts[1] == 'on')
    console.print(f'  [dim]debug {parts[1]}[/dim]')
    continue
```

Result: user types `debug on` once at the prompt, then every subsequent error in that REPL session shows the traceback until they type `debug off` or exit.

### Recommendation

**Ship both.** They're complementary, ~30 LOC combined, and cover the two interaction modes naturally:
- `--debug` inline (option A) for one-off debugging on a specific command
- `debug on/off` (option B) for "I'm investigating; show me everything until I say otherwise"

The implementation cost is the same as either alone (the hard part is recognising `--debug` in the parser; once that's done, both flows fall out).

### Tests

```python
# tests/unit/sg_compute/cli/test_Cli__SG__Repl__debug.py

def test__debug_flag_is_hoisted_to_top_when_typed_at_verb_position():
    invocations = []
    def fake_sg_app(args, **_):
        invocations.append(list(args))
    parse_and_invoke(fake_sg_app, base_path=['aws', 'credentials'],
                                  line='test --debug iam-admin')
    assert invocations[0][0] == '--debug'      # hoisted to top

def test__debug_on_pseudo_command_sets_global_debug():
    from sg_compute.cli.base.Spec__CLI__Errors import set_debug, _DEBUG
    set_debug(False)
    handle_repl_line('debug on')
    from sg_compute.cli.base.Spec__CLI__Errors import _DEBUG as _D2
    assert _D2 is True
    handle_repl_line('debug off')
    from sg_compute.cli.base.Spec__CLI__Errors import _DEBUG as _D3
    assert _D3 is False
```

Plus an integration smoke that the REPL prompt actually accepts `test --debug iam-admin` and dispatches it without "No such option".

### Effort

~30 prod LOC + ~40 test LOC, ~1 hour.

---

## Part 2 — Broader Safe_Str default-regex audit

### The problem

The 2026-05-17 SignatureDoesNotMatch bug (`Safe_Str__AWS__Secret__Key` silently mangling `/+=` because it inherited the Safe_Str default regex) was fixed surgically in `de95ba60`. A follow-up audit on this branch (`ed3fffbe`) found one more case in `Safe_Str__Secret__Value` and fixed it.

**Both fixes were scoped to credential-bearing primitives.** A wider sweep across `sg_compute/`, `sg_compute_specs/`, and the v0.2.29 aws surfaces turns up **three more mangling primitives** that aren't credentials but corrupt real-world inputs anyway. None of them is a security boundary — but each one silently corrupts data the user expects to be preserved verbatim.

### The three latent bugs

```python
# Confirmed via live round-trip with realistic inputs:

# 1. sg_compute/primitives/Safe_Str__Log__Content.py — 1 MB container log capture
input:  'INFO: started\nERROR: failed at line 42 (timeout: 30s)\n'
output: 'INFO__started_ERROR__failed_at_line_42__timeout__30s__'
        ← colons, parens, newlines all → _

# 2. sg_compute/primitives/Safe_Str__Message.py — 512-char status / error message
input:  'CloudFront E123ABC: status=disabled / 4xx-rate=12%'
output: 'CloudFront_E123ABC__status_disabled___4xx_rate_12_'
        ← every : = / % → _

# 3. sgraph_ai_service_playwright__cli/aws/billing/primitives/Safe_Str__Aws_Usage_Type.py — Cost Explorer usage strings
input:  'EU-BoxUsage:t3.micro'   (what Cost Explorer actually returns)
output: 'EU_BoxUsage_t3_micro'
        ← the colon between BoxUsage and t3.micro → _, the dot → _
```

All three have `strict_validation = False` in two cases and no flag in the third — but the regex strips characters regardless of `strict_validation`. The header comments on Log__Content and Message both say "No regex — log output can contain any printable character" — they intended permissive but didn't make it explicit.

### Out of scope for Open-5 (already verified safe)

Three other candidates that initially looked suspicious but actually inherit from osbot-utils' `Safe_Str__Text` / `Safe_Str__Text__Dangerous` which have their own permissive regex:

```
sgraph_ai_service_playwright__cli/firefox/primitives/Safe_Str__Health__Detail.py             (extends Safe_Str__Text)
sg_compute_specs/playwright/core/schemas/primitives/text/Safe_Str__Page__Content.py          (extends Safe_Str__Text__Dangerous)
sg_compute_specs/playwright/core/schemas/primitives/text/Safe_Str__Artefact__Inline.py       (extends Safe_Str__Text__Dangerous)
```

These are safe — the parent class supplies a permissive regex. The audit confirmed `Safe_Str__Health__Detail('CPU: 95%')` round-trips correctly.

### Fix shape

For Log__Content and Message — the intent was permissive ("any printable character"):

```python
import re

from osbot_utils.type_safe.primitives.core.Safe_Str                          import Safe_Str
from osbot_utils.type_safe.primitives.core.enums.Enum__Safe_Str__Regex_Mode  import Enum__Safe_Str__Regex_Mode


class Safe_Str__Log__Content(Safe_Str):
    max_length      = 1048576
    regex           = re.compile(r'[^\x20-\x7E\n\r\t]')   # printable ASCII + common whitespace; matches Safe_Str__Secret__Value
    regex_mode      = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty     = True
    strict_validation = False                              # keep the existing flag
```

Same shape for `Safe_Str__Message` (smaller max_length).

For `Safe_Str__Aws_Usage_Type` — AWS usage types contain `:`, `.`, `-`, plus alphanumerics. The base AWS resource-string alphabet works:

```python
class Safe_Str__Aws_Usage_Type(Safe_Str):
    max_length  = 256
    regex       = re.compile(r'[^A-Za-z0-9:\-_./]')
    regex_mode  = Enum__Safe_Str__Regex_Mode.REPLACE
    allow_empty = True
```

### Tests

One round-trip test per primitive, modelled on `test_Safe_Str__Secret__Value.py`:

```python
# tests/unit/sg_compute/primitives/test_Safe_Str__Log__Content.py

class test_Safe_Str__Log__Content(TestCase):
    def test__multiline_log_with_special_chars_round_trips(self):
        log = 'INFO: started\nERROR: failed at line 42 (timeout: 30s)\n'
        assert str(Safe_Str__Log__Content(log)) == log

    def test__binary_garbage_scrubbed(self):
        assert str(Safe_Str__Log__Content('hello\x00\x01world')) == 'hello__world'

# tests/unit/sg_compute/primitives/test_Safe_Str__Message.py

class test_Safe_Str__Message(TestCase):
    def test__status_message_with_special_chars_round_trips(self):
        msg = 'CloudFront E123ABC: status=disabled / 4xx-rate=12%'
        assert str(Safe_Str__Message(msg)) == msg

# tests/unit/sgraph_ai_service_playwright__cli/aws/billing/primitives/test_Safe_Str__Aws_Usage_Type.py

class test_Safe_Str__Aws_Usage_Type(TestCase):
    def test__cost_explorer_usage_type_round_trips(self):
        usage = 'EU-BoxUsage:t3.micro'
        assert str(Safe_Str__Aws_Usage_Type(usage)) == usage

    def test__other_realistic_shapes(self):
        for raw in ['DataTransfer-Out-Bytes', 'Requests-Tier1', 'EUW2-BoxUsage:t4g.nano']:
            assert str(Safe_Str__Aws_Usage_Type(raw)) == raw
```

### Effort

~30 prod LOC + ~40 test LOC, ~1 hour.

---

## Note on the user's lingering `SignatureDoesNotMatch` (2026-05-17)

The fix at `de95ba60` (`Safe_Str__AWS__Secret__Key` regex) is on dev as of `36e88a1f` (merge commit). End-to-end verification on this branch with a realistic 40-char base64 secret confirms the fix works:

```
input  (40): wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY     # AWS docs example shape (chars: / + base64)
output (40): wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
match: True
```

The user's lingering `test iam-admin` failure is **almost certainly a stale `sg` binary** — the installed entry point still references the pre-fix module. Verification recipe for the user:

```bash
python3 -c "
import sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__AWS__Secret__Key as m
import inspect
src = inspect.getsource(m)
print('FIXED' if 'A-Za-z0-9/+=' in src else 'OLD BINARY — `git pull origin dev && poetry install`')
"
```

If `FIXED`, but `sg aws credentials test iam-admin` still fails, then:
- The stored secret may actually contain characters outside the base64 alphabet (unusual for AWS but possible if a paste introduced unicode spaces, soft hyphens, etc.) — verify with `sg credentials show iam-admin` (which prints the access key prefix) and then check the keychain bytes directly via `security find-generic-password -s sg.aws.iam-admin -a secret_key -w` on macOS.
- Or the role's IAM permissions genuinely deny `sts:GetCallerIdentity` — but that produces `AccessDenied`, not `SignatureDoesNotMatch`, so this is unlikely.

**Not in scope of Open-5** to fix — the underlying primitive bug is closed. This section exists so the next Sonnet doesn't re-investigate the same trail.

---

## Sequencing

Both parts of Open-5 are independent of each other and of Open-1/2/3/4. Either can ship as a one-commit PR; total combined effort is ~2 hours.

**Suggested order:**
1. Part 1 (REPL `--debug`) first — directly improves debuggability of every other commit
2. Part 2 (Safe_Str audit) second — preventive fix; pays back the next time a log line / message / usage type contains an unexpected character

Or batch both into one PR titled `fix(v0.2.30/open-5): REPL --debug hoist + Safe_Str audit of 3 latent primitives`.

---

## Acceptance

```bash
# Part 1 — REPL --debug
sg repl
> aws credentials test iam-admin --debug         # option A — hoist
  (traceback shown on error)
> debug on                                        # option B — session toggle
> aws credentials test iam-admin
  (traceback shown)
> debug off
> aws credentials test iam-admin
  (clean error only)
> exit

# Part 2 — Safe_Str audit
pytest tests/unit/sg_compute/primitives/test_Safe_Str__Log__Content.py -v
pytest tests/unit/sg_compute/primitives/test_Safe_Str__Message.py -v
pytest tests/unit/sgraph_ai_service_playwright__cli/aws/billing/primitives/test_Safe_Str__Aws_Usage_Type.py -v
# All round-trip tests pass

# Repo-wide invariant: no Safe_Str primitive (outside re-export shims) lacks an explicit regex
find sgraph_ai_service_playwright__cli sg_compute sg_compute_specs -name "Safe_Str*.py" \
  -not -name "__init__.py" -not -path "*/__pycache__/*" -not -path "*/_archive/*" \
  | while read f; do
      has_regex=$(grep -c "^\s*regex\s*=" "$f")
      is_shim=$(grep -c "noqa: F401\|re-export shim" "$f")
      inherits_text=$(grep -c "from .*Safe_Str__Text" "$f")
      if [ "$has_regex" = "0" ] && [ "$is_shim" = "0" ] && [ "$inherits_text" = "0" ]; then
        echo "MISSING: $f"
      fi
    done
# Should print nothing
```

---

## Commit + PR template

```
fix(v0.2.30/open-5): REPL --debug hoist + Safe_Str audit (3 latent primitives)

Part 1 — REPL --debug hoist
  When the user types `<verb> --debug <args>` inside `sg repl`, the REPL
  now hoists --debug to the top of the assembled command line so the
  top-level @app.callback() (wired in 35e4026e) fires. Also adds a
  session-level `debug on` / `debug off` pseudo-command for persistent
  toggling.

Part 2 — Safe_Str default-regex audit
  Three primitives outside the credentials surface were silently
  inheriting the Safe_Str default regex and mangling real-world inputs:
    - sg_compute/primitives/Safe_Str__Log__Content      (container logs)
    - sg_compute/primitives/Safe_Str__Message           (status messages)
    - aws/billing/primitives/Safe_Str__Aws_Usage_Type   ('EU-BoxUsage:t3.micro' → 'EU_BoxUsage_t3_micro')
  Same fix shape as de95ba60 + ed3fffbe — explicit regex matching the
  intended alphabet. Round-trip tests pin the alphabet for each.

Combined: ~60 prod LOC + ~80 test LOC.
```

---

## Pointer back

- Parent pack: [`README.md`](README.md) — Open-1 / Open-2 / Open-3 / Open-4
- Original SignatureDoesNotMatch fix: commit `de95ba60` (`Safe_Str__AWS__Secret__Key`)
- Credential audit follow-up: commit `ed3fffbe` (`Safe_Str__Secret__Value`)
- Open-4 Part B (the `--debug` callbacks that this hoist exposes): commit `35e4026e`
- REPL impl: `sg_compute/cli/Cli__SG__Repl.py` (`_resolve` at lines 60-79, run loop at lines 140-175)
- Debug toggle setter: `sg_compute/cli/base/Spec__CLI__Errors.py` (`set_debug()`)
