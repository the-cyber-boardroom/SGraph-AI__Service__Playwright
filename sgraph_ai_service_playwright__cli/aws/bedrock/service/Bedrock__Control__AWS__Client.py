# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Bedrock__Control__AWS__Client
# Sole boto3 boundary for the Bedrock control-plane API (service name 'bedrock').
# Used for list-models only (list_foundation_models).
#
# EXCEPTION: boto3 used directly — no osbot-aws Bedrock wrapper exists.
# Pattern matches ACM__AWS__Client precedent.
# ═══════════════════════════════════════════════════════════════════════════════

import boto3                                                                     # EXCEPTION — see module header

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.aws.bedrock.collections.List__Schema__Bedrock__Model import List__Schema__Bedrock__Model
from sgraph_ai_service_playwright__cli.aws.bedrock.enums.Enum__Bedrock__Provider             import Enum__Bedrock__Provider
from sgraph_ai_service_playwright__cli.aws.bedrock.primitives.Safe_Str__Bedrock__Model_Id    import Safe_Str__Bedrock__Model_Id
from sgraph_ai_service_playwright__cli.aws.bedrock.schemas.Schema__Bedrock__Model            import Schema__Bedrock__Model

FALLBACK_REGION = 'us-east-1'


class Bedrock__Control__AWS__Client(Type_Safe):

    def client(self, region: str = None):                                        # Single seam — tests override to return a fake client
        from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session import Sg__Aws__Session
        return Sg__Aws__Session.from_context().boto3_client_from_context('bedrock', region=region or self.current_region())

    def current_region(self) -> str:                                             # Returns the boto3 configured region, falling back to us-east-1
        region = boto3.session.Session().region_name
        return region if region else FALLBACK_REGION

    def list_models(self, region: str = None, provider_filter: str = None) -> List__Schema__Bedrock__Model:
        effective_region = region or self.current_region()
        bedrock          = self.client(effective_region)
        models           = List__Schema__Bedrock__Model()
        kwargs = {'byInferenceType': 'ON_DEMAND'}
        if provider_filter:
            kwargs['byProvider'] = provider_filter
        resp  = bedrock.list_foundation_models(**kwargs)              # let ClientError propagate — no silent swallow
        items = resp.get('modelSummaries', [])
        for item in items:
            model = self.map_model(item, effective_region)
            if model is not None:
                models.append(model)
        return models

    def map_model(self, raw: dict, region: str):                                 # Map a raw boto3 model summary to Schema__Bedrock__Model
        model_id   = raw.get('modelId', '')
        model_name = raw.get('modelName', '')
        provider   = raw.get('providerName', '')
        input_mods = ', '.join(raw.get('inputModalities', []))
        output_mods= ', '.join(raw.get('outputModalities', []))
        try:
            safe_id    = Safe_Str__Bedrock__Model_Id(model_id)
        except Exception:
            return None
        provider_enum = self.infer_provider(provider, model_id)
        return Schema__Bedrock__Model(model_id          = safe_id      ,
                                      model_name        = model_name   ,
                                      provider          = provider_enum,
                                      provider_name     = provider     ,
                                      input_modalities  = input_mods   ,
                                      output_modalities = output_mods  ,
                                      region            = region       )

    def infer_provider(self, provider_name: str, model_id: str) -> Enum__Bedrock__Provider:
        name  = provider_name.lower()
        mid   = model_id.lower()
        if 'anthropic' in name or 'claude' in mid:
            return Enum__Bedrock__Provider.CLAUDE
        if 'amazon'    in name and 'nova'  in mid:
            return Enum__Bedrock__Provider.NOVA
        if 'meta'      in name or 'llama'  in mid:
            return Enum__Bedrock__Provider.LLAMA
        if 'openai'    in name or 'openai' in mid:
            return Enum__Bedrock__Provider.OPENAI
        return Enum__Bedrock__Provider.OTHER
