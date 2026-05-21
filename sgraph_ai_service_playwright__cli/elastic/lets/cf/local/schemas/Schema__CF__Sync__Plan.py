# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf local: Schema__CF__Sync__Plan
# The diff between what S3 holds for a scope (date / day+hour) and what is already in
# the local raw-cf-logs cache. This is the "list" mode output and the input to the
# "download" mode. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.schemas.List__CF__Sync__File import List__CF__Sync__File


class Schema__CF__Sync__Plan(Type_Safe):
    bucket        : str
    prefix        : str                                                              # scoped S3 prefix this plan covers
    date_iso      : str
    hour          : str
    remote_count  : int = 0
    local_count   : int = 0                                                          # already present locally
    missing_count : int = 0
    present_bytes : int = 0
    missing_bytes : int = 0
    files         : List__CF__Sync__File
