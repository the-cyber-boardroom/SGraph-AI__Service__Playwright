# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Bedrock__Runtime__AWS__Client
# Sole boto3 boundary for the Bedrock runtime API (service name 'bedrock-runtime').
# Handles converse calls for all chat providers.
#
# Note: boto3.session.Session() is used in current_region() for config reading
# only — no client calls bypass Sg__Aws__Session.
# ═══════════════════════════════════════════════════════════════════════════════

import boto3                                                                     # used only in current_region() for config reading

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session      import Sg__Aws__Session

FALLBACK_REGION = 'us-east-1'


class Bedrock__Runtime__AWS__Client(Type_Safe):
    session : Sg__Aws__Session = None                                            # cached session — injected or lazy-init via setup()

    def setup(self):                                                              # idempotent — noop if session already set
        if self.session is None:
            self.session = Sg__Aws__Session.from_context()
        return self

    def client(self, region: str = None):                                        # Single seam — tests override to return a fake client
        self.setup()
        return self.session.boto3_client_from_context('bedrock-runtime', region=region or self.current_region())

    def current_region(self) -> str:                                             # Returns the boto3 configured region, falling back to us-east-1
        region = boto3.session.Session().region_name
        return region if region else FALLBACK_REGION

    def converse(self, model_id: str, prompt: str, region: str = None) -> dict:
        """Send a single-turn converse request; returns the raw boto3 response."""  # inline
        effective_region = region or self.current_region()
        runtime          = self.client(effective_region)
        messages         = [{'role': 'user', 'content': [{'text': prompt}]}]
        resp             = runtime.converse(modelId=model_id, messages=messages)
        return resp

    def converse_stream(self, model_id: str, prompt: str, region: str = None):
        """Yield raw streaming chunks from a converse_stream call."""             # inline
        effective_region = region or self.current_region()
        runtime          = self.client(effective_region)
        messages         = [{'role': 'user', 'content': [{'text': prompt}]}]
        stream_resp      = runtime.converse_stream(modelId=model_id, messages=messages)
        stream           = stream_resp.get('stream')
        if stream:
            for event in stream:
                yield event

    def extract_text(self, response: dict) -> str:                               # Extract the assistant text from a converse response
        output   = response.get('output', {})
        message  = output.get('message', {})
        contents = message.get('content', [])
        parts    = [c.get('text', '') for c in contents if c.get('text')]
        return '\n'.join(parts)

    def extract_usage(self, response: dict) -> tuple:                            # Returns (input_tokens, output_tokens) from a converse response
        usage = response.get('usage', {})
        return (int(usage.get('inputTokens', 0)),
                int(usage.get('outputTokens', 0)))
