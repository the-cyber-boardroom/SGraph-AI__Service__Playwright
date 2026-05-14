# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Enum__Provisioning__Step_Kind
# The allowlisted vocabulary of provisioning steps. Manifest__Interpreter only
# ever emits steps of these kinds — there is no step kind that runs arbitrary
# code. The closed set is the allowlist.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Provisioning__Step_Kind(str, Enum):
    SET_RUNTIME      = 'set-runtime'        # select the (allowlisted) runtime
    MOUNT_CONTENT    = 'mount-content'      # point the server at the content root
    SET_ENV          = 'set-env'            # apply one allowlisted env key/value
    REGISTER_ROUTE   = 'register-route'     # map a request path to a content path
    SET_HEALTH_PATH  = 'set-health-path'    # the path the warming page polls
