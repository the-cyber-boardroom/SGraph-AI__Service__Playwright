# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: Enum__CF_TUI__Source
# Which data source produced a traffic snapshot: in-memory (real CF log lines held
# in memory / read from a file — runs with no AWS) or s3 (the live Firehose-written
# cloudfront-realtime/ bucket, read-only).
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__CF_TUI__Source(str, Enum):
    IN_MEMORY = 'in-memory'
    S3        = 's3'

    def __str__(self):
        return self.value
