# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Local_FS__Log__Sink
# Filesystem sink, one JSON object per record under the shared key layout
# (<root>/<prefix>/YYYY/MM/DD/HH/<request_id>.json). Mirrors the S3 key layout so
# `trace`/replay behave identically local vs AWS.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os

from sgraph_ai_service_playwright__cli.sentinel.collections.List__Schema__Sentinel__Log_Record import List__Schema__Sentinel__Log_Record
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Log_Record           import Schema__Sentinel__Log_Record
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.Log__Sink                      import Log__Sink


class Local_FS__Log__Sink(Log__Sink):
    root_dir : str = ''                                                             # filesystem path — plain str (Safe_Str would mangle '/' '.' '-' → '_')

    def write(self, record: Schema__Sentinel__Log_Record) -> str:
        key  = self.key_for(record)
        path = os.path.join(self.root_dir, key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as fh:
            json.dump(record.json(), fh, indent=2)
        return key

    def read_all(self) -> List__Schema__Sentinel__Log_Record:
        root    = self.root_dir
        records = List__Schema__Sentinel__Log_Record()
        if not os.path.isdir(root):
            return records
        paths = []
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                if name.endswith('.json'):
                    paths.append(os.path.join(dirpath, name))
        for path in sorted(paths):
            with open(path, 'r') as fh:
                records.append(Schema__Sentinel__Log_Record.from_json(json.load(fh)))
        return records
