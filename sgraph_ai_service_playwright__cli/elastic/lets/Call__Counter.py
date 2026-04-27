# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Call__Counter
# Cross-cutting utility for the LETS pipelines: counts external HTTP calls
# made during a single run, broken down by destination.
#
# Two categories tracked today:
#   - s3_calls       boto3 S3 calls (ListObjectsV2 paginator iterations + GetObject)
#   - elastic_calls  Inventory__HTTP__Client.request() calls (search, _bulk,
#                    _update_by_query, _cat/indices, DELETE, _count, ...)
#
# Used by:
#   - S3__Inventory__Lister.paginate         (one per page)
#   - S3__Object__Fetcher.get_object_bytes   (one per file)
#   - Inventory__HTTP__Client.request        (one per HTTP call)
#   - SG_Send__Orchestrator                  (constructs ONE counter, injects
#                                              into every collaborator so the
#                                              final tallies span the whole run)
#
# Existing tests construct each class with its own auto-instantiated counter
# (the Type_Safe default).  They simply ignore it.  The orchestrator shares
# a single counter across all collaborators by injecting the same instance.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


class Call__Counter(Type_Safe):
    s3_calls      : int = 0
    elastic_calls : int = 0

    def s3(self):                                                                   # Increment S3 call count by 1
        self.s3_calls += 1

    def elastic(self):                                                              # Increment Elastic HTTP call count by 1
        self.elastic_calls += 1

    def reset(self):
        self.s3_calls      = 0
        self.elastic_calls = 0

    def total(self) -> int:                                                         # Sum of both — useful for "did anything happen?" checks
        return self.s3_calls + self.elastic_calls
