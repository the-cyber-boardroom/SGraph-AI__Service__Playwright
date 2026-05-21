# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: CF_TUI__File_Builder
# PURE: one CF-logs object's gunzipped TSV text → Schema__CF_TUI__File_View. Shared
# by the in-memory and S3 sources so a "file" renders identically wherever it came
# from. Reuses CF__Realtime__Log__Parser; maps each parsed record to a compact
# Event_Row and keeps the raw TSV (capped) for the raw view. No boto3, no textual —
# runs on 3.11 and is fully unit-testable.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Bot__Classifier        import Bot__Classifier
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Realtime__Log__Parser import CF__Realtime__Log__Parser
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__Event_Row  import Schema__CF_TUI__Event_Row
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__File_View   import Schema__CF_TUI__File_View
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.service.CF_TUI__Aggregator          import STATUS_LABEL


class CF_TUI__File_Builder(Type_Safe):
    parser        : CF__Realtime__Log__Parser
    max_raw_lines : int = 200                                                        # cap the raw view so a huge file can't blow up the screen

    def setup(self):
        if self.parser.bot_classifier is None:
            self.parser.bot_classifier = Bot__Classifier()
        return self

    def build(self, key : str, tsv_text : str, size_bytes : int = 0) -> Schema__CF_TUI__File_View:
        self.setup()
        records, skipped = self.parser.parse(tsv_text)
        view = Schema__CF_TUI__File_View(key           = key,
                                         size_bytes    = size_bytes,
                                         total_events  = len(records),
                                         lines_skipped = skipped,
                                         raw_text      = self.cap_raw(tsv_text))
        for record in records:
            view.events.append(self.event_row(record))
        return view

    def event_row(self, record) -> Schema__CF_TUI__Event_Row:
        return Schema__CF_TUI__Event_Row(time         = str(record.timestamp)[11:19],
                                         method       = str(record.cs_method),
                                         status       = record.sc_status,
                                         status_class = STATUS_LABEL.get(record.sc_status_class, 'other'),
                                         uri          = str(record.cs_uri_stem),
                                         country      = str(record.c_country),
                                         cache_hit    = record.cache_hit,
                                         is_bot       = record.is_bot,
                                         user_agent   = str(record.cs_user_agent)[:48])

    def cap_raw(self, tsv_text : str) -> str:
        lines = tsv_text.split('\n')
        if len(lines) <= self.max_raw_lines:
            return tsv_text
        kept = '\n'.join(lines[:self.max_raw_lines])
        return f'{kept}\n… ({len(lines) - self.max_raw_lines} more lines)'
