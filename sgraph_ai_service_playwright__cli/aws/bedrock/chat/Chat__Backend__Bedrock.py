# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — aws/bedrock/chat: Chat__Backend__Bedrock
# The Bedrock adapter for the neutral Chat__Backend seam (plan 07). All Bedrock
# wire-shaping that used to live in the engine lives HERE: neutral messages → Converse
# blocks (text / document / toolUse / toolResult), neutral tools → toolConfig, the
# Converse response → neutral content, and Nova pricing via the cost calculator. The
# model_id is treated as a neutral alias and resolved against PROVIDER + region (region
# is backend config, not a per-call argument). The boto3 boundary stays in the injected
# source — this adapter never imports boto3.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Cost__Calculator        import Bedrock__Cost__Calculator
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Model__Resolver         import Bedrock__Model__Resolver
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.bedrock_chat_tui__config             import PROVIDER
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.schemas.Schema__Bedrock__Chat__Document import Schema__Bedrock__Chat__Document
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.service.Bedrock__Chat__Documents     import Bedrock__Chat__Documents
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.source.Bedrock__Chat__Source         import Bedrock__Chat__Source
from sgraph_ai_service_playwright__cli.tui.chat.backend.Chat__Backend                       import Chat__Backend
from sgraph_ai_service_playwright__cli.tui.chat.enums.Enum__Chat__Role                      import Enum__Chat__Role
from sgraph_ai_service_playwright__cli.tui.chat.schemas.List__Chat__Content                 import List__Chat__Content
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Capabilities          import Schema__Chat__Capabilities
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Content               import Schema__Chat__Content
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Tool_Use              import Schema__Chat__Tool_Use
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Turn__Result          import Schema__Chat__Turn__Result
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Usage                 import Schema__Chat__Usage


class Chat__Backend__Bedrock(Chat__Backend):
    source    : Bedrock__Chat__Source                                             # injected boto3 boundary (AWS | in-memory)
    resolver  : Bedrock__Model__Resolver
    calc      : Bedrock__Cost__Calculator
    documents : Bedrock__Chat__Documents
    provider  : str = PROVIDER                                                    # backend config — Nova for v1
    region    : str = ''                                                          # backend config — NOT a per-call argument

    def id(self) -> str:
        return 'bedrock'

    def capabilities(self, model_id: str) -> Schema__Chat__Capabilities:
        return Schema__Chat__Capabilities(streaming=True, tools=True, documents=True, vision=False)

    def resolve(self, model_id: str) -> str:                                      # neutral alias → Bedrock model id
        return self.resolver.resolve(self.provider, model_id or 'default', self.region)

    def cost(self, model_id: str, usage: Schema__Chat__Usage) -> float:
        return self.calc.estimate(self.resolve(model_id), usage.input_tokens, usage.output_tokens)

    def stream_turn(self, model_id: str, messages, system: str = None, options: dict = None):
        wire = self.wire_messages(messages)
        for kind, payload in self.source.stream_turn(self.resolve(model_id), wire, region=self.region, system=system):
            if kind == 'delta':
                yield ('delta', payload)
            elif kind == 'usage':
                in_tok, out_tok, latency = payload
                yield ('usage', Schema__Chat__Usage(input_tokens=in_tok, output_tokens=out_tok, latency_ms=latency))

    def converse(self, model_id: str, messages, system: str = None,
                 tools=None, options: dict = None) -> Schema__Chat__Turn__Result:
        wire        = self.wire_messages(messages)
        tool_config = self.wire_tool_config(tools)
        response    = self.source.converse_turn(self.resolve(model_id), wire, region=self.region,
                                               system=system, tool_config=tool_config)
        result = Schema__Chat__Turn__Result(stop_reason = response.get('stop_reason', 'end_turn'),
                                           content     = self.neutral_content(response.get('content', [])),
                                           usage       = Schema__Chat__Usage(input_tokens  = int(response.get('input_tokens',  0)),
                                                                            output_tokens = int(response.get('output_tokens', 0)),
                                                                            latency_ms    = int(response.get('latency_ms',    0))))
        return result

    # ── neutral ↔ Bedrock wire-shaping ───────────────────────────────────────────────

    def wire_messages(self, messages) -> list:                                    # neutral messages → Converse messages list
        out = []
        for message in messages:
            role    = 'assistant' if message.role == Enum__Chat__Role.ASSISTANT else 'user'
            content = []
            for block in message.content:
                if   block.tool_use    is not None: content.append(self.wire_tool_use(block.tool_use))
                elif block.tool_result is not None: content.append(self.wire_tool_result(block.tool_result))
                elif block.document    is not None: content.append(self.documents.content_block(self.bedrock_document(block.document)))
                elif block.text                   : content.append({'text': block.text})
            out.append({'role': role, 'content': content})
        return out

    def wire_tool_use(self, tool_use) -> dict:
        return {'toolUse': {'toolUseId': str(tool_use.id), 'name': str(tool_use.name), 'input': dict(tool_use.input)}}

    def wire_tool_result(self, tool_result) -> dict:
        return {'toolResult': {'toolUseId': str(tool_result.id),
                              'content'  : [{'json': dict(tool_result.data)}],
                              'status'   : str(tool_result.status)}}

    def wire_tool_config(self, tools) -> dict:                                    # neutral tools → Bedrock toolConfig
        if not tools:
            return None
        specs = [{'toolSpec': {'name'       : str(tool.name),
                              'description': str(tool.description),
                              'inputSchema': {'json': dict(tool.input_schema)}}} for tool in tools]
        return {'tools': specs}

    def bedrock_document(self, document) -> Schema__Bedrock__Chat__Document:       # neutral document → the Bedrock document schema
        return Schema__Bedrock__Chat__Document(name=str(document.name), format=str(document.format),
                                             size=int(document.size), data_b64=str(document.data_b64))

    def neutral_content(self, content: list) -> List__Chat__Content:              # Converse response content → neutral blocks
        blocks = List__Chat__Content()
        for block in content:
            tool_use = block.get('toolUse')
            if tool_use:
                blocks.append(Schema__Chat__Content(tool_use=Schema__Chat__Tool_Use(
                    id=str(tool_use.get('toolUseId', '')), name=str(tool_use.get('name', '')),
                    input=tool_use.get('input', {}) or {})))
            elif 'text' in block:
                blocks.append(Schema__Chat__Content(text=block['text']))
        return blocks
