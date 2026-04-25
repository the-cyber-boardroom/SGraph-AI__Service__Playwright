# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__LETS__Source__Slug
# Identifier for the data source the LETS pipeline pulled from. Stored on
# every Schema__S3__Object__Record so a single Elastic index can hold
# inventories from multiple sources without losing provenance.
# Slice 1 has one value; slice 5 (second source) will add more.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__LETS__Source__Slug(str, Enum):
    CF_REALTIME = 'cf-realtime'                                                     # CloudFront real-time logs delivered to S3 via Kinesis Data Firehose
    UNKNOWN     = 'unknown'                                                         # Defensive default; service rejects on persist

    def __str__(self):
        return self.value
