# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — InMemory__Log__Sink
# List-backed sink for unit tests. No filesystem, no network. read_all() returns
# records ordered by the shared key layout so tests see the same order as FS/S3.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.sentinel.collections.List__Schema__Sentinel__Log_Record import List__Schema__Sentinel__Log_Record
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Log_Record           import Schema__Sentinel__Log_Record
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.Log__Sink                      import Log__Sink


class InMemory__Log__Sink(Log__Sink):
    records : List__Schema__Sentinel__Log_Record

    def write(self, record: Schema__Sentinel__Log_Record) -> str:
        self.records.append(record)
        return self.key_for(record)

    def read_all(self) -> List__Schema__Sentinel__Log_Record:
        ordered = sorted(self.records, key=lambda r: self.key_for(r))
        out     = List__Schema__Sentinel__Log_Record()
        for record in ordered:
            out.append(record)
        return out
