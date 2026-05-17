# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/creds — Schema__Creds__Scope
# Scope catalogue entry — maps a logical name to a role ARN + max TTL.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Creds__Scope(Type_Safe):
    name       : str = ''
    role_arn   : str = ''
    max_ttl    : str = '1h'
    created_at : str = ''
