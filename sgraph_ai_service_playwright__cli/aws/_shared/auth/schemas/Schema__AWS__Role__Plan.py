# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — aws shared auth: Schema__AWS__Role__Plan
# The diff between a family's desired least-priv role (from the profile) and what
# exists in IAM right now. Drives `… iam plan` / the create/update confirmation. Pure
# data — the provisioner fills it, the CLI renders it. No methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__AWS__Role__Plan(Type_Safe):
    family            : str
    role_name         : str
    role_arn          : str
    exists            : bool                                                         # role already present in IAM
    actions_desired   : list                                                         # from the profile
    actions_current   : list                                                         # from the live inline policy ('' → none)
    actions_to_add    : list                                                         # desired − current
    actions_to_remove : list                                                         # current − desired
    in_sync           : bool                                                         # exists and no add/remove
    policy_json       : str                                                          # the inline policy we would write
    trust_json        : str                                                          # the trust policy we would write
