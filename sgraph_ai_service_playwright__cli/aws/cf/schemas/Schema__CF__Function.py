# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__CF__Function
# Metadata for a CloudFront Function. Pure data — no methods.
# `stage` is 'DEVELOPMENT' or 'LIVE'. `etag` is the opaque version token used
# for subsequent update_function / publish_function / delete_function calls.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__CF__Function(Type_Safe):
    name           : str  = ''
    arn            : str  = ''
    stage          : str  = ''                                                       # DEVELOPMENT or LIVE
    status         : str  = ''                                                       # UNPUBLISHED, UNASSOCIATED, INUSE
    runtime        : str  = 'cloudfront-js-2.0'
    comment        : str  = ''
    etag           : str  = ''                                                       # required for update/publish/delete
    last_modified  : str  = ''
    exists         : bool = False
