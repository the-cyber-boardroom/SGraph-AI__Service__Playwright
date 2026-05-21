# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: Bedrock__Chat__Engine
# The printing-free orchestrator for a chat turn (what run_chat() does, minus typer /
# Console / Exit). The ONLY place that knows how a turn executes; the Textual view
# just calls send_turn and renders. Pure: no Textual, no boto3 — the AWS call is
# behind the injected source. Reuses the existing Resolver + Cost calculator verbatim.
# ═══════════════════════════════════════════════════════════════════════════════

import json
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
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.schemas.Schema__Bedrock__Chat__Turn       import Schema__Bedrock__Chat__Turn
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.schemas.List__Bedrock__Chat__Tool_Call    import List__Bedrock__Chat__Tool_Call
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.schemas.Schema__Bedrock__Chat__Tool_Call  import Schema__Bedrock__Chat__Tool_Call
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

        cost         = self.calc.estimate(model_id, in_tok, out_tok)
        request_body = {'modelId': model_id, 'messages': messages}                # the exact body the source sent (region is a client param, not body)
        if system:
            request_body['system'] = [{'text': system}]
        turn = Schema__Bedrock__Chat__Turn(model_id      = Safe_Str__Bedrock__Model_Id(model_id),
                                           input_tokens  = in_tok,
                                           output_tokens = out_tok,
                                           cost_usd      = cost,
                                           latency_ms    = latency,
                                           ts            = time.time(),
                                           request_json  = json.dumps(request_body, indent=2, ensure_ascii=False),
                                           response_text = response_text)
        session.turns.append(turn)
        session.total_input_tokens  += in_tok
        session.total_output_tokens += out_tok
        session.total_cost_usd      += cost
        session.turn_count          += 1
        return turn

    def send_turn_agentic(self, session, user_text, registry, center,                   # the Converse tool-use loop (C-TL1)
                          tool_config=None, name_map=None, grants=None, max_steps=6):
        model_id = self.resolve_model(session)
        session.messages.append(Schema__Bedrock__Chat__Message(role=Enum__Bedrock__Chat__Role.USER,
                                                               text=user_text, ts=time.time()))
        messages         = self.build_messages(session)
        system           = session.system_prompt or None
        name_map         = name_map or {}
        initial_messages = list(messages)                                               # captured for the Inspector

        total_in = total_out = total_latency = 0
        tool_cost   = 0.0
        model_calls = 0
        tool_calls  = 0
        final_text  = ''
        tool_log    = List__Bedrock__Chat__Tool_Call()                                   # per-tool detail for the Inspector

        for _ in range(max_steps):
            response = self.source.converse_turn(model_id, messages, region=session.region,
                                                system=system, tool_config=tool_config)
            model_calls   += 1
            total_in      += int(response.get('input_tokens',  0))
            total_out     += int(response.get('output_tokens', 0))
            total_latency += int(response.get('latency_ms',    0))
            content        = response.get('content', [])
            messages.append({'role': 'assistant', 'content': content})

            if response.get('stop_reason') != 'tool_use':                               # final answer — done
                final_text = self.text_of_content(content)
                break

            tool_result_blocks = []
            for block in content:                                                       # execute every requested tool
                tool_use = block.get('toolUse')
                if not tool_use:
                    continue
                tool_calls += 1
                slug, action = name_map.get(tool_use.get('name', ''), (None, None))
                if slug is None:
                    payload, status = {'error': f"unknown tool: {tool_use.get('name')}"}, 'error'
                else:
                    result    = center.execute(slug, action, tool_use.get('input', {}) or {}, grants=grants)
                    tool_cost += float(result.cost_usd)
                    payload   = result.json().get('data', {})
                    status    = 'success' if result.ok else 'error'
                tool_result_blocks.append({'toolResult': {'toolUseId': tool_use.get('toolUseId', ''),
                                                         'content'  : [{'json': payload}],
                                                         'status'   : status}})
                tool_log.append(Schema__Bedrock__Chat__Tool_Call(
                    name        = str(tool_use.get('name', '')),
                    input_json  = json.dumps(tool_use.get('input', {}) or {}, ensure_ascii=False, default=str),
                    status      = status,
                    result_json = json.dumps(payload, ensure_ascii=False, default=str)[:2000]))
            messages.append({'role': 'user', 'content': tool_result_blocks})            # feed results back

        session.messages.append(Schema__Bedrock__Chat__Message(role=Enum__Bedrock__Chat__Role.ASSISTANT,
                                                              text=final_text, ts=time.time()))
        cost         = self.calc.estimate(model_id, total_in, total_out) + tool_cost
        request_body = {'modelId': model_id, 'messages': initial_messages}
        if tool_config:
            request_body['toolConfig'] = tool_config
        if system:
            request_body['system'] = [{'text': system}]
        turn = Schema__Bedrock__Chat__Turn(model_id      = Safe_Str__Bedrock__Model_Id(model_id),
                                          input_tokens  = total_in,
                                          output_tokens = total_out,
                                          cost_usd      = cost,
                                          latency_ms    = total_latency,
                                          ts            = time.time(),
                                          request_json  = json.dumps(request_body, indent=2, ensure_ascii=False, default=str),
                                          response_text = final_text,
                                          model_calls   = model_calls,
                                          tool_calls    = tool_calls,
                                          tool_log      = tool_log)
        session.turns.append(turn)
        session.total_input_tokens  += total_in
        session.total_output_tokens += total_out
        session.total_cost_usd      += cost
        session.turn_count          += 1
        return turn

    def text_of_content(self, content: list) -> str:                                    # concat the text blocks of an assistant message
        return ''.join(block.get('text', '') for block in content if 'text' in block)
