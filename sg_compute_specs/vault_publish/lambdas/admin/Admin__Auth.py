# ═══════════════════════════════════════════════════════════════════════════════
# Admin — Admin__Auth
# API-key gate for the admin UI surface. Two env vars (set by Setup__Lambda at
# deploy time, auto-generated on first create):
#   SG_VAULT_PUBLISH__ADMIN__API_KEY_NAME   — cookie + header name
#   SG_VAULT_PUBLISH__ADMIN__API_KEY_VALUE  — the secret token
#
# A request is authorised iff either:
#   - it carries the header `<KEY_NAME>: <KEY_VALUE>`, OR
#   - it carries the cookie `<KEY_NAME>=<KEY_VALUE>`
#
# The login flow accepts the value via POST form, then sets a cookie scoped to
# `Domain=.<zone>` so it's valid across every subdomain of the public zone —
# operator sets it once in the browser, every <slug>.<zone> and waker.<zone>
# tab carries it forward.
#
# Fails closed: if either env var is missing, no request is authorised. This
# means the admin UI is not exposed until the Lambda has had its env vars
# baked — see Setup__Lambda._build_deploy_env.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import secrets

from osbot_utils.type_safe.Type_Safe import Type_Safe

ENV_KEY_NAME   = 'SG_VAULT_PUBLISH__ADMIN__API_KEY_NAME'
ENV_KEY_VALUE  = 'SG_VAULT_PUBLISH__ADMIN__API_KEY_VALUE'
DEFAULT_NAME   = 'sg-vp-admin-key'                                                    # default cookie/header name if env var unset


def configured_key_name() -> str:
    return os.environ.get(ENV_KEY_NAME, DEFAULT_NAME)


def configured_key_value() -> str:
    return os.environ.get(ENV_KEY_VALUE, '')


def is_configured() -> bool:
    return bool(configured_key_value())


def generate_key_value() -> str:
    return secrets.token_urlsafe(24)                                                  # ~32 char URL-safe random token


class Admin__Auth(Type_Safe):

    def check(self, *, headers: dict, cookies: dict) -> bool:
        key_name  = configured_key_name()
        key_value = configured_key_value()
        if not key_value:
            return False                                                              # fail closed when not configured
        # Header lookup is case-insensitive — `headers` here is dict-like with
        # already-lowered keys (FastAPI normalises) or raw HTTP headers. Try both.
        hv = headers.get(key_name) or headers.get(key_name.lower()) or headers.get(key_name.upper())
        if hv and _consteq(hv, key_value):
            return True
        cv = cookies.get(key_name)
        if cv and _consteq(cv, key_value):
            return True
        return False


def _consteq(a: str, b: str) -> bool:
    # Constant-time string comparison — defends against timing oracles.
    if len(a) != len(b):
        return False
    return secrets.compare_digest(a, b)
