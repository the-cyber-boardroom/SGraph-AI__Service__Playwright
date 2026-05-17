# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI _shared — Aws__Tagger
# Builds the canonical sg:* tag set applied to every create_* call.
# Five mandatory tags + optional sg:session-id (for observability correlation).
# ═══════════════════════════════════════════════════════════════════════════════

import os
import socket
from datetime import datetime, timezone

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.enums.Enum__AWS__Surface          import Enum__AWS__Surface
from sgraph_ai_service_playwright__cli.aws._shared.schemas.Schema__AWS__Tag          import Schema__AWS__Tag
from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Tag_Key   import Safe_Str__AWS__Tag_Key
from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Tag_Value import Safe_Str__AWS__Tag_Value


class Aws__Tagger(Type_Safe):

    def tags_for(self, surface: Enum__AWS__Surface, verb: str, session_id: str = '') -> list:
        tags = [
            self._tag('sg:managed-by',  'sg-cli'),
            self._tag('sg:surface',     surface.value if surface else ''),
            self._tag('sg:verb',        verb),
            self._tag('sg:created-by',  os.environ.get('USER', socket.gethostname())),
            self._tag('sg:created-at',  datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')),
        ]
        if session_id:
            tags.append(self._tag('sg:session-id', session_id))
        return tags

    def as_boto3_tags(self, surface: Enum__AWS__Surface, verb: str, session_id: str = '') -> list:
        return [{'Key': str(t.key), 'Value': str(t.value)} for t in self.tags_for(surface, verb, session_id)]

    def _tag(self, key: str, value: str) -> Schema__AWS__Tag:
        return Schema__AWS__Tag(key   = Safe_Str__AWS__Tag_Key(key),
                                value = Safe_Str__AWS__Tag_Value(value))
