# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Bedrock__Region__Catalogue
# Curated allowlist of AWS regions where Bedrock is GA as of v0.2.29.
# Hardcoded for v0.2.29; v0.2.30 will query the SSM parameter path.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

_BEDROCK_GA_REGIONS = [                                                           # Regions where Bedrock is GA as of 2026-05-17
    'us-east-1'      ,
    'us-east-2'      ,
    'us-west-2'      ,
    'eu-west-1'      ,
    'eu-west-2'      ,
    'eu-west-3'      ,
    'eu-central-1'   ,
    'eu-north-1'     ,
    'ap-northeast-1' ,
    'ap-northeast-2' ,
    'ap-southeast-1' ,
    'ap-southeast-2' ,
    'ap-south-1'     ,
    'ca-central-1'   ,
    'sa-east-1'      ,
]


class Bedrock__Region__Catalogue(Type_Safe):

    def is_supported(self, region: str) -> bool:                                  # True if the region is in the GA allowlist
        return region in _BEDROCK_GA_REGIONS

    def supported_regions(self) -> list:                                          # Returns the full list of GA region strings
        return list(_BEDROCK_GA_REGIONS)
