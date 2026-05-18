# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish setup: Schema__Setup__Action
# A suggested remediation step to fix a detected issue.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Setup__Action(Type_Safe):
    area   : str = ''   # e.g. 'iam', 'lambda', 'url', 'cf', 'dns'
    verb   : str = ''   # e.g. 'create', 'update', 'delete'
    reason : str = ''   # human-readable explanation
