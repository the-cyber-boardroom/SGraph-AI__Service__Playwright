# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Sentinel__Tui_Api__Provider (read-only TUI API)
# Drives the provider through the real Tui_Api__Execution_Center over an in-memory
# sink — no AWS, no mocks. node-gated for the two engine-backed actions.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import skipUnless

from sgraph_ai_service_playwright__cli.sentinel.runtime.layer1.Sentinel__L1__Source       import node_available
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Log_Record       import Schema__Sentinel__Log_Record
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.InMemory__Log__Sink        import InMemory__Log__Sink
from sgraph_ai_service_playwright__cli.sentinel.tui.source.Sentinel__TUI__Source            import Sentinel__TUI__Source
from sgraph_ai_service_playwright__cli.sentinel.tui.tui_api.Sentinel__Tui_Api__Provider     import Sentinel__Tui_Api__Provider
from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Tier               import Enum__Tui_Api__Tier
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Execution_Center       import Tui_Api__Execution_Center
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry               import Tui_Api__Registry

SLUG = 'sg-sentinel'


def _block(request_id='sn-1'):
    return Schema__Sentinel__Log_Record(request_id=request_id, received_at='2026-05-23T14:30:00Z', method='GET',
                                        path='/etc/passwd', host='h', source_ip='abc', verdict='block',
                                        reason='path never valid', rule_id='0012', http_status=403, enforced=True)


def _center(records=()):
    sink = InMemory__Log__Sink()
    for r in records:
        sink.write(r)
    provider = Sentinel__Tui_Api__Provider(source=Sentinel__TUI__Source(log_sink=sink))
    return Tui_Api__Execution_Center(registry=Tui_Api__Registry().register(provider)), provider


def _result(center, action, params=None):
    return center.execute(SLUG, action, params or {})


class TestManifest:
    def test_all_actions_read_only(self):
        _, provider = _center()
        actions = provider.manifest().actions
        assert len(actions) == 11
        assert all(a.tier == Enum__Tui_Api__Tier.READ_ONLY for a in actions)

    def test_registered_under_slug(self):
        center, _ = _center()
        assert SLUG in center.registry.list_slugs()


class TestReadActions:
    def test_rules_list(self):
        center, _ = _center()
        r = _result(center, 'rules_list')
        assert r.ok and len(r.json()['data']['result']['rules']) == 6

    def test_rule_show_and_unknown(self):
        center, _ = _center()
        assert _result(center, 'rule_show', {'rule_id': '0012'}).ok
        assert _result(center, 'rule_show', {'rule_id': '9999'}).ok is False

    def test_logs_and_trace(self):
        center, _ = _center([_block('sn-a')])
        assert len(_result(center, 'logs_list').json()['data']['result']['records']) == 1
        assert _result(center, 'logs_trace', {'request_id': 'sn-a'}).ok
        assert _result(center, 'logs_trace', {'request_id': 'nope'}).ok is False

    def test_blocks_list_and_why(self):
        center, _ = _center([_block('sn-a'), _block('sn-b')])
        assert _result(center, 'blocks_list').json()['data']['result']['blocks'][0]['count'] == 2
        assert len(_result(center, 'blocks_why', {'needle': 'sn-a'}).json()['data']['result']['matches']) == 1

    def test_status_and_engine_code(self):
        center, _ = _center([_block()])
        assert _result(center, 'status').json()['data']['result']['status']['block_count'] == 1
        code = _result(center, 'engine_code').json()['data']['result']['engine_code']
        assert 'var BANNED_IPS = [];' not in code and '10.0.0.6' in code

    def test_traffic_cases(self):
        center, _ = _center()
        names = {c['name'] for c in _result(center, 'traffic_cases').json()['data']['result']['cases']}
        assert 'etc-passwd' in names

    def test_unknown_action_errors(self):
        center, _ = _center()
        assert _result(center, 'nope').ok is False


@skipUnless(node_available(), 'node not available')
class TestNodeBacked:
    def test_rules_test(self):
        center, _ = _center()
        sigs = _result(center, 'rules_test').json()['data']['result']['signals']
        assert any(s['rule'] == '0012' and s['verdict'] == 'block' for s in sigs)

    def test_traffic_gen_reports_perfect_accuracy(self):
        center, _ = _center()
        report = _result(center, 'traffic_gen', {'repeat': 1}).json()['data']['result']['report']
        assert report['accuracy_pct'] == 100.0
