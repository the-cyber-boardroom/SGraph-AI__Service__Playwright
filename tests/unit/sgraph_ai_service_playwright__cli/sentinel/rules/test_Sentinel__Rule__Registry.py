# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Sentinel__Rule__Registry
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Action     import Enum__Sentinel__Action
from sgraph_ai_service_playwright__cli.sentinel.rules.Sentinel__Rule__Registry   import Sentinel__Rule__Registry


class TestAll:
    def test_returns_six_rules(self):
        assert len(Sentinel__Rule__Registry().all()) == 6

    def test_ids_match_the_engine(self):
        ids = [str(r.rule_id) for r in Sentinel__Rule__Registry().all()]
        assert ids == ['0001', '0003', '0007', '0012', '0014', '0018']

    def test_block_rules_carry_a_block_action(self):
        by_id = {str(r.rule_id): r for r in Sentinel__Rule__Registry().all()}
        assert by_id['0001'].action == Enum__Sentinel__Action.PASS
        assert by_id['0012'].action == Enum__Sentinel__Action.DROP_403
        assert by_id['0014'].action == Enum__Sentinel__Action.DEFLECT_404


class TestGet:
    def test_get_existing(self):
        rule = Sentinel__Rule__Registry().get('0018')
        assert str(rule.name) == 'wp-scan-on-static'

    def test_get_missing_returns_none(self):
        assert Sentinel__Rule__Registry().get('9999') is None
