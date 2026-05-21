# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — s3 tui: Schema__S3_Browser__Entry
# One row in the S3 browser: a bucket, a folder (common prefix), or a file (object).
# `path` is the bucket name / child prefix / full key respectively. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__S3_Browser__Entry(Type_Safe):
    name          : str
    kind          : str                                                              # bucket | folder | file
    bucket        : str
    path          : str                                                              # bucket name / child prefix / full key
    size_bytes    : int = 0
    last_modified : str
