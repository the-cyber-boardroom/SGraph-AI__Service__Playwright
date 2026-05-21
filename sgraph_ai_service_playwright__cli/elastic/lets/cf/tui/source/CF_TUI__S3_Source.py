# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: CF_TUI__S3_Source
# The LIVE view: reads the newest .gz objects from the Firehose-written
# cloudfront-realtime/ bucket and aggregates them — directly, with NO Elasticsearch
# in the loop (the seam the brief calls for). Reuses the LETS boundaries verbatim:
# S3__Inventory__Lister (list) + S3__Object__Fetcher (get) + CF__Realtime__Log__
# Parser (gunzip + parse). Read-only; never writes to the bucket.
#
# The two S3 boundaries are injected Type_Safe attributes — tests subclass them to
# return fixture bytes (the LETS no-mock pattern), so this is testable with no AWS.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Bot__Classifier        import Bot__Classifier
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Realtime__Log__Parser import CF__Realtime__Log__Parser, gunzip
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.S3__Object__Fetcher     import S3__Object__Fetcher
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.S3__Inventory__Lister import S3__Inventory__Lister
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__config            import CF_LOGS_BUCKET, CF_LOGS_PREFIX, CF_LOGS_REGION, TUI_S3_SAMPLE_FILES
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.enums.Enum__CF_TUI__Source         import Enum__CF_TUI__Source
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__Traffic_Snapshot import Schema__CF_TUI__Traffic_Snapshot
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.service.CF_TUI__Aggregator         import CF_TUI__Aggregator
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.source.CF_TUI__Data_Source         import CF_TUI__Data_Source


class CF_TUI__S3_Source(CF_TUI__Data_Source):
    bucket       : str = CF_LOGS_BUCKET
    prefix       : str = CF_LOGS_PREFIX
    region       : str = CF_LOGS_REGION
    sample_files : int = TUI_S3_SAMPLE_FILES                                         # newest N objects pulled per refresh
    lister       : S3__Inventory__Lister
    fetcher      : S3__Object__Fetcher
    parser       : CF__Realtime__Log__Parser

    def setup(self):
        if self.parser.bot_classifier is None:
            self.parser.bot_classifier = Bot__Classifier()
        return self

    def source(self) -> Enum__CF_TUI__Source:
        return Enum__CF_TUI__Source.S3

    def label(self) -> str:
        return f's3://{self.bucket}/{self.prefix}'

    def newest_keys(self) -> list:                                                   # newest `sample_files` object keys under the prefix
        objects, _ = self.lister.paginate(bucket=self.bucket, prefix=self.prefix, region=self.region)
        objects.sort(key=lambda obj: str(obj.get('LastModified', '')), reverse=True)
        return [obj['Key'] for obj in objects[:self.sample_files] if obj.get('Key')]

    def traffic_snapshot(self) -> Schema__CF_TUI__Traffic_Snapshot:
        self.setup()
        keys  = self.newest_keys()
        blobs = []
        for key in keys:
            raw = self.fetcher.get_object_bytes(bucket=self.bucket, key=key, region=self.region)
            text = gunzip(raw)
            if text:
                blobs.append(text)
        records, skipped = self.parser.parse('\n'.join(blobs))
        return self.aggregator().aggregate(records,
                                           source        = Enum__CF_TUI__Source.S3,
                                           source_label  = self.label(),
                                           files_sampled = len(keys),
                                           lines_skipped = skipped,
                                           captured_at   = int(time.time()))

    def aggregator(self) -> CF_TUI__Aggregator:
        return CF_TUI__Aggregator()
