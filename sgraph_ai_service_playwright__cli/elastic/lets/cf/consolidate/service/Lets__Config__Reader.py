# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Lets__Config__Reader
# Parses raw JSON bytes (fetched from S3) into a Schema__Lets__Config and
# validates compat-region compatibility.  Pure logic — no I/O.
#
# Decision #5b: events load --from-consolidated calls check_compat() before
# reading any artefact from the region.  A mismatch on parser_version,
# output_schema, or output_schema_version is a hard rejection — the caller must
# create a new compat region rather than mixing toolchain generations.
#
# Two methods:
#   from_bytes(data)             → (Schema__Lets__Config, error_str)
#   check_compat(stored, current) → error_str  ('' = compatible)
# ═══════════════════════════════════════════════════════════════════════════════

import json
from typing                                                                         import Tuple

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.schemas.Schema__Lets__Config import Schema__Lets__Config


COMPAT_FIELDS = ('parser_version', 'output_schema', 'output_schema_version')       # Fields that break compat on change


class Lets__Config__Reader(Type_Safe):

    def from_bytes(self, data: bytes) -> Tuple[Schema__Lets__Config, str]:          # Parse raw JSON bytes into a config; return (config, '') or (empty, error)
        if not data:
            return Schema__Lets__Config(), 'empty data'
        try:
            d = json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return Schema__Lets__Config(), f'json parse error: {exc}'
        try:
            config = Schema__Lets__Config(**d)
        except Exception as exc:
            return Schema__Lets__Config(), f'schema error: {exc}'
        return config, ''

    def check_compat(self, stored  : Schema__Lets__Config ,
                           current : Schema__Lets__Config ,
                    ) -> str:                                                        # '' = compatible; non-empty = rejection reason
        errors = []
        stored_d  = stored.json()
        current_d = current.json()
        for field in COMPAT_FIELDS:
            sv = stored_d.get(field, '')
            cv = current_d.get(field, '')
            if sv and cv and sv != cv:                                               # Only compare when both sides are populated
                errors.append(f'{field}: stored={sv!r} current={cv!r}')
        return '; '.join(errors)
