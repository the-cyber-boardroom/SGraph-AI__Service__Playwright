# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__CF__Method
# HTTP method on the CloudFront request (cs_method TSV column).
# Pinned to the common verbs the realtime log emits; OTHER catches anything
# unusual (PROPFIND, MKCOL, etc.) without crashing the parser.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__CF__Method(str, Enum):
    GET     = 'GET'
    POST    = 'POST'
    PUT     = 'PUT'
    DELETE  = 'DELETE'
    HEAD    = 'HEAD'
    OPTIONS = 'OPTIONS'
    PATCH   = 'PATCH'
    OTHER   = 'OTHER'

    def __str__(self):
        return self.value
