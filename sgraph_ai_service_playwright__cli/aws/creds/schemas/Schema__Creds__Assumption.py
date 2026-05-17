# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/creds — Schema__Creds__Assumption
# Represents a single STS role-assumption event (as stored in audit log).
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Creds__Assumption(Type_Safe):
    assumption_id  : str = ''
    scope_name     : str = ''
    role_arn       : str = ''
    caller         : str = ''
    assumed_at     : str = ''
    expires_at     : str = ''
    access_key_id  : str = ''
    session_token  : str = ''
