# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__CF__Create__Request
# Input for CloudFront__AWS__Client.create_distribution().
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                    import Type_Safe

from sgraph_ai_service_playwright__cli.aws.cf.collections.List__CF__Alias               import List__CF__Alias
from sgraph_ai_service_playwright__cli.aws.cf.enums.Enum__CF__Price__Class              import Enum__CF__Price__Class
from sgraph_ai_service_playwright__cli.aws.cf.primitives.Safe_Str__CF__Domain_Name     import Safe_Str__CF__Domain_Name
from sgraph_ai_service_playwright__cli.aws.cf.primitives.Safe_Str__Cert__Arn           import Safe_Str__Cert__Arn


class Schema__CF__Create__Request(Type_Safe):
    origin_domain : Safe_Str__CF__Domain_Name                                             # Lambda Function URL hostname (no scheme)
    cert_arn      : Safe_Str__Cert__Arn                                                   # ACM cert ARN (must be us-east-1)
    aliases       : List__CF__Alias                                                       # CNAME aliases e.g. ['*.aws.sg-labs.app']
    comment       : str               = ''
    price_class   : Enum__CF__Price__Class = Enum__CF__Price__Class.PriceClass_All
    enabled       : bool              = True
