# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI observe — Observe__Session__Writer
# Writes captured observe sessions to ~/.sg/aws/observe/sessions/ as JSONL.
# Each file is chmod 0600 (owner read/write only).
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import stat
import time
from pathlib import Path

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Observe__Session__Writer(Type_Safe):
    sessions_dir : str = ''                                             # overridable in tests

    def base_dir(self) -> Path:
        if self.sessions_dir:
            return Path(self.sessions_dir)
        return Path.home() / '.sg' / 'aws' / 'observe' / 'sessions'

    def write(self, session_id: str, events: list) -> str:              # returns written file path
        base = self.base_dir()
        base.mkdir(parents=True, exist_ok=True)
        filename  = f'{session_id}.jsonl'
        file_path = base / filename
        with open(file_path, 'w') as fh:
            for ev in events:
                if hasattr(ev, 'json'):
                    line = ev.json()
                elif isinstance(ev, dict):
                    line = json.dumps(ev)
                else:
                    line = json.dumps({'event': str(ev)})
                fh.write(line + '\n')
        os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)               # 0600 — owner only
        return str(file_path)

    def read(self, session_file: str) -> list:                          # JSONL → list[dict]
        path = Path(session_file)
        if not path.exists():
            return []
        events = []
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return events

    def list_sessions(self) -> list:                                    # list[str] of .jsonl paths
        base = self.base_dir()
        if not base.exists():
            return []
        return sorted(str(p) for p in base.glob('*.jsonl'))
