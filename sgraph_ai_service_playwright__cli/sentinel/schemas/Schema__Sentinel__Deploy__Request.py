# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Sentinel__Deploy__Request
# Input for Sentinel__Deployer.create(). Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                     import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_Str                                      import Safe_Str

from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Region      import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.aws.cf.primitives.Safe_Str__CF__Distribution_Id   import Safe_Str__CF__Distribution_Id
from sgraph_ai_service_playwright__cli.aws.s3.primitives.Safe_Str__S3__Bucket            import Safe_Str__S3__Bucket


class Schema__Sentinel__Deploy__Request(Type_Safe):
    distribution_id : Safe_Str__CF__Distribution_Id                                 # '' → create a new ephemeral test distribution
    region          : Safe_Str__AWS__Region
    log_bucket      : Safe_Str__S3__Bucket                                          # '' → derive a name
    comment         : Safe_Str
