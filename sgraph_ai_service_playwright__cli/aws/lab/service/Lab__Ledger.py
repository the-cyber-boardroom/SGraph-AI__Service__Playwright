# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Lab__Ledger
# Append-only JSONL ledger on disk. Each line is one JSON-serialised
# Schema__Lab__Ledger__Entry. Uses an fcntl exclusive lock so concurrent
# writers don't corrupt the file. Default path: ~/.sg-lab/ledger.jsonl
# ═══════════════════════════════════════════════════════════════════════════════

import fcntl
import json
import os
from datetime  import datetime, timezone
from pathlib   import Path
from typing    import Optional

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.lab.enums.Enum__Lab__Entry__State          import Enum__Lab__Entry__State
from sgraph_ai_service_playwright__cli.aws.lab.enums.Enum__Lab__Resource_Type         import Enum__Lab__Resource_Type
from sgraph_ai_service_playwright__cli.aws.lab.primitives.Safe_Str__Lab__Entry_Id     import Safe_Str__Lab__Entry_Id
from sgraph_ai_service_playwright__cli.aws.lab.primitives.Safe_Str__Lab__Run_Id       import Safe_Str__Lab__Run_Id
from sgraph_ai_service_playwright__cli.aws.lab.schemas.Schema__Lab__Ledger__Entry     import Schema__Lab__Ledger__Entry
from sgraph_ai_service_playwright__cli.aws.lab.collections.List__Schema__Lab__Ledger__Entry import List__Schema__Lab__Ledger__Entry

_DEFAULT_LEDGER_PATH = Path.home() / '.sg-lab' / 'ledger.jsonl'
_DEFAULT_TTL_MINUTES = 60


class Lab__Ledger(Type_Safe):
    ledger_path : str = ''                                                         # empty → use default

    def setup(self) -> 'Lab__Ledger':
        path = Path(self.ledger_path) if self.ledger_path else _DEFAULT_LEDGER_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger_path = str(path)
        return self

    # ── write ─────────────────────────────────────────────────────────────────

    def append(self, entry: Schema__Lab__Ledger__Entry) -> None:
        path = Path(self.ledger_path) if self.ledger_path else _DEFAULT_LEDGER_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'a') as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                fh.write(json.dumps(self._entry_to_dict(entry)) + '\n')
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)

    def update_state(self, entry_id: str, new_state: Enum__Lab__Entry__State) -> bool:
        entries = self.all_entries()
        updated = False
        for entry in entries:
            if str(entry.entry_id) == entry_id:
                entry.state = new_state
                updated = True
        if updated:
            self._rewrite_all(entries)
        return updated

    # ── read ──────────────────────────────────────────────────────────────────

    def all_entries(self) -> List__Schema__Lab__Ledger__Entry:
        path = Path(self.ledger_path) if self.ledger_path else _DEFAULT_LEDGER_PATH
        result = List__Schema__Lab__Ledger__Entry()
        if not path.exists():
            return result
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data  = json.loads(line)
                entry = self._dict_to_entry(data)
                result.append(entry)
            except (json.JSONDecodeError, Exception):
                continue                                                            # skip corrupted lines (partial-write recovery)
        return result

    def entries_for_run(self, run_id: str) -> List__Schema__Lab__Ledger__Entry:
        return List__Schema__Lab__Ledger__Entry(
            [e for e in self.all_entries() if str(e.run_id) == run_id]
        )

    def pending_entries(self) -> List__Schema__Lab__Ledger__Entry:
        return List__Schema__Lab__Ledger__Entry(
            [e for e in self.all_entries() if e.state == Enum__Lab__Entry__State.PENDING]
        )

    # ── helpers ───────────────────────────────────────────────────────────────

    def _entry_to_dict(self, entry: Schema__Lab__Ledger__Entry) -> dict:
        return {
            'entry_id'      : str(entry.entry_id),
            'run_id'        : str(entry.run_id),
            'resource_type' : entry.resource_type.value if entry.resource_type else '',
            'resource_id'   : str(entry.resource_id),
            'region'        : str(entry.region),
            'created_at'    : entry.created_at,
            'expires_at'    : entry.expires_at,
            'state'         : entry.state.value if entry.state else '',
            'experiment'    : entry.experiment,
            'extra'         : entry.extra,
        }

    def _dict_to_entry(self, data: dict) -> Schema__Lab__Ledger__Entry:
        from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__ARN    import Safe_Str__AWS__ARN
        from sgraph_ai_service_playwright__cli.aws._shared.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region
        return Schema__Lab__Ledger__Entry(
            entry_id      = Safe_Str__Lab__Entry_Id(data.get('entry_id', '')),
            run_id        = Safe_Str__Lab__Run_Id(data.get('run_id', '')),
            resource_type = Enum__Lab__Resource_Type(data.get('resource_type', 'r53-record')),
            resource_id   = Safe_Str__AWS__ARN(data.get('resource_id', '')),
            region        = Safe_Str__AWS__Region(data.get('region', '')),
            created_at    = data.get('created_at', ''),
            expires_at    = data.get('expires_at', ''),
            state         = Enum__Lab__Entry__State(data.get('state', 'pending')),
            experiment    = data.get('experiment', ''),
            extra         = data.get('extra', ''),
        )

    def _rewrite_all(self, entries: List__Schema__Lab__Ledger__Entry) -> None:
        path = Path(self.ledger_path) if self.ledger_path else _DEFAULT_LEDGER_PATH
        with open(path, 'w') as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                for entry in entries:
                    fh.write(json.dumps(self._entry_to_dict(entry)) + '\n')
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)
