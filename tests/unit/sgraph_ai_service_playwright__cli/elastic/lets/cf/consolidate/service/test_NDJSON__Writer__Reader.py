# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — NDJSON__Writer + NDJSON__Reader
# Round-trip: List → gzip bytes → identical List.
# Edge cases: empty list, single record, record with non-ASCII user-agent.
# ═══════════════════════════════════════════════════════════════════════════════

import gzip
from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.service.NDJSON__Writer import NDJSON__Writer
from sgraph_ai_service_playwright__cli.elastic.lets.cf.consolidate.service.NDJSON__Reader import NDJSON__Reader
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.collections.List__Schema__CF__Event__Record import List__Schema__CF__Event__Record
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.schemas.Schema__CF__Event__Record            import Schema__CF__Event__Record


def make_record(**kwargs) -> Schema__CF__Event__Record:
    return Schema__CF__Event__Record(**kwargs)


class test_NDJSON__Writer__Reader(TestCase):

    def setUp(self):
        self.writer = NDJSON__Writer()
        self.reader = NDJSON__Reader()

    def test_empty_list_round_trip(self):
        empty = List__Schema__CF__Event__Record()
        data  = self.writer.records_to_bytes(empty)
        assert isinstance(data, bytes)
        result = self.reader.bytes_to_records(data)
        assert len(result) == 0

    def test_single_record_round_trip(self):
        lst = List__Schema__CF__Event__Record()
        lst.append(make_record(sc_status=200, time_taken_ms=42))
        data   = self.writer.records_to_bytes(lst)
        assert isinstance(data, bytes)
        result = self.reader.bytes_to_records(data)
        assert len(result) == 1
        assert result[0].sc_status      == 200
        assert result[0].time_taken_ms  == 42

    def test_multi_record_round_trip(self):
        lst = List__Schema__CF__Event__Record()
        for i in range(10):
            lst.append(make_record(sc_status=200 + i, line_index=i))
        data   = self.writer.records_to_bytes(lst)
        result = self.reader.bytes_to_records(data)
        assert len(result) == 10
        for i, rec in enumerate(result):
            assert rec.sc_status  == 200 + i
            assert rec.line_index == i

    def test_output_is_gzip_compressed(self):
        lst = List__Schema__CF__Event__Record()
        lst.append(make_record(sc_status=301))
        data = self.writer.records_to_bytes(lst)
        decompressed = gzip.decompress(data).decode('utf-8')
        assert '"sc_status": 301' in decompressed or '"sc_status":301' in decompressed

    def test_output_is_ndjson_one_line_per_record(self):
        lst = List__Schema__CF__Event__Record()
        lst.append(make_record(sc_status=200))
        lst.append(make_record(sc_status=404))
        data  = self.writer.records_to_bytes(lst)
        lines = [l for l in gzip.decompress(data).decode('utf-8').splitlines() if l.strip()]
        assert len(lines) == 2

    def test_reader_tolerates_empty_bytes(self):
        result = self.reader.bytes_to_records(b'')
        assert len(result) == 0

    def test_reader_tolerates_corrupted_bytes(self):
        result = self.reader.bytes_to_records(b'not-gzip-data')
        assert len(result) == 0

    def test_user_agent_preserved(self):
        lst = List__Schema__CF__Event__Record()
        lst.append(make_record(cs_user_agent='Mozilla/5.0 (compatible; Googlebot/2.1)'))
        data   = self.writer.records_to_bytes(lst)
        result = self.reader.bytes_to_records(data)
        assert result[0].cs_user_agent == 'Mozilla/5.0 (compatible; Googlebot/2.1)'

    def test_schema_version_preserved(self):
        lst = List__Schema__CF__Event__Record()
        lst.append(make_record())
        data   = self.writer.records_to_bytes(lst)
        result = self.reader.bytes_to_records(data)
        assert str(result[0].schema_version) == 'Schema__CF__Event__Record_v1'
