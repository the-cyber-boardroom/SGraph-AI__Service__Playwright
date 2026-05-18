# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Audit__Log
# Append-only JSONL audit trail at ~/.sg/audit.jsonl.
# One JSON object per line; each line is a Schema__Audit__Event.
# Secrets MUST NOT appear in any audit line — caller is responsible.
#
# v0.2.28 additions:
#   - _ensure_file() creates path + sets mode 0600; warns on mode widening
#   - 50 MB rotation: audit.jsonl → audit.jsonl.1 before appending
#   - log() accepts full event fields; serialises all of them
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import sys
from datetime                                                                                   import datetime, timezone
from pathlib                                                                                    import Path

from osbot_utils.type_safe.Type_Safe                                                            import Type_Safe

from sgraph_ai_service_playwright__cli.credentials.enums.Enum__Audit__Action                   import Enum__Audit__Action
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Audit__Command_Args    import Safe_Str__Audit__Command_Args
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Aws__Arn               import Safe_Str__Aws__Arn
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Error__Message         import Safe_Str__Error__Message
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Iso8601_Timestamp      import Safe_Str__Iso8601_Timestamp
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Role__Name             import Safe_Str__Role__Name
from sgraph_ai_service_playwright__cli.credentials.primitives.Safe_Str__Sts__Session_Name      import Safe_Str__Sts__Session_Name
from sgraph_ai_service_playwright__cli.credentials.schemas.Schema__Audit__Event                import Schema__Audit__Event


DEFAULT_AUDIT_PATH  = Path.home() / '.sg' / 'audit.jsonl'
ROTATION_SIZE_BYTES = 50 * 1024 * 1024                              # 50 MB rotation threshold
REQUIRED_MODE       = 0o600


class Audit__Log(Type_Safe):
    audit_file  : str = ''                                          # override in tests; empty = use DEFAULT_AUDIT_PATH

    # ── path helpers ──────────────────────────────────────────────────────────

    def _path(self) -> Path:
        if self.audit_file:
            return Path(self.audit_file)
        return DEFAULT_AUDIT_PATH

    # ── file lifecycle ────────────────────────────────────────────────────────

    def _ensure_file(self, path: Path) -> None:                     # create file + enforce mode 0600
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.touch(mode=REQUIRED_MODE)
        try:
            current_mode = path.stat().st_mode & 0o777
            if current_mode != REQUIRED_MODE:
                os.chmod(path, REQUIRED_MODE)
                print(f'  \033[2m[audit] warning: mode widened on {path}; reset to 0600\033[0m',
                      file=sys.stderr)
        except OSError:
            pass

    def _rotate_if_needed(self, path: Path) -> None:                # single roll: audit.jsonl → audit.jsonl.1
        try:
            if path.exists() and path.stat().st_size >= ROTATION_SIZE_BYTES:
                rotated = path.with_suffix('.jsonl.1')
                if rotated.exists():
                    rotated.unlink()
                path.rename(rotated)
        except OSError:
            pass

    # ── setup ─────────────────────────────────────────────────────────────────

    def setup(self) -> 'Audit__Log':
        self._ensure_file(self._path())
        return self

    # ── log ───────────────────────────────────────────────────────────────────

    def log(self,
            action         : Enum__Audit__Action,
            role           : str  = '',
            identity_arn   : str  = '',
            session_id     : str  = '',
            session_expiry : str  = '',
            command_args   : str  = '',
            resolved_via   : list = None,
            duration_ms    : int  = 0,
            success        : bool = True,
            error          : str  = '') -> Schema__Audit__Event:
        path = self._path()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_file(path)
        self._rotate_if_needed(path)
        now   = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        event = Schema__Audit__Event(
            timestamp      = Safe_Str__Iso8601_Timestamp(now)               ,
            role           = Safe_Str__Role__Name(role)                      ,
            identity_arn   = Safe_Str__Aws__Arn(identity_arn)               ,
            session_id     = Safe_Str__Sts__Session_Name(session_id)        ,
            session_expiry = Safe_Str__Iso8601_Timestamp(session_expiry)    ,
            action         = action                                           ,
            command_args   = Safe_Str__Audit__Command_Args(command_args)    ,
            resolved_via   = list(resolved_via) if resolved_via else []     ,
            duration_ms    = max(0, int(duration_ms))                        ,
            success        = bool(success)                                   ,
            error          = Safe_Str__Error__Message(error)                ,
        )
        line = json.dumps({
            'timestamp'     : str(event.timestamp)     ,
            'role'          : str(event.role)           ,
            'identity_arn'  : str(event.identity_arn)  ,
            'session_id'    : str(event.session_id)    ,
            'session_expiry': str(event.session_expiry) ,
            'action'        : str(event.action)         ,
            'command_args'  : str(event.command_args)   ,
            'resolved_via'  : event.resolved_via        ,
            'duration_ms'   : event.duration_ms         ,
            'success'       : event.success             ,
            'error'         : str(event.error)          ,
        })
        try:
            with open(path, 'a', encoding='utf-8') as fh:
                fh.write(line + '\n')
        except OSError:
            pass                                                     # audit failure must never block the primary operation
        return event

    # ── read ──────────────────────────────────────────────────────────────────

    def read_all(self) -> list:                                      # list[dict] — raw JSON objects
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

    def tail(self, n: int = 20) -> list:                             # last n events, oldest first
        all_events = self.read_all()
        return all_events[-n:]
