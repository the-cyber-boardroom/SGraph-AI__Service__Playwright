# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/cloudtrail — Schema__CloudTrail__Event
# Summary schema for a single CloudTrail event.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__CloudTrail__Event(Type_Safe):
    event_id             : str = ''
    event_time           : str = ''
    event_name           : str = ''
    username             : str = ''
    source_ip_address    : str = ''
    aws_region           : str = ''
    request_parameters   : str = ''   # JSON-serialised string
    response_elements    : str = ''   # JSON-serialised string
    resources            : str = ''   # JSON-serialised string
    error_code           : str = ''
    error_message        : str = ''
