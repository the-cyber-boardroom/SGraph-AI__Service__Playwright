# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Sentinel__Deploy__Response
# Returned by Sentinel__Deployer.create(). Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                     import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_Str                                      import Safe_Str

from sgraph_ai_service_playwright__cli.aws.cf.primitives.Safe_Str__CF__Distribution_Id   import Safe_Str__CF__Distribution_Id
from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Arn      import Safe_Str__Lambda__Arn
from sgraph_ai_service_playwright__cli.aws.s3.primitives.Safe_Str__S3__Bucket            import Safe_Str__S3__Bucket


class Schema__Sentinel__Deploy__Response(Type_Safe):
    distribution_id : Safe_Str__CF__Distribution_Id
    cf_function_arn : Safe_Str
    lambda_edge_arn : Safe_Str__Lambda__Arn
    log_bucket      : Safe_Str__S3__Bucket
    status          : Safe_Str
