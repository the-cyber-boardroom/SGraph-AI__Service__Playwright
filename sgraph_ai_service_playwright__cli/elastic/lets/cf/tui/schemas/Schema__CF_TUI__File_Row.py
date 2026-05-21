# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: Schema__CF_TUI__File_Row
# One CloudFront-logs object as the file browser lists it: key, size, last-modified,
# and the Firehose-embedded delivery timestamp parsed from the filename. Listing-only
# metadata (no .gz content read) — mirrors the LETS inventory slice. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__CF_TUI__File_Row(Type_Safe):
    key           : str
    size_bytes    : int = 0
    last_modified : str                                                              # S3 LastModified (string form)
    delivery_iso  : str                                                              # Firehose timestamp from the filename, or '' if not Firehose-shaped
