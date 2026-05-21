# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: Bedrock__Chat__Brief__Builder
# Pure: turn a chat session (+ the context it was seeded with) into a dev-brief
# markdown string for the coding agents — the "talk to the data → capture idea →
# action plan" payoff. No LLM call here (that is an optional, separately-costed turn
# the screen can run first); this assembles a brief from whatever is in the session.
# PURE — no Textual, no boto3, no disk I/O (the caller writes via the capture writer).
# ═══════════════════════════════════════════════════════════════════════════════

import datetime

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.enums.Enum__Bedrock__Chat__Role        import Enum__Bedrock__Chat__Role
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.schemas.Schema__Bedrock__Chat__Session import Schema__Bedrock__Chat__Session


class Bedrock__Chat__Brief__Builder(Type_Safe):

    def build(self, session: Schema__Bedrock__Chat__Session, title: str = '') -> str:
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        title = title or self.default_title(session)
        lines = [f'# Dev brief — {title}',
                 '',
                 f'> Captured from `sg aws bedrock chat` ({session.provider}/{session.model_alias}) '
                 f'at {stamp}.',
                 f'> Session cost ${session.total_cost_usd:.6f} over {session.turn_count} turns '
                 f'(in {session.total_input_tokens} / out {session.total_output_tokens} tokens).',
                 '']
        if session.context_label:
            lines += ['## Context (seeded)', '', session.context_label, '']
        lines += ['## Conversation', '']
        for m in session.messages:
            if m.role == Enum__Bedrock__Chat__Role.SYSTEM:
                continue
            who = 'You' if m.role == Enum__Bedrock__Chat__Role.USER else session.model_alias
            lines += [f'**{who}:** {m.text}', '']
        lines += ['## Proposed actions', '',
                  '- [ ] (review the conversation above and turn findings into concrete tasks)',
                  '']
        return '\n'.join(lines)

    def default_title(self, session: Schema__Bedrock__Chat__Session) -> str:
        for m in session.messages:                                                # first user line, trimmed
            if m.role == Enum__Bedrock__Chat__Role.USER and m.text.strip():
                first = m.text.strip().split('\n')[0]
                return first[:60]
        return 'bedrock chat session'
