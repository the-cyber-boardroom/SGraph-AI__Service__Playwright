# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — NDJSON__Reader
# Deserialises gzip-compressed NDJSON bytes back into a typed
# List__Schema__CF__Event__Record.  Pure logic — no I/O.
# Caller is responsible for fetching bytes from S3 via S3__Object__Fetcher.
#
# Paired with NDJSON__Writer.  Empty lines are silently skipped (tolerant of
# trailing newlines produced by Writer).  An empty or all-whitespace input
# returns an empty list rather than raising.
# ═══════════════════════════════════════════════════════════════════════════════

import gzip
import json

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.collections.List__Schema__CF__Event__Record import List__Schema__CF__Event__Record
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.schemas.Schema__CF__Event__Record            import Schema__CF__Event__Record


class NDJSON__Reader(Type_Safe):

    def bytes_to_records(self, data: bytes) -> List__Schema__CF__Event__Record:     # Gunzip + parse NDJSON → typed list
        result = List__Schema__CF__Event__Record()
        if not data:
            return result
        try:
            text = gzip.decompress(data).decode('utf-8')
        except (OSError, UnicodeDecodeError):
            return result
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                result.append(Schema__CF__Event__Record(**d))
            except (json.JSONDecodeError, Exception):
                continue
        return result
