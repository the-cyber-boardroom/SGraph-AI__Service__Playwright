# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: Schema__CF_TUI__Arch_Snapshot
# The deployed-architecture snapshot the wiring view renders: live CloudFront
# distributions, the CF-logs S3 bucket reachability, CloudWatch log groups — and an
# explicit Firehose note (not introspectable via sg aws). Per-source error strings
# surface honestly when a credential/permission is missing rather than crashing.
# Built by CF_TUI__Arch_Source. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.aws.firehose.schemas.List__Firehose__Stream             import List__Firehose__Stream
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.List__CF_TUI__Arch_Distribution import List__CF_TUI__Arch_Distribution
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.List__CF_TUI__Arch_Log_Group    import List__CF_TUI__Arch_Log_Group


class Schema__CF_TUI__Arch_Snapshot(Type_Safe):
    captured_at        : int = 0
    distributions      : List__CF_TUI__Arch_Distribution
    firehose_streams   : List__Firehose__Stream                                      # now enumerated via `sg aws firehose` — the Firehose→S3 hop is verified
    log_groups         : List__CF_TUI__Arch_Log_Group
    bucket_name        : str
    bucket_reachable   : bool = False
    bucket_top_folders : int  = 0                                                    # top-level prefixes under cloudfront-realtime/
    firehose_note      : str  = 'per-distribution real-time-log → Firehose mapping is not introspectable via sg aws'
    cf_error           : str                                                         # populated when the CloudFront read failed (e.g. no creds)
    logs_error         : str
    s3_error           : str
    firehose_error     : str
