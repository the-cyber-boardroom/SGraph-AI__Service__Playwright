# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__CF__Distribution
# One CloudFront distribution summary as returned by list / get.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                     import Type_Safe

from sgraph_ai_service_playwright__cli.aws.cf.collections.List__CF__Alias                import List__CF__Alias
from sgraph_ai_service_playwright__cli.aws.cf.enums.Enum__CF__Distribution__Status      import Enum__CF__Distribution__Status
from sgraph_ai_service_playwright__cli.aws.cf.enums.Enum__CF__Price__Class               import Enum__CF__Price__Class
from sgraph_ai_service_playwright__cli.aws.cf.primitives.Safe_Str__CF__Distribution_Id  import Safe_Str__CF__Distribution_Id
from sgraph_ai_service_playwright__cli.aws.cf.primitives.Safe_Str__CF__Domain_Name      import Safe_Str__CF__Domain_Name
from sgraph_ai_service_playwright__cli.aws.cf.primitives.Safe_Str__Cert__Arn            import Safe_Str__Cert__Arn


class Schema__CF__Distribution(Type_Safe):
    distribution_id : Safe_Str__CF__Distribution_Id                                      # E1ABCDE2FGHIJK
    domain_name     : Safe_Str__CF__Domain_Name                                          # d1abc.cloudfront.net
    status          : Enum__CF__Distribution__Status = Enum__CF__Distribution__Status.IN_PROGRESS
    comment         : str                            = ''
    enabled         : bool                           = True
    cert_arn        : Safe_Str__Cert__Arn                                                # ACM ARN (empty when using default CF cert)
    price_class     : Enum__CF__Price__Class         = Enum__CF__Price__Class.PriceClass_All
    aliases         : List__CF__Alias                                                     # CNAME aliases (e.g. ['*.aws.sg-labs.app'])
    created_time    : str                            = ''                                # ISO-8601 string from API
