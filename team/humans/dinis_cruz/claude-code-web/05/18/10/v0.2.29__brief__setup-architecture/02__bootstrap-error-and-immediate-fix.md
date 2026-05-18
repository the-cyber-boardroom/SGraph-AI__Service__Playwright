---
title: "02 — Bootstrap error & immediate fix"
file: 02__bootstrap-error-and-immediate-fix.md
author: Claude (Architect)
date: 2026-05-18 (UTC hour 10)
parent: README.md
---

# 02 — Bootstrap error & immediate fix

## The error in full

```
sg vault-publish bootstrap
  Bootstrap vault-publish for zone 'aws.sg-labs.app'? [Y/n]:
  →  Bootstrapping vault-publish for aws.sg-labs.app…

ResourceConflictException: An error occurred (ResourceConflictException) when
calling the CreateFunctionUrlConfig operation: Failed to create function url
config for [functionArn = arn:aws:lambda:eu-west-2:745506449035:function:
sg-compute-vault-publish-waker]. Error message: FunctionUrlConfig exists for
this Lambda function
```

## Root cause

`Vault_Publish__Service.bootstrap()` calls
`self._lambda_client().create_function_url(WAKER_LAMBDA_NAME)` unconditionally.

`Lambda__AWS__Client.create_function_url` translates straight to
`boto3.lambda.create_function_url_config`, which AWS rejects if a config
already exists. There is no idempotency check.

Same pattern repeats elsewhere in `bootstrap`:
- `Lambda__Deployer.deploy_from_folder` *does* check (catches
  `ResourceNotFoundException`) — but it only checks the function itself,
  not the URL or the IAM policy.
- `CloudFront__AWS__Client.create_distribution` will also throw on a
  duplicate Aliases match (`CNAMEAlreadyExists`) — same problem, just
  hasn't been hit yet because nobody has run bootstrap twice past the
  Function URL step.

## Narrow fix (today's PR could ship this alone)

Make `create_function_url` idempotent in `Lambda__AWS__Client`:

```python
def ensure_function_url(self, name: str,
                        auth_type: Enum__Lambda__Url__Auth_Type =
                            Enum__Lambda__Url__Auth_Type.NONE
                        ) -> Schema__Lambda__Url__Info:
    existing = self.get_function_url(name)
    if existing.exists:
        return existing                            # already there — no-op
    return self.create_function_url(name, auth_type)
```

Then change `bootstrap` to call `ensure_function_url` instead of
`create_function_url`. Same shape for `ensure_distribution` on the CF
side (match on Aliases).

**This unblocks the operator today.** But it doesn't solve the broader
problem — see below.

## Why the narrow fix is not enough

`ensure_*` is the right shape, but applied ad-hoc it leaves us with:

1. **No introspection.** Operator can't ask "is this account
   correctly set up?" without running `bootstrap` and reading the
   side-effects.
2. **No drift detection.** If someone edits the IAM policy in the
   console, `ensure_*` would happily skip the IAM step — and we'd
   never know the live policy disagrees with `Waker__Policy__Template`.
3. **No targeted re-apply.** If only the Lambda code changed, the
   operator still has to run the full bootstrap and hope it's
   actually idempotent on every step.
4. **No teardown story.** `unpublish` removes a single slug. There is
   no `bootstrap --delete` that removes the CF distribution + Lambda
   + IAM role in the right order.

## The path forward

Land the narrow fix on the way to the bigger refactor:

1. **Phase A (this week)** — `ensure_function_url` and
   `ensure_distribution` so bootstrap stops crashing. One-liner change
   per area. No new architecture.
2. **Phase B (the refactor)** — introduce `setup/` sub-package with
   per-area primitives, `check`, and `teardown`. See
   [04](04__per-area-capabilities.md) and [05](05__check-architecture.md).

Phase A is the bandage. Phase B is the surgery. The Phase A code
becomes redundant once Phase B lands, but it lets us unblock real
bootstrap usage today without waiting for the refactor.
