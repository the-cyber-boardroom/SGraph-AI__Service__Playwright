# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Sentinel__TUI__Source (the data layer behind the TUIs)
# Uses an in-memory sink (no AWS, no node for the sink-backed paths).
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Log_Record      import Schema__Sentinel__Log_Record
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.InMemory__Log__Sink       import InMemory__Log__Sink
from sgraph_ai_service_playwright__cli.sentinel.tui.source.Sentinel__TUI__Source           import Sentinel__TUI__Source


def _rec(request_id, verdict, rule_id, reason) -> Schema__Sentinel__Log_Record:
    return Schema__Sentinel__Log_Record(request_id=request_id, received_at='2026-05-23T14:30:00Z', method='GET',
                                        path='/x', host='h', source_ip='abc', verdict=verdict, reason=reason, rule_id=rule_id)


def _source_with(records) -> Sentinel__TUI__Source:
    sink = InMemory__Log__Sink()
    for r in records:
        sink.write(r)
    return Sentinel__TUI__Source(log_sink=sink)


class TestRules:
    def test_rules_and_get(self):
        s = Sentinel__TUI__Source(log_sink=InMemory__Log__Sink())
        assert len(s.rules()) == 6
        assert str(s.rule('0012').name) == 'path-never-valid'


class TestRecordsAndBlocks:
    def test_records_and_blocks_filter(self):
        s = _source_with([_rec('sn-1', 'allow', '0001', 'no rule matched'),
                          _rec('sn-2', 'block', '0012', 'path never valid'),
                          _rec('sn-3', 'block', '0012', 'path never valid')])
        assert len(s.records()) == 3
        assert len(s.blocks())  == 2

    def test_block_groups_aggregate_and_sort_by_count(self):
        s = _source_with([_rec('sn-1', 'block', '0012', 'path never valid'),
                          _rec('sn-2', 'block', '0012', 'path never valid'),
                          _rec('sn-3', 'block', '0014', 'hidden file probe')])
        groups = s.block_groups()
        assert len(groups) == 2
        assert str(groups[0].rule_id) == '0012' and groups[0].count == 2            # highest count first
        assert str(groups[1].rule_id) == '0014' and groups[1].count == 1

    def test_record_lookup_by_id(self):
        s = _source_with([_rec('sn-find', 'block', '0012', 'path never valid')])
        assert str(s.record('sn-find').rule_id) == '0012'
        assert s.record('sn-missing') is None


class TestStatusAndEngine:
    def test_status_counts_and_versions(self):
        s = _source_with([_rec('sn-1', 'allow', '0001', 'no rule matched'),
                          _rec('sn-2', 'block', '0012', 'path never valid')])
        st = s.status()
        assert st.record_count == 2 and st.allow_count == 1 and st.block_count == 1
        assert st.rule_count == 6
        assert str(st.engine_version) == '0.1.0'                                     # parsed from sentinel_l1.js
        assert st.banned_ip_count >= 1

    def test_engine_code_is_materialised_with_banned_ips_inlined(self):
        code = Sentinel__TUI__Source(log_sink=InMemory__Log__Sink()).engine_code()
        assert 'var BANNED_IPS = [];' not in code
        assert '10.0.0.6' in code
