# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate — Vault_App__Fargate__Timings__Store
# Append-only JSONL store for per-start timing records.
# Default path: ~/.cache/sg/vault-app-fargate/timings.jsonl
# path is injectable so tests can write to a temp dir.
# ═══════════════════════════════════════════════════════════════════════════════

import json
from pathlib import Path

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_app.fargate.schemas.Schema__VAF__Timings__Record import Schema__VAF__Timings__Record


class Vault_App__Fargate__Timings__Store(Type_Safe):
    path : str = ''                                                               # default resolved via _get_path()

    def _default_path(self) -> str:                                              # ~/.cache/sg/vault-app-fargate/timings.jsonl
        return str(Path.home() / '.cache' / 'sg' / 'vault-app-fargate' / 'timings.jsonl')

    def _get_path(self) -> str:                                                  # use injected path or fall back to default
        return self.path or self._default_path()

    def append(self, record: Schema__VAF__Timings__Record) -> None:              # write one JSON line; creates parent dirs as needed
        file_path = Path(self._get_path())
        file_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record.json()) + '\n'
        with file_path.open('a', encoding='utf-8') as fh:
            fh.write(line)

    def last(self, n: int = 10) -> list:                                         # return last n records; [] if file absent
        file_path = Path(self._get_path())
        if not file_path.exists():
            return []
        lines = file_path.read_text(encoding='utf-8').splitlines()
        tail  = lines[-n:] if len(lines) > n else lines
        result = []
        for line in tail:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                result.append(Schema__VAF__Timings__Record(**data))
            except (json.JSONDecodeError, TypeError):
                pass                                                              # skip malformed lines gracefully
        return result

    def clear(self) -> None:                                                     # delete the file if it exists
        file_path = Path(self._get_path())
        if file_path.exists():
            file_path.unlink()
