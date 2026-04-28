# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Lets__Config__Writer
# Serialises a Schema__Lets__Config to JSON bytes for upload to S3.
# Written at compat-region root on first use of a region.  Pure logic — no I/O.
# Caller hands bytes to S3__Object__Writer.
#
# Decision #5: one lets-config.json per compat-region folder.  Stable toolchain
# = same file for the life of the region.  Parser/schema breaks → new region.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.schemas.Schema__Lets__Config import Schema__Lets__Config


class Lets__Config__Writer(Type_Safe):

    def to_bytes(self, config: Schema__Lets__Config) -> bytes:                      # Serialize config to JSON bytes (UTF-8, pretty-printed for human readability)
        payload = config.json()
        return json.dumps(payload, indent=2, sort_keys=True).encode('utf-8')
