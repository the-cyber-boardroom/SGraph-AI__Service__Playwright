---
title: "01 — Implementation review (Phase A + B1)"
file: 01__implementation-review.md
author: Claude (Architect)
date: 2026-05-18 (UTC hour 11)
parent: README.md
---

# 01 — Implementation review

What landed in commit `385f78b` after the v0.2.29 setup-architecture
brief. Tests pass (130/130 in `sg_compute_specs/vault_publish/`),
the new `sg vault-publish setup iam …` verbs work, and bootstrap is
now idempotent. But there are correctness issues worth fixing before
declaring drift detection "done".

---

## What works

- **`Lambda__AWS__Client.ensure_function_url`** — check-then-create,
  no more `ResourceConflictException` on re-runs.
- **`CloudFront__AWS__Client.ensure_distribution`** — find by alias
  before creating. Fixes the `CNAMEAlreadyExists` we hadn't hit yet
  but would have.
- **`Setup__IAM` shape** — five verbs (check / status / create /
  update / delete), mutation-gated via env vars, in-memory tests for
  all paths.
- **Sub-package layout** — `sg_compute_specs/vault_publish/setup/`
  with `schemas/`, `service/`, `collections/`, `cli/`, `tests/`.
  Clean separation; sets the pattern for B2 (Lambda + URL) and B3
  (CF + ACM + DNS).
- **CLI integration** — `sg vault-publish setup` mounts cleanly under
  the existing `Cli__Vault_Publish` typer app.

---

## Real bugs / weak spots

### 1. `_find_inline_policy` ignores its `policy_name` argument

```python
def _find_inline_policy(role, policy_name: str):
    for p in list(role.inline_policies):
        return p                                  # we own exactly one inline policy
    return None
```

The function takes `policy_name` and silently ignores it — returns
the first inline policy regardless of name. Today this works because
we only ever attach one inline policy (`WakerExecutionPolicy`), but
the function is lying.

**Root cause**: `Schema__IAM__Policy` (the schema returned by
`IAM__AWS__Client._parse_policy_doc`) has no `name` field. The IAM
client knows the policy name when it loads it, but throws the name
away before returning the parsed policy.

**Fix options:**
- (cheap) drop the `policy_name` parameter from `_find_inline_policy`
  and rename to `_first_inline_policy(role)`, with a comment that
  asserts the role has exactly one.
- (better) add `name: str = ''` to `Schema__IAM__Policy` and have
  `_load_inline_policies` populate it. Lets us reliably look up by
  name, future-proofs for roles with multiple inline policies.

**Recommendation:** the second option. ~10 lines, no caller changes,
removes the silent lie.

---

### 2. Drift detection is action-level only

```python
expected_actions = _collect_actions(expected_policy)
live_actions     = _collect_actions(live_policy)
missing_actions  = expected_actions - live_actions
extra_actions    = live_actions - expected_actions
```

I flatten every statement into a set of action strings. That misses
the three classes of drift that actually matter for security:

#### Resource-scope drift
Template:  `arn:aws:ssm:*:*:parameter/sg-compute/vault-publish/*`
Live:      `*`

Same actions (`ssm:GetParameter`). Different resource. Currently
**reported as OK**. This is the difference between "read parameters
in our prefix" and "read every secret in the account".

#### Condition drift
Template:  `ec2:StartInstances` with `StringEquals: {aws:ResourceTag/StackType: vault-app}`
Live:      `ec2:StartInstances` with no condition

Same action. The condition is the *only* thing preventing the Lambda
from starting any EC2 instance in the account. Currently **reported
as OK**.

#### Effect flip
Template:  `Effect: Allow` on `ssm:GetParameter`
Live:      `Effect: Deny` on `ssm:GetParameter`

Same action set. Lambda now can't read SSM at all. Currently
**reported as OK** because both have the same actions.

**The brief explicitly asked for `missing_stmts` and `extra_stmts`
(statement-level diff), not actions.** I simplified — needs walking
back.

**Fix:** compare statements by a canonical key (`(effect, sorted(actions), sorted(resources), condition_json)`):
```python
def _stmt_key(stmt):
    return (
        stmt.effect,
        tuple(sorted(str(a) for a in stmt.actions)),
        tuple(sorted(str(r) for r in stmt.resources)),
        stmt.condition_json or '',
    )

expected_keys = {_stmt_key(s) for s in expected_policy.statements}
live_keys     = {_stmt_key(s) for s in live_policy.statements}
missing       = expected_keys - live_keys
extra         = live_keys - expected_keys
```

Schema fields `missing_actions` / `extra_actions` should become
`missing_statements` / `extra_statements` with stringified summaries.
Touches the schema + report rendering — ~30 lines.

---

### 3. Trust policy is never compared

`Setup__IAM.check` reads `role.trust_policy` indirectly through
`get_role` but never compares it to the expected
`{Service: lambda.amazonaws.com}`. If a malicious or buggy console
edit replaces the trust policy with `{Service: ec2.amazonaws.com}`,
the Lambda silently stops being able to assume the role — and our
`check` says OK.

**Fix:** add `trust_policy_ok: bool` to the report, set by:
```python
expected_trust = IAM__Trust_Policy__Builder().build(Enum__IAM__Trust__Service.LAMBDA)
trust_ok       = _trust_principals_match(role.trust_policy, expected_trust)
```

If `trust_ok` is False, state is DRIFT and we emit a CRITICAL issue.
`update()` should also re-`update_assume_role_policy` when this
drifts — but `IAM__AWS__Client` doesn't have that method today, so
we'd need to add it.

---

### 4. Minor cleanliness

- **`create_resp = iam.create_role(req)`** — captured, never used.
  Drop the assignment.
- **`status()` returns `dict`** — every other verb returns a Type_Safe
  schema. Either return `Schema__Setup__IAM__Report` (re-use `check`
  output minus state evaluation) or document that `status` is the
  one read-only verb that's intentionally a dict for pretty-printing.
- **CLI mounting is a side-effecting import** in `Cli__Vault_Publish`:
  ```python
  from sg_compute_specs.vault_publish.setup.cli.Cli__Setup import app as setup_app
  app.add_typer(setup_app, name='setup')
  ```
  Works, but the import-at-module-bottom pattern is unusual. Could be
  moved into a small `_mount_subapps(app)` helper called at the
  bottom for symmetry with how other Typer apps are composed.

---

### 5. Missing test cases

- **Extra-actions drift** — I test the "live policy missing actions"
  case but not "live policy has extra actions". Worth a test even
  with the current action-only diff.
- **Trust policy drift** — once #3 is fixed.
- **`create` when role exists with wrong trust policy** — should
  detect + repair, currently would just no-op-ish via the
  `if role is not None: return self.update()` short-circuit (which
  also doesn't fix trust).
- **CLI smoke test** — `typer.testing.CliRunner` against
  `Cli__Setup.app` for at least `iam check`. Confirms the wiring.

---

## What to do now

A small targeted commit (~50 lines + tests) fixes #1–#4. Then the
shape is ready to use as the template for B2 (Lambda + URL).
Recommend doing this *before* Phase B2 because every B2 area will
copy this pattern — better to copy a clean one.

Suggested sequence:

1. Add `name: str = ''` to `Schema__IAM__Policy`, populate in
   `_load_inline_policies`.
2. Switch `Setup__IAM.check` to statement-level diff using
   `_stmt_key`.
3. Add trust-policy comparison + `IAM__AWS__Client.update_assume_role_policy`.
4. Drop the unused `create_resp` assignment.
5. Decide on `status()` shape (recommend: small dedicated schema
   `Schema__Setup__IAM__Status`).
6. Add the three missing test cases.

Estimated effort: 0.5 day. Should land before B2 starts.
