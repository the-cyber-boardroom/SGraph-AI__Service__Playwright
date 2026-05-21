# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: CF_TUI__In_Memory_Source
# Data source over real CF log lines held in memory (or read from a local file).
# Parses with the same CF__Realtime__Log__Parser the LETS events slice uses, then
# aggregates — so it renders identically to the S3 source with no AWS. Honest: it
# parses REAL CloudFront TSV lines and labels itself "in-memory (fixtures)" so the
# screen never implies live traffic.
#
# It can hold multiple named blobs (`files`) so the file browser works in-memory; if
# only `tsv_text` is set it presents a single "fixtures.tsv" file. Traffic aggregates
# across all files, so traffic and the file browser stay consistent.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Bot__Classifier        import Bot__Classifier
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Realtime__Log__Parser import CF__Realtime__Log__Parser
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.enums.Enum__CF_TUI__Source         import Enum__CF_TUI__Source
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.List__CF_TUI__File_Row      import List__CF_TUI__File_Row
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.List__CF_TUI__Fixture_File  import List__CF_TUI__Fixture_File
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__File_Row    import Schema__CF_TUI__File_Row
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__File_View   import Schema__CF_TUI__File_View
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__Fixture_File import Schema__CF_TUI__Fixture_File
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__Traffic_Snapshot import Schema__CF_TUI__Traffic_Snapshot
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.service.CF_TUI__Aggregator         import CF_TUI__Aggregator
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.service.CF_TUI__File_Builder       import CF_TUI__File_Builder
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.source.CF_TUI__Data_Source         import CF_TUI__Data_Source


class CF_TUI__In_Memory_Source(CF_TUI__Data_Source):
    tsv_text     : str                                                               # single-blob shorthand; presented as "fixtures.tsv"
    files        : List__CF_TUI__Fixture_File                                         # optional named blobs for multi-file browsing
    source_label : str = 'in-memory (fixtures)'
    aggregator   : CF_TUI__Aggregator
    parser       : CF__Realtime__Log__Parser

    def setup(self):
        if self.parser.bot_classifier is None:
            self.parser.bot_classifier = Bot__Classifier()
        return self

    @classmethod
    def from_file(cls, path : str, source_label : str = ''):                         # load real CF TSV from a local file
        with open(path, 'r', encoding='utf-8', errors='replace') as handle:
            text = handle.read()
        return cls(tsv_text=text, source_label=source_label or f'file: {path}').setup()

    def effective_files(self) -> List__CF_TUI__Fixture_File:
        if len(self.files):
            return self.files
        synth = List__CF_TUI__Fixture_File()
        if self.tsv_text.strip():
            synth.append(Schema__CF_TUI__Fixture_File(key='fixtures.tsv', tsv_text=self.tsv_text))
        return synth

    def source(self) -> Enum__CF_TUI__Source:
        return Enum__CF_TUI__Source.IN_MEMORY

    def label(self) -> str:
        return self.source_label

    def traffic_snapshot(self) -> Schema__CF_TUI__Traffic_Snapshot:
        self.setup()
        files            = self.effective_files()
        combined         = '\n'.join(f.tsv_text for f in files)
        records, skipped = self.parser.parse(combined)
        return self.aggregator.aggregate(records,
                                         source        = Enum__CF_TUI__Source.IN_MEMORY,
                                         source_label  = self.source_label,
                                         files_sampled = len(files),
                                         lines_skipped = skipped,
                                         captured_at   = int(time.time()))

    def list_files(self, date_iso : str = '', hour : str = '', max_files : int = 0) -> List__CF_TUI__File_Row:
        rows = List__CF_TUI__File_Row()
        for f in self.effective_files():
            rows.append(Schema__CF_TUI__File_Row(key=f.key, size_bytes=len(f.tsv_text.encode('utf-8'))))
            if max_files and len(rows) >= max_files:
                break
        return rows

    def read_file(self, key : str) -> Schema__CF_TUI__File_View:
        for f in self.effective_files():
            if f.key == key:
                return CF_TUI__File_Builder(parser=self.parser).build(key, f.tsv_text, size_bytes=len(f.tsv_text.encode('utf-8')))
        return Schema__CF_TUI__File_View(key=key)
