# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Kibana__Export__Result
# Result of POST /api/saved_objects/_export, after the service has persisted
# the ndjson to disk. Schemas don't hold raw bytes — the file path + object
# count + http status are what the CLI prints; the actual file is on disk.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.files.safe_str.Safe_Str__File__Path   import Safe_Str__File__Path

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Diagnostic      import Safe_Str__Diagnostic


class Schema__Kibana__Export__Result(Type_Safe):
    object_count : int                  = 0
    bytes_written: int                  = 0
    file_path    : Safe_Str__File__Path                                             # Where the ndjson was written; empty if export failed before disk write
    http_status  : int                  = 0
    error        : Safe_Str__Diagnostic
