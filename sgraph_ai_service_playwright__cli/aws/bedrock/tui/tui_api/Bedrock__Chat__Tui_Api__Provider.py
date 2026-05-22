# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — aws/bedrock/tui/tui_api: Bedrock__Chat__Tui_Api__Provider
# Decision #8 (v1): the chat is itself a TUI API provider — driveable + inspectable
# the same way the tools it consumes are. Its Schema__Bedrock__Chat__Session IS the
# state() surface (no new state); send/clear/set_model are the actions; each send's
# cost is attributed on the Result (the cost-first differentiator). Pure: the engine's
# AWS call is behind the injected source, so tests use the in-memory engine.
#
# Recommendation (pack-05 §8): state is READ_ONLY (default-exposable); send is WRITE
# (it spends money) so the execution center gates it when driven headlessly.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.schemas.Schema__Bedrock__Chat__Session import Schema__Bedrock__Chat__Session
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.service.Bedrock__Chat__Engine          import Bedrock__Chat__Engine
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.tui_api.schemas.Schema__Chat__Params__Send      import Schema__Chat__Params__Send
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.tui_api.schemas.Schema__Chat__Params__Set_Model import Schema__Chat__Params__Set_Model
from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Tier               import Enum__Tui_Api__Tier
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Action            import List__Tui_Api__Action
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Tier              import List__Tui_Api__Tier
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Action          import Schema__Tui_Api__Action
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Manifest        import Schema__Tui_Api__Manifest
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Result          import Schema__Tui_Api__Result
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Scope           import Schema__Tui_Api__Scope
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Provider               import Tui_Api__Provider
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Schema__Builder         import Tui_Api__Schema__Builder


class Bedrock__Chat__Tui_Api__Provider(Tui_Api__Provider):
    engine      : Bedrock__Chat__Engine                                           # inject one over an in-memory source in tests
    builder     : Tui_Api__Schema__Builder
    session     : Schema__Bedrock__Chat__Session = None
    region      : str = 'us-east-1'
    model_alias : str = 'lite'

    def ensure_session(self) -> Schema__Bedrock__Chat__Session:
        if self.session is None:
            self.session = self.engine.new_session(region=self.region, model_alias=self.model_alias)
        return self.session

    def manifest(self) -> Schema__Tui_Api__Manifest:
        write = Schema__Tui_Api__Scope(api='sg-aws.bedrock-chat', capability='write')
        actions = List__Tui_Api__Action()
        actions.append(Schema__Tui_Api__Action(name='send', tier=Enum__Tui_Api__Tier.WRITE, scope=write,
                                              description='Send a user message; returns the reply + its token cost.',
                                              input_schema=self.builder.input_schema(Schema__Chat__Params__Send)))
        actions.append(Schema__Tui_Api__Action(name='set_model', tier=Enum__Tui_Api__Tier.WRITE, scope=write,
                                              description='Switch the Nova model (keeps the conversation).',
                                              input_schema=self.builder.input_schema(Schema__Chat__Params__Set_Model)))
        actions.append(Schema__Tui_Api__Action(name='clear', tier=Enum__Tui_Api__Tier.WRITE, scope=write,
                                              description='Clear the conversation and reset cost (new session).',
                                              input_schema={'type': 'object', 'properties': {}}))
        tiers = List__Tui_Api__Tier()
        tiers.append(Enum__Tui_Api__Tier.READ_ONLY)
        tiers.append(Enum__Tui_Api__Tier.WRITE)
        return Schema__Tui_Api__Manifest(slug='sg-aws.bedrock-chat', tool='sg-aws', name='Bedrock chat (Nova)',
                                        version='0.1.0',
                                        description='Drive + inspect the Nova chat: send, switch model, clear; state is the live session.',
                                        tiers=tiers, actions=actions)

    def state(self) -> dict:                                                      # the read surface — the live session
        session = self.ensure_session()
        return {'model_alias'        : str(session.model_alias),
                'region'             : session.region,
                'turns'              : session.turn_count,
                'messages'           : len(session.messages),
                'total_input_tokens' : session.total_input_tokens,
                'total_output_tokens': session.total_output_tokens,
                'total_cost_usd'     : session.total_cost_usd}

    def dispatch(self, action: str, params: dict) -> Schema__Tui_Api__Result:
        try:
            session = self.ensure_session()
            if action == 'send':
                p    = Schema__Chat__Params__Send(**params)
                turn = self.engine.send_turn(session, str(p.text))
                data = {'assistant_text': session.messages[-1].text,
                        'input_tokens'  : turn.input_tokens,
                        'output_tokens' : turn.output_tokens,
                        'cost_usd'      : turn.cost_usd}
                return Schema__Tui_Api__Result(ok=True, data={'result': data}, cost_usd=turn.cost_usd)
            if action == 'set_model':
                p = Schema__Chat__Params__Set_Model(**params)
                session.model_alias = str(p.alias)
                return Schema__Tui_Api__Result(ok=True, data={'result': {'model_alias': str(p.alias)}})
            if action == 'clear':
                self.session = self.engine.new_session(region=session.region, model_alias=str(session.model_alias))
                return Schema__Tui_Api__Result(ok=True, data={'result': {'cleared': True}})
            return Schema__Tui_Api__Result(ok=False, error=f'unknown action: {action}')
        except Exception as exc:
            return Schema__Tui_Api__Result(ok=False, error=f'{type(exc).__name__}: {exc}')
