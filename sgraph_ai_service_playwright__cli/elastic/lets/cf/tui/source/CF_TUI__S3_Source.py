# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: CF_TUI__S3_Source
# The LIVE view: reads CF-logs .gz objects from the Firehose-written
# cloudfront-realtime/ bucket and aggregates / browses them — directly, with NO
# Elasticsearch in the loop (the seam the brief calls for). Reuses the LETS boundaries
# verbatim: S3__Inventory__Lister (list) + S3__Object__Fetcher (get) +
# CF__Realtime__Log__Parser (gunzip + parse). Read-only.
#
# `date_iso`/`hour` scope the prefix to a day (or day+hour) and `sample_files` caps
# how many newest objects are pulled — so the screens can load more files and walk
# hours/days. The two S3 boundaries are injected — tests subclass them to return
# fixture bytes (the LETS no-mock pattern), so this is testable with no AWS.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Bot__Classifier        import Bot__Classifier
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Realtime__Log__Parser import CF__Realtime__Log__Parser, gunzip
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.S3__Object__Fetcher     import S3__Object__Fetcher
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.S3__Inventory__Lister import S3__Inventory__Lister, parse_firehose_filename
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__config            import CF_LOGS_BUCKET, CF_LOGS_PREFIX, CF_LOGS_REGION, TUI_S3_SAMPLE_FILES, cf_realtime_prefix
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.enums.Enum__CF_TUI__Source         import Enum__CF_TUI__Source
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.List__CF_TUI__File_Row      import List__CF_TUI__File_Row
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__File_Row    import Schema__CF_TUI__File_Row
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__File_View   import Schema__CF_TUI__File_View
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__Traffic_Snapshot import Schema__CF_TUI__Traffic_Snapshot
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.service.CF_TUI__Aggregator         import CF_TUI__Aggregator
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.service.CF_TUI__File_Builder       import CF_TUI__File_Builder
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.source.CF_TUI__Data_Source         import CF_TUI__Data_Source


class CF_TUI__S3_Source(CF_TUI__Data_Source):
    bucket       : str = CF_LOGS_BUCKET
    prefix       : str = CF_LOGS_PREFIX                                              # base prefix; date/hour scope under it
    region       : str = CF_LOGS_REGION
    date_iso     : str                                                              # '' = all dates; '2026-05-21' scopes to a day
    hour         : str                                                              # '' = all hours; '08' scopes to an hour (needs date)
    sample_files : int = TUI_S3_SAMPLE_FILES                                         # newest N objects pulled
    lister       : S3__Inventory__Lister
    fetcher      : S3__Object__Fetcher
    parser       : CF__Realtime__Log__Parser

    def setup(self):
        if self.parser.bot_classifier is None:
            self.parser.bot_classifier = Bot__Classifier()
        return self

    def source(self) -> Enum__CF_TUI__Source:
        return Enum__CF_TUI__Source.S3

    def scoped_prefix(self, date_iso : str = '', hour : str = '') -> str:
        return cf_realtime_prefix(date_iso or self.date_iso, hour or self.hour, base=self.prefix)

    def label(self) -> str:
        return f's3://{self.bucket}/{self.scoped_prefix()}'

    def newest_objects(self, date_iso : str = '', hour : str = '', limit : int = 0) -> list:
        objects, _ = self.lister.paginate(bucket=self.bucket, prefix=self.scoped_prefix(date_iso, hour), region=self.region)
        objects.sort(key=lambda obj: str(obj.get('LastModified', '')), reverse=True)
        cap = limit or self.sample_files
        return objects[:cap]

    def traffic_snapshot(self) -> Schema__CF_TUI__Traffic_Snapshot:
        self.setup()
        objects = self.newest_objects()
        blobs   = []
        for obj in objects:
            key = obj.get('Key')
            if not key:
                continue
            text = gunzip(self.fetcher.get_object_bytes(bucket=self.bucket, key=key, region=self.region))
            if text:
                blobs.append(text)
        records, skipped = self.parser.parse('\n'.join(blobs))
        return CF_TUI__Aggregator().aggregate(records,
                                              source        = Enum__CF_TUI__Source.S3,
                                              source_label  = self.label(),
                                              files_sampled = len(objects),
                                              lines_skipped = skipped,
                                              captured_at   = int(time.time()))

    def list_files(self, date_iso : str = '', hour : str = '', max_files : int = 0) -> List__CF_TUI__File_Row:
        rows = List__CF_TUI__File_Row()
        for obj in self.newest_objects(date_iso, hour, limit=max_files):
            key = obj.get('Key')
            if not key:
                continue
            info = parse_firehose_filename(key)
            rows.append(Schema__CF_TUI__File_Row(key           = key,
                                                 size_bytes    = int(obj.get('Size', 0) or 0),
                                                 last_modified = str(obj.get('LastModified', '')),
                                                 delivery_iso  = info.get('iso', '')))
        return rows

    def read_file(self, key : str) -> Schema__CF_TUI__File_View:
        self.setup()
        raw  = self.fetcher.get_object_bytes(bucket=self.bucket, key=key, region=self.region)
        text = gunzip(raw)
        return CF_TUI__File_Builder(parser=self.parser).build(key, text, size_bytes=len(raw))
