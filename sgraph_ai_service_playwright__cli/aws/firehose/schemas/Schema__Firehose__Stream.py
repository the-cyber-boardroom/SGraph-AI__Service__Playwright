# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — firehose: Schema__Firehose__Stream
# One Amazon Data Firehose delivery stream as the read-only commands surface it,
# including the resolved S3 destination (bucket + prefix) — which is the hop that
# lets the CF architecture view confirm Firehose → S3 wiring. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Firehose__Stream(Type_Safe):
    name               : str
    status             : str                                                         # CREATING | ACTIVE | DELETING | …
    stream_type        : str                                                         # DirectPut | KinesisStreamAsSource
    created            : str
    destination_bucket : str                                                         # resolved from the S3 destination ARN
    destination_prefix : str
    arn                : str
