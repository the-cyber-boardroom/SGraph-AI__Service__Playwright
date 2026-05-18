# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Credentials — Edit__Session__Journal
#
# Records edit sessions to ~/.sg/edit-sessions/<session_id>.json.
# Enables orphan detection when a previous editor exited uncleanly.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from datetime   import datetime, timezone
from pathlib    import Path

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Edit__Session__Journal(Type_Safe):

    journal_dir: str = ''                                                        # default: ~/.sg/edit-sessions

    def dir(self) -> Path:
        if self.journal_dir:
            return Path(self.journal_dir)
        return Path.home() / '.sg' / 'edit-sessions'

    def session_path(self, session_id: str) -> Path:
        return self.dir() / f'{session_id}.json'

    def create(self, session_id: str, temp_path: str) -> None:
        d = self.dir()
        d.mkdir(parents=True, exist_ok=True)
        entry = {'session_id': session_id                              ,
                 'started_at': datetime.now(timezone.utc).isoformat() ,
                 'status'    : 'projecting'                            ,
                 'temp_path' : temp_path                               }
        self.session_path(session_id).write_text(json.dumps(entry))

    def update_status(self, session_id: str, status: str) -> None:
        p = self.session_path(session_id)
        if not p.exists():
            return
        entry          = json.loads(p.read_text())
        entry['status'] = status
        p.write_text(json.dumps(entry))

    def find_orphans(self) -> list:                                              # entries where status != 'completed'/'discarded'
        d = self.dir()
        if not d.exists():
            return []
        orphans = []
        for f in sorted(d.glob('*.json')):
            try:
                entry = json.loads(f.read_text())
                if entry.get('status') not in ('completed', 'discarded'):
                    orphans.append(entry)
            except (ValueError, OSError):
                pass
        return orphans

    def discard(self, session_id: str) -> None:
        self.update_status(session_id, 'discarded')
