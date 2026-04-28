# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — NDJSON__Writer
# Converts a list of Schema__CF__Event__Record objects to gzip-compressed NDJSON
# bytes.  One JSON object per line, then gzip.  Pure logic — no I/O.
# Caller is responsible for writing bytes to S3 via S3__Object__Writer.
#
# Decision #5: the consolidated artefact is a single events.ndjson.gz per day.
# This class is the serialisation half; NDJSON__Reader is the deserialisation
# half.  Both are stateless and have no external dependencies.
# ═══════════════════════════════════════════════════════════════════════════════

import gzip
import json

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.collections.List__Schema__CF__Event__Record import List__Schema__CF__Event__Record


class NDJSON__Writer(Type_Safe):

    def records_to_bytes(self, records: List__Schema__CF__Event__Record) -> bytes:  # Serialize to gzip-compressed NDJSON
        lines      = [json.dumps(rec.json(), separators=(',', ':')) for rec in records]
        ndjson_raw = '\n'.join(lines)
        if ndjson_raw:
            ndjson_raw += '\n'
        return gzip.compress(ndjson_raw.encode('utf-8'))
