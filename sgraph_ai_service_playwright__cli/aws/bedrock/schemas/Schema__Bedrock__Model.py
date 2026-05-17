# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Bedrock__Model
# One enabled Bedrock foundation model as returned by list_foundation_models.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.aws.bedrock.enums.Enum__Bedrock__Provider import Enum__Bedrock__Provider
from sgraph_ai_service_playwright__cli.aws.bedrock.primitives.Safe_Str__Bedrock__Model_Id import Safe_Str__Bedrock__Model_Id


class Schema__Bedrock__Model(Type_Safe):
    model_id          : Safe_Str__Bedrock__Model_Id                                 # Canonical Bedrock model ID
    model_name        : str                                                          # Human-readable name
    provider          : Enum__Bedrock__Provider                                      # Provider family
    provider_name     : str                                                          # Raw provider string from Bedrock
    input_modalities  : str                                                          # Comma-separated input modalities
    output_modalities : str                                                          # Comma-separated output modalities
    region            : str                                                          # AWS region where listed
