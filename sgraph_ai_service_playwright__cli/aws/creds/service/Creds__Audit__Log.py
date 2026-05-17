# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/creds — Creds__Audit__Log
# Append-only JSONL audit log at ~/.sg/aws/creds/audit.jsonl (0600).
# Supports append, filtered query, and single-entry lookup.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import stat
from datetime import datetime, timezone, timedelta
from pathlib  import Path

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.creds.service.Creds__TTL__Parser import Creds__TTL__Parser


_DEFAULT_PATH = Path.home() / '.sg' / 'aws' / 'creds' / 'audit.jsonl'


class Creds__Audit__Log(Type_Safe):

    log_path : str = ''                                                         # overridable; empty means use _DEFAULT_PATH

    def _path(self) -> Path:
        return Path(self.log_path) if self.log_path else _DEFAULT_PATH

    def append(self, entry: dict):                                              # Appends one JSON line; creates file+dirs if absent
        p = self._path()
        p.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(entry, default=str)
        with p.open('a') as fh:
            fh.write(line + '\n')
        p.chmod(stat.S_IRUSR | stat.S_IWUSR)                                   # 0600 every write to be safe

    def query(self, caller: str = '', scope: str = '', since: str = '1h') -> list:
        p = self._path()
        if not p.exists():
            return []
        ttl_parser = Creds__TTL__Parser()
        cutoff_dt  = datetime.now(timezone.utc) - timedelta(seconds=ttl_parser.parse(since))
        results    = []
        with p.open() as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if caller and entry.get('caller', '') != caller:
                    continue
                if scope and entry.get('scope_name', '') != scope:
                    continue
                assumed_at_str = entry.get('assumed_at', '')
                if assumed_at_str:
                    try:
                        assumed_dt = datetime.fromisoformat(assumed_at_str)
                        if assumed_dt < cutoff_dt:
                            continue
                    except ValueError:
                        pass
                results.append(entry)
        return results

    def load_entry(self, assumption_id: str) -> dict | None:
        p = self._path()
        if not p.exists():
            return None
        with p.open() as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get('assumption_id') == assumption_id:
                    return entry
        return None
