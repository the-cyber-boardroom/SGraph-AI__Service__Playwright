# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish setup: Schema__Setup__Issue
# One human-readable problem found during a check().
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Setup__Issue(Type_Safe):
    severity : str = 'error'   # 'info' | 'warn' | 'error'
    area     : str = ''        # e.g. 'iam', 'lambda', 'cf'
    message  : str = ''        # human-readable description of the problem
