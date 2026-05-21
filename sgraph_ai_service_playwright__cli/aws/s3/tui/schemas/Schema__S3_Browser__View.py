# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — s3 tui: Schema__S3_Browser__View
# One S3 object opened in the browser: a decoded text preview (gunzipped when the
# object is gzip), the detected format, and flags for binary / truncated content.
# Built by S3_Browser__Source. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__S3_Browser__View(Type_Safe):
    bucket     : str
    key        : str
    size_bytes : int  = 0                                                            # raw object size (bytes)
    fmt        : str                                                                 # detected format label (json/yaml/csv/text/binary/…)
    text       : str                                                                 # decoded preview (or a hex dump when binary)
    is_binary  : bool = False
    truncated  : bool = False
    gunzipped  : bool = False                                                         # object was .gz and was decompressed for the preview
