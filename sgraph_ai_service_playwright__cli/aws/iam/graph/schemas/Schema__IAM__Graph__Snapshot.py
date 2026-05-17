# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__IAM__Graph__Snapshot
# Top-level metadata for a single IAM graph snapshot.
# Pure data. No methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                           import Type_Safe

from sgraph_ai_service_playwright__cli.aws.iam.graph.primitives.Safe_Str__IAM__Snapshot__Id   import Safe_Str__IAM__Snapshot__Id


class Schema__IAM__Graph__Snapshot(Type_Safe):
    snapshot_id    : Safe_Str__IAM__Snapshot__Id               # <ISO-ts-Z>__<nonce>
    captured_at    : str                         = ''           # ISO-8601 UTC
    role_count     : int                         = 0
    policy_count   : int                         = 0
    user_count     : int                         = 0
    group_count    : int                         = 0
    edge_count     : int                         = 0
    aws_account_id : str                         = ''
    region         : str                         = ''
