# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/chat: Chat__Engine (neutral, backend-agnostic)
# The promoted, provider-neutral engine (plan 07). Speaks only neutral messages /
# tools / content; the injected Chat__Backend adapts to its wire format. Keeps both
# paths: send_turn (streaming chat) and send_turn_agentic (the tool loop — neutral
# tool_use/tool_result, routed through the TUI API execution center, honest on failure).
# Cost is the backend's (the model catalogue is backend-specific). No Textual, no AWS.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import time
import uuid

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.tui.chat.backend.Chat__Backend             import Chat__Backend
from sgraph_ai_service_playwright__cli.tui.chat.enums.Enum__Chat__Role            import Enum__Chat__Role
from sgraph_ai_service_playwright__cli.tui.chat.schemas.List__Chat__Message       import List__Chat__Message
from sgraph_ai_service_playwright__cli.tui.chat.schemas.List__Chat__Tool_Call     import List__Chat__Tool_Call
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Content     import Schema__Chat__Content
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Message     import Schema__Chat__Message
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Session     import Schema__Chat__Session
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Tool_Call   import Schema__Chat__Tool_Call
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Tool_Result import Schema__Chat__Tool_Result
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Turn        import Schema__Chat__Turn
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Usage       import Schema__Chat__Usage


class Chat__Engine(Type_Safe):
    backend : Chat__Backend

    def new_session(self, model_id: str = '', budget_usd: float = 0.50,
                    system: str = '', context_label: str = '') -> Schema__Chat__Session:
        return Schema__Chat__Session(session_id=uuid.uuid4().hex, backend_id=self.backend.id(),
                                    model_id=model_id, started_at=time.time(), budget_usd=budget_usd,
                                    system_prompt=system, context_label=context_label)

    def build_messages(self, session: Schema__Chat__Session) -> List__Chat__Message:
        messages = List__Chat__Message()                                          # non-system messages; system goes separately
        for message in session.messages:
            if message.role != Enum__Chat__Role.SYSTEM:
                messages.append(message)
        return messages

    def user_message(self, text: str, documents=None) -> Schema__Chat__Message:
        message = Schema__Chat__Message(role=Enum__Chat__Role.USER)
        message.content.append(Schema__Chat__Content(text=text))
        for document in documents or []:
            message.content.append(Schema__Chat__Content(document=document))
        return message

    def text_of(self, content) -> str:
        return ''.join(block.text for block in content if block.tool_use is None
                                                       and block.tool_result is None and block.text)

    # ── streaming chat ────────────────────────────────────────────────────────────

    def send_turn(self, session: Schema__Chat__Session, text: str,
                  documents=None, on_delta=None) -> Schema__Chat__Turn:
        session.messages.append(self.user_message(text, documents))
        messages = self.build_messages(session)
        system   = session.system_prompt or None

        parts = []
        usage = Schema__Chat__Usage()
        for kind, payload in self.backend.stream_turn(session.model_id, messages, system=system):
            if kind == 'delta':
                parts.append(payload)
                if on_delta is not None:
                    on_delta(payload)
            elif kind == 'usage':
                usage = payload

        response_text = ''.join(parts)
        assistant = Schema__Chat__Message(role=Enum__Chat__Role.ASSISTANT)
        assistant.content.append(Schema__Chat__Content(text=response_text))
        session.messages.append(assistant)

        cost = self.backend.cost(session.model_id, usage)
        turn = Schema__Chat__Turn(model_id=session.model_id, input_tokens=usage.input_tokens,
                                 output_tokens=usage.output_tokens, cost_usd=cost, latency_ms=usage.latency_ms,
                                 ts=time.time(), response_text=response_text, model_calls=1, tool_calls=0,
                                 estimated=usage.estimated,
                                 request_json=self.request_json(session.model_id, messages, system, None))
        return self.record(session, turn)

    # ── agentic tool loop (neutral) ────────────────────────────────────────────────

    def send_turn_agentic(self, session: Schema__Chat__Session, text: str, center,
                          tools, name_map, grants=None, documents=None, max_steps: int = 6) -> Schema__Chat__Turn:
        session.messages.append(self.user_message(text, documents))
        messages = self.build_messages(session)
        system   = session.system_prompt or None
        name_map = name_map or {}

        total_in = total_out = total_latency = 0
        tool_cost   = 0.0
        model_calls = 0
        tool_calls  = 0
        estimated   = False
        final_text  = ''
        tool_log    = List__Chat__Tool_Call()
        request_json = self.request_json(session.model_id, messages, system, tools)

        for _ in range(max_steps):
            result = self.backend.converse(session.model_id, messages, system=system, tools=tools)
            model_calls   += 1
            total_in      += result.usage.input_tokens
            total_out     += result.usage.output_tokens
            total_latency += result.usage.latency_ms
            estimated      = estimated or result.usage.estimated

            assistant = Schema__Chat__Message(role=Enum__Chat__Role.ASSISTANT)
            for block in result.content:
                assistant.content.append(block)
            messages.append(assistant)

            if result.stop_reason != 'tool_use':
                final_text = self.text_of(result.content)
                break

            tool_message = Schema__Chat__Message(role=Enum__Chat__Role.USER)
            for block in result.content:
                if block.tool_use is None:
                    continue
                tool_use     = block.tool_use
                tool_calls  += 1
                slug, action = name_map.get(str(tool_use.name), (None, None))
                if slug is None:
                    data, status = {'error': f'unknown tool: {tool_use.name}'}, 'error'
                else:
                    result_obj = center.execute(slug, action, dict(tool_use.input), grants=grants)
                    tool_cost += float(result_obj.cost_usd)
                    if result_obj.ok:
                        data, status = result_obj.json().get('data', {}), 'success'
                    else:                                                         # gated / failed — tell the model the truth
                        data   = {'error': result_obj.error, 'dry_run': result_obj.dry_run, 'preview': result_obj.preview}
                        status = 'error'
                tool_message.content.append(Schema__Chat__Content(
                    tool_result=Schema__Chat__Tool_Result(id=str(tool_use.id), status=status, data=data)))
                tool_log.append(Schema__Chat__Tool_Call(name=str(tool_use.name),
                                                       input_json=json.dumps(dict(tool_use.input), default=str),
                                                       status=status,
                                                       result_json=json.dumps(data, default=str)[:2000]))
            messages.append(tool_message)

        assistant_final = Schema__Chat__Message(role=Enum__Chat__Role.ASSISTANT)
        assistant_final.content.append(Schema__Chat__Content(text=final_text))
        session.messages.append(assistant_final)

        usage = Schema__Chat__Usage(input_tokens=total_in, output_tokens=total_out,
                                   latency_ms=total_latency, estimated=estimated)
        cost  = self.backend.cost(session.model_id, usage) + tool_cost
        turn  = Schema__Chat__Turn(model_id=session.model_id, input_tokens=total_in, output_tokens=total_out,
                                  cost_usd=cost, latency_ms=total_latency, ts=time.time(), response_text=final_text,
                                  model_calls=model_calls, tool_calls=tool_calls, tool_log=tool_log,
                                  estimated=estimated, request_json=request_json)
        return self.record(session, turn)

    # ── helpers ────────────────────────────────────────────────────────────────────

    def record(self, session: Schema__Chat__Session, turn: Schema__Chat__Turn) -> Schema__Chat__Turn:
        session.turns.append(turn)
        session.total_input_tokens  += turn.input_tokens
        session.total_output_tokens += turn.output_tokens
        session.total_cost_usd      += turn.cost_usd
        session.turn_count          += 1
        return turn

    def request_json(self, model_id: str, messages, system, tools) -> str:
        body = {'model_id': model_id, 'system': system, 'messages': [self.message_display(m) for m in messages]}
        if tools:
            body['tools'] = [str(tool.name) for tool in tools]
        return json.dumps(body, indent=2, ensure_ascii=False, default=str)

    def message_display(self, message: Schema__Chat__Message) -> dict:            # readable, base64-free, for the Inspector
        blocks = []
        for block in message.content:
            if   block.tool_use    is not None: blocks.append({'tool_use'   : {'name': str(block.tool_use.name), 'input': dict(block.tool_use.input)}})
            elif block.tool_result is not None: blocks.append({'tool_result': {'status': block.tool_result.status, 'data': dict(block.tool_result.data)}})
            elif block.document    is not None: blocks.append({'document'   : f'{block.document.name} ({block.document.size}B)'})
            elif block.text                   : blocks.append({'text': block.text})
        return {'role': str(message.role), 'content': blocks}
