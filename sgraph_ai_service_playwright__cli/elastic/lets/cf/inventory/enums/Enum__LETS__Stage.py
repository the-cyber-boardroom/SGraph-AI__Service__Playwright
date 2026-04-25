# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__LETS__Stage
# Stage of the LETS pipeline (Load / Extract / Transform / Save) plus an
# explicit INDEX value for the Elastic ingest step (not a LETS stage proper —
# Elasticsearch is NOT the source of truth, per the LETS doctrine §3).
# Used in operational events; the data index itself doesn't carry this field.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__LETS__Stage(str, Enum):
    LOAD      = 'load'                                                              # Retrieve raw source data; for slice 1 the bucket is the load layer
    EXTRACT   = 'extract'                                                           # Convert raw into structured records (Schema__S3__Object__Record)
    TRANSFORM = 'transform'                                                         # Aggregate / enrich / reduce — deferred to slice 2+
    SAVE      = 'save'                                                              # Persist immutable artifacts (manifest, screenshot) — deferred to slice 3
    INDEX     = 'index'                                                             # Bulk-post into Elastic; throwaway by design

    def __str__(self):
        return self.value
