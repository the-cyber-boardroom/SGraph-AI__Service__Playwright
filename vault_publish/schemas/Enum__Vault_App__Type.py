# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Enum__Vault_App__Type
# The kind of app a vault publishes. Allowlisted set — the manifest can only
# declare one of these; anything else is rejected by Manifest__Interpreter.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Vault_App__Type(str, Enum):
    STATIC_SITE  = 'static-site'      # plain static content served as-is
    VAULT_JS_APP = 'vault-js-app'     # HTML app on top of the vault JS API
