# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for the Sentinel TUI pure render functions (3.11-safe, no textual)
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.sentinel.rules.Sentinel__Rule__Registry            import Sentinel__Rule__Registry
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Log_Record       import Schema__Sentinel__Log_Record
from sgraph_ai_service_playwright__cli.sentinel.tui.schemas.Schema__Sentinel__TUI__Block_Group import Schema__Sentinel__TUI__Block_Group
from sgraph_ai_service_playwright__cli.sentinel.tui.schemas.List__Schema__Sentinel__TUI__Block_Group import List__Schema__Sentinel__TUI__Block_Group
from sgraph_ai_service_playwright__cli.sentinel.tui.schemas.Schema__Sentinel__TUI__Status   import Schema__Sentinel__TUI__Status
from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Rules__Render    import rules_markup, rule_detail_markup, rules_plain
from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Logs__Render     import logs_markup, trace_markup, logs_plain
from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Blocks__Render   import blocks_markup, blocks_plain
from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Status__Render   import status_markup, status_plain


def _record(request_id='sn-1', verdict='block', rule_id='0012', path='/etc/passwd', reason='path never valid') -> Schema__Sentinel__Log_Record:
    return Schema__Sentinel__Log_Record(request_id=request_id, received_at='2026-05-23T14:30:00Z', method='GET',
                                        path=path, host='h', source_ip='abc', verdict=verdict, reason=reason,
                                        rule_id=rule_id, http_status=403, enforced=(verdict == 'block'),
                                        engine_version='0.1.0', ruleset_version='0.1.0')


class TestRulesRender:
    def test_markup_lists_rules_and_marks_selection(self):
        out = rules_markup(Sentinel__Rule__Registry().all(), selected_index=3)
        assert 'SG/Sentinel — Rules' in out
        assert '0012' in out and 'path-never-valid' in out
        assert '▸' in out                                                            # selection marker

    def test_detail_shows_schema_in_out(self):
        out = rule_detail_markup(Sentinel__Rule__Registry().get('0014'))
        assert 'hidden-file-probe' in out
        assert 'schema in' in out and 'schema out' in out

    def test_plain_has_no_markup(self):
        out = rules_plain(Sentinel__Rule__Registry().all())
        assert '0012' in out and '[' not in out


class TestLogsRender:
    def test_markup_lists_records(self):
        out = logs_markup([_record(verdict='allow', rule_id='0001', path='/index.html')], 'sink-x', 0)
        assert 'SG/Sentinel — Logs' in out and 'sink-x' in out and '/index.html' in out

    def test_markup_empty(self):
        assert '(no records' in logs_markup([], 'sink-x', 0)

    def test_trace_shows_reason_and_enforcement(self):
        out = trace_markup(_record())
        assert 'path never valid' in out and 'HTTP 403' in out and 'rule 0012' in out

    def test_plain_no_markup(self):
        assert '[' not in logs_plain([_record()], 'sink')


class TestBlocksRender:
    def _groups(self):
        g = List__Schema__Sentinel__TUI__Block_Group()
        g.append(Schema__Sentinel__TUI__Block_Group(reason='path never valid', rule_id='0012', count=12))
        return g

    def test_markup_shows_group_and_actions(self):
        out = blocks_markup(self._groups(), 12)
        assert 'path never valid' in out and '0012' in out
        assert 'BLOCK ACTIONS' in out and 'Dropped (403)' in out

    def test_markup_empty(self):
        assert '(no blocks' in blocks_markup(List__Schema__Sentinel__TUI__Block_Group(), 0)

    def test_plain_no_markup(self):
        assert '[' not in blocks_plain(self._groups(), 12)


class TestStatusRender:
    def _status(self):
        return Schema__Sentinel__TUI__Status(node_available=True, record_count=3, allow_count=1, block_count=2,
                                             rule_count=6, banned_ip_count=2, engine_version='0.1.0', ruleset_version='0.1.0')

    def test_markup_shows_reality_and_engine_code(self):
        out = status_markup(self._status(), 'sink-x', "var BANNED_IPS = ['10.0.0.6'];\nfunction handler(e){}")
        assert 'Status & Deployed Code' in out
        assert 'v0.1.0' in out and 'sink-x' in out
        assert 'BANNED_IPS' in out                                                   # the exact engine code is shown
        assert 'function handler' in out

    def test_markup_escapes_brackets_in_code(self):
        out = status_markup(self._status(), 's', "var X = arr[0];")
        assert r'\[0]' in out                                                        # Rich markup escaped

    def test_plain_no_markup_and_omits_code(self):
        out = status_plain(self._status(), 'sink')
        assert '[' not in out and 'records 3' in out
