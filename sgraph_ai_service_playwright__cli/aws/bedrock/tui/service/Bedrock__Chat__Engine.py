# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: Bedrock__Chat__Engine
# The printing-free orchestrator for a chat turn (what run_chat() does, minus typer /
# Console / Exit). The ONLY place that knows how a turn executes; the Textual view
# just calls send_turn and renders. Pure: no Textual, no boto3 — the AWS call is
# behind the injected source. Reuses the existing Resolver + Cost calculator verbatim.
# ═══════════════════════════════════════════════════════════════════════════════

import time
import uuid

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.aws.bedrock.primitives.Safe_Str__Bedrock__Model_Id     import Safe_Str__Bedrock__Model_Id
from sgraph_ai_service_playwright__cli.aws.bedrock.primitives.Safe_Str__Bedrock__Session_Id   import Safe_Str__Bedrock__Session_Id
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Cost__Calculator           import Bedrock__Cost__Calculator
from sgraph_ai_service_playwright__cli.aws.bedrock.service.Bedrock__Model__Resolver            import Bedrock__Model__Resolver
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.bedrock_chat_tui__config                import (PROVIDER, DEFAULT_MODEL_ALIAS,
                                                                                                       DEFAULT_BUDGET_USD)
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.enums.Enum__Bedrock__Chat__Role         import Enum__Bedrock__Chat__Role
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.schemas.Schema__Bedrock__Chat__Message  import Schema__Bedrock__Chat__Message
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.schemas.Schema__Bedrock__Chat__Session  import Schema__Bedrock__Chat__Session
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.schemas.Schema__Bedrock__Chat__Turn     import Schema__Bedrock__Chat__Turn
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.source.Bedrock__Chat__Source            import Bedrock__Chat__Source


class Bedrock__Chat__Engine(Type_Safe):
    source   : Bedrock__Chat__Source                                              # injected (AWS | in-memory)
    resolver : Bedrock__Model__Resolver
    calc     : Bedrock__Cost__Calculator

    def new_session(self, region: str = '', model_alias: str = DEFAULT_MODEL_ALIAS,
                    context=None, budget_usd: float = DEFAULT_BUDGET_USD) -> Schema__Bedrock__Chat__Session:
        session = Schema__Bedrock__Chat__Session(session_id  = Safe_Str__Bedrock__Session_Id(uuid.uuid4().hex),
                                                 provider    = PROVIDER,
                                                 model_alias = model_alias,
                                                 region      = region,
                                                 started_at  = time.time(),
                                                 budget_usd  = budget_usd)
        if context is not None and context.body:
            session.system_prompt = ('You are a focused engineering assistant. The user is '
                                     'looking at the following context and wants to diagnose it '
                                     'and turn findings into action items.\n\n' + context.body)
            session.context_label = context.label
        return session

    def resolve_model(self, session: Schema__Bedrock__Chat__Session) -> str:
        return self.resolver.resolve(session.provider, session.model_alias, session.region)

    def build_messages(self, session: Schema__Bedrock__Chat__Session) -> list:    # session messages → Bedrock messages list (system goes separately)
        out = []
        for m in session.messages:
            if m.role == Enum__Bedrock__Chat__Role.SYSTEM:
                continue
            role = 'assistant' if m.role == Enum__Bedrock__Chat__Role.ASSISTANT else 'user'
            out.append({'role': role, 'content': [{'text': m.text}]})
        return out

    def preflight_cost(self, session: Schema__Bedrock__Chat__Session, user_text: str,
                       cost_override: float = None) -> None:                       # raises ValueError if over the per-call cap
        model_id      = self.resolve_model(session)
        history_chars = sum(len(m.text) for m in session.messages) + len(user_text)
        self.calc.check_cost_cap(model_id, history_chars, cost_override)

    def send_turn(self, session: Schema__Bedrock__Chat__Session, user_text: str,
                  on_delta=None, cost_override: float = None) -> Schema__Bedrock__Chat__Turn:
        model_id = self.resolve_model(session)

        # Pre-flight BEFORE mutating the session, so a rejected send leaves it clean.
        self.preflight_cost(session, user_text, cost_override)

        session.messages.append(Schema__Bedrock__Chat__Message(role=Enum__Bedrock__Chat__Role.USER,
                                                               text=user_text, ts=time.time()))
        messages = self.build_messages(session)
        system   = session.system_prompt or None

        parts = []
        in_tok = out_tok = latency = 0
        for kind, payload in self.source.stream_turn(model_id, messages, region=session.region, system=system):
            if kind == 'delta':
                parts.append(payload)
                if on_delta is not None:
                    on_delta(payload)
            elif kind == 'usage':
                in_tok, out_tok, latency = payload

        response_text = ''.join(parts)
        session.messages.append(Schema__Bedrock__Chat__Message(role=Enum__Bedrock__Chat__Role.ASSISTANT,
                                                              text=response_text, ts=time.time()))

        cost = self.calc.estimate(model_id, in_tok, out_tok)
        turn = Schema__Bedrock__Chat__Turn(model_id      = Safe_Str__Bedrock__Model_Id(model_id),
                                           input_tokens  = in_tok,
                                           output_tokens = out_tok,
                                           cost_usd      = cost,
                                           latency_ms    = latency,
                                           ts            = time.time())
        session.turns.append(turn)
        session.total_input_tokens  += in_tok
        session.total_output_tokens += out_tok
        session.total_cost_usd      += cost
        session.turn_count          += 1
        return turn
