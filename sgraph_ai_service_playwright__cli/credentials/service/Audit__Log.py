# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Audit__Log
# Append-only JSONL audit trail at ~/.sg/audit.jsonl.
# One JSON object per line; each line is a Schema__Audit__Event.
# Secrets MUST NOT appear in any audit line — caller is responsible.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from datetime                                                                                   import datetime, timezone
from pathlib                                                                                    import Path

from osbot_utils.type_safe.Type_Safe                                                            import Type_Safe

from sgraph_ai_service_playwright__cli.credentials.enums.Enum__Audit__Action                   import Enum__Audit__Action
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Audit__Detail          import Safe_Str__Audit__Detail
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Role__Name             import Safe_Str__Role__Name
from sgraph_ai_service_playwright__cli.credentials.schemas.Schema__Audit__Event                import Schema__Audit__Event
from sgraph_ai_service_playwright__cli.vault.primitives.Safe_Str__ISO_Datetime                  import Safe_Str__ISO_Datetime


DEFAULT_AUDIT_PATH = Path.home() / '.sg' / 'audit.jsonl'


class Audit__Log(Type_Safe):
    audit_file  : str = ''                                          # override in tests; empty = use DEFAULT_AUDIT_PATH

    def _path(self) -> Path:
        if self.audit_file:
            return Path(self.audit_file)
        return DEFAULT_AUDIT_PATH

    def setup(self) -> 'Audit__Log':
        self._path().parent.mkdir(parents=True, exist_ok=True)
        return self

    def log(self, action: Enum__Audit__Action, role: str = '', detail: str = '') -> Schema__Audit__Event:
        path   = self._path()
        path.parent.mkdir(parents=True, exist_ok=True)
        now    = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        event  = Schema__Audit__Event(
            timestamp = Safe_Str__ISO_Datetime(now),
            action    = action                      ,
            role      = Safe_Str__Role__Name(role)  ,
            detail    = Safe_Str__Audit__Detail(detail),
        )
        line = json.dumps({'timestamp': str(event.timestamp),
                           'action'   : str(event.action)   ,
                           'role'     : str(event.role)     ,
                           'detail'   : str(event.detail)   })
        try:
            with open(path, 'a', encoding='utf-8') as fh:
                fh.write(line + '\n')
        except OSError:
            pass                                                    # audit failure must never block the primary operation
        return event

    def read_all(self) -> list:                                     # list[dict] — raw JSON objects
        path = self._path()
        if not path.exists():
            return []
        events = []
        try:
            with open(path, encoding='utf-8') as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        try:
                            events.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except OSError:
            pass
        return events

    def tail(self, n: int = 20) -> list:                            # last n events, oldest first
        all_events = self.read_all()
        return all_events[-n:]
