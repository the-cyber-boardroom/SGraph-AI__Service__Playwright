# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: Bedrock__Chat__Card
# Pure: render a session as a plain-text ASCII card for the export action (OSC-52 /
# file). No Rich markup — meant to be copied into a note. Leads with the cost summary
# (the point of the tool) then the transcript. PURE — no Textual.
# ═══════════════════════════════════════════════════════════════════════════════

import datetime

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.bedrock_chat_tui__config               import CARD_WIDTH
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.enums.Enum__Bedrock__Chat__Role        import Enum__Bedrock__Chat__Role
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.schemas.Schema__Bedrock__Chat__Session import Schema__Bedrock__Chat__Session


class Bedrock__Chat__Card(Type_Safe):
    width : int = CARD_WIDTH

    def render(self, session: Schema__Bedrock__Chat__Session) -> str:
        W     = self.width
        lines = []

        def row(text=''):
            lines.append('│ ' + text[:W].ljust(W) + ' │')

        def rule(left, right):
            lines.append(left + '─' * (W + 2) + right)

        stamp = datetime.datetime.fromtimestamp(int(session.started_at or 0),
                                                datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        rule('┌', '┐')
        row(f'sg aws bedrock chat — {session.provider}/{session.model_alias}  [{session.region}]')
        row(stamp)
        rule('├', '┤')
        row(f'turns {session.turn_count}   tokens in {session.total_input_tokens} '
            f'out {session.total_output_tokens}')
        row(f'session cost  ${session.total_cost_usd:.6f}   budget ${session.budget_usd:.2f}')
        if session.context_label:
            row(f'context  {session.context_label}')
        rule('├', '┤')

        for m in session.messages:
            if m.role == Enum__Bedrock__Chat__Role.SYSTEM:
                continue
            who = 'you' if m.role == Enum__Bedrock__Chat__Role.USER else str(session.model_alias)
            row(f'{who}:')
            for chunk in self._wrap(m.text, W - 2):
                row('  ' + chunk)
            row('')
        rule('└', '┘')
        return '\n'.join(lines)

    def _wrap(self, text: str, width: int) -> list:
        out = []
        for paragraph in text.split('\n'):
            line = ''
            for word in paragraph.split(' '):
                if line and len(line) + 1 + len(word) > width:
                    out.append(line)
                    line = word
                else:
                    line = (line + ' ' + word).strip()
            out.append(line)
        return out or ['']
