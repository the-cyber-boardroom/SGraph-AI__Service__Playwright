# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Enum__Tui_Api__Priv_Kind
# The kind of backing grant an SG/Role scope maps DOWN to when an action runs.
# SG_ROLE / IAM_ROLE map to a creds scope (role assumption); the rest are presence checks.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Tui_Api__Priv_Kind(str, Enum):
    SG_ROLE    = 'sg_role'                                                         # a named SG/Role -> a creds scope (role ARN + TTL)
    IAM_POLICY = 'iam_policy'                                                      # an IAM policy / action string
    IAM_ROLE   = 'iam_role'                                                        # an IAM role to assume (via aws/creds)
    VAULT_KEY  = 'vault_key'                                                       # a vault key that must be unlocked
    ENV        = 'env'                                                             # an environment variable that must be set
    NETWORK    = 'network'                                                         # outbound network access
    OTHER      = 'other'

    def __str__(self):
        return self.value
