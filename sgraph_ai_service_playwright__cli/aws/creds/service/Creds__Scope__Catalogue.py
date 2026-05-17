# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/creds — Creds__Scope__Catalogue
# Local JSON catalogue stored at ~/.sg/aws/creds/scopes.json (0600).
# Maps scope names to role ARNs and max-TTL strings.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import stat
from datetime import datetime, timezone
from pathlib  import Path

from osbot_utils.type_safe.Type_Safe import Type_Safe


_DEFAULT_PATH = Path.home() / '.sg' / 'aws' / 'creds' / 'scopes.json'


class Creds__Scope__Catalogue(Type_Safe):

    catalogue_path : str = ''                                                   # overridable for tests; empty means use _DEFAULT_PATH

    def _path(self) -> Path:
        return Path(self.catalogue_path) if self.catalogue_path else _DEFAULT_PATH

    def load(self) -> dict:                                                     # Returns {'scopes': {name: {...}}}
        p = self._path()
        if not p.exists():
            return {'scopes': {}}
        with p.open() as fh:
            return json.load(fh)

    def save(self, data: dict):                                                 # Writes atomically; sets 0600 permissions
        p = self._path()
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix('.tmp')
        with tmp.open('w') as fh:
            json.dump(data, fh, indent=2)
        tmp.chmod(stat.S_IRUSR | stat.S_IWUSR)                                 # 0600 — owner read/write only
        tmp.rename(p)
        p.chmod(stat.S_IRUSR | stat.S_IWUSR)

    def scope_get(self, name: str) -> dict | None:
        data = self.load()
        return data.get('scopes', {}).get(name)

    def scope_add(self, name: str, role_arn: str, max_ttl: str = '1h') -> dict:
        data   = self.load()
        scopes = data.setdefault('scopes', {})
        entry  = {
            'name'       : name,
            'role_arn'   : role_arn,
            'max_ttl'    : max_ttl,
            'created_at' : datetime.now(timezone.utc).isoformat(),
        }
        scopes[name] = entry
        self.save(data)
        return entry

    def scope_remove(self, name: str) -> bool:
        data   = self.load()
        scopes = data.get('scopes', {})
        if name not in scopes:
            return False
        del scopes[name]
        self.save(data)
        return True

    def scope_list(self) -> list:                                               # Returns list of scope dicts, sorted by name
        data = self.load()
        return sorted(data.get('scopes', {}).values(), key=lambda s: s.get('name', ''))
