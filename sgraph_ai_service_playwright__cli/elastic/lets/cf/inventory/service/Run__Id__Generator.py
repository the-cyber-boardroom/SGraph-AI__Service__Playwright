# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Run__Id__Generator
# Builds pipeline run ids of the form
#   "{utc-compact-iso}-{source-slug}-{verb}-{shortsha}"
# e.g. "20260425T103042Z-cf-realtime-load-a3f2"
# The compact ISO + 4-hex-char short sha give us second-level uniqueness with
# fixed-width sortability. now_iso() and short_sha() are seams — tests
# override them for deterministic ids.
# ═══════════════════════════════════════════════════════════════════════════════

import secrets
from datetime                                                                       import datetime, timezone

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.type_safe_core.decorators.type_safe                      import type_safe


class Run__Id__Generator(Type_Safe):

    def now_iso(self) -> str:                                                       # Compact ISO-8601 UTC: "YYYYMMDDTHHMMSSZ"
        return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')

    def short_sha(self) -> str:                                                     # 4 hex chars from urandom — sufficient for within-second uniqueness
        return secrets.token_hex(2)

    @type_safe
    def generate(self, source: str ,                                                # Enum value (e.g. "cf-realtime"); kept as plain str for caller flexibility
                       verb   : str                                                 # e.g. "load", "wipe"
                  ) -> str:
        return f'{self.now_iso()}-{source}-{verb}-{self.short_sha()}'
