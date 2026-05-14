# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Enum__Vault_App__Runtime
# The allowlisted runtimes a vault app may declare. Deny-by-default: a runtime
# outside this set is rejected by Manifest__Interpreter. There is deliberately
# no 'shell' or 'arbitrary' member — that is the security property.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Vault_App__Runtime(str, Enum):
    STATIC = 'static'     # no runtime — files served directly
    NODE   = 'node'       # a Node.js runtime for the vault JS app
