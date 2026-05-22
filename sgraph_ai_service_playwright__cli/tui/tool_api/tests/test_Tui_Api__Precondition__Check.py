# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api tests: Tui_Api__Precondition__Check
# Flat preconditions over a nested state dict (EQ / IN / EXISTS / dotted path). 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Cond_Op        import Enum__Tui_Api__Cond_Op
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Precondition import Schema__Tui_Api__Precondition
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Precondition__Check  import Tui_Api__Precondition__Check

STATE = {'slug': {'state': 'live', 'name': 'alice'}}


def _pc(path, op, value, note=''):
    return Schema__Tui_Api__Precondition(state_path=path, op=op, value=value, note=note)


def test_empty_preconditions_pass():
    assert Tui_Api__Precondition__Check().evaluate([], STATE) == (True, '')


def test_eq_pass_and_fail_with_note():
    check = Tui_Api__Precondition__Check()
    assert check.evaluate([_pc('slug.state', Enum__Tui_Api__Cond_Op.EQ, 'live')], STATE)[0] is True
    ok, note = check.evaluate([_pc('slug.state', Enum__Tui_Api__Cond_Op.EQ, 'dormant', 'must be dormant')], STATE)
    assert ok is False and note == 'must be dormant'


def test_in_and_exists_and_absent():
    check = Tui_Api__Precondition__Check()
    assert check.evaluate([_pc('slug.state', Enum__Tui_Api__Cond_Op.IN, 'idle,live')], STATE)[0] is True
    assert check.evaluate([_pc('slug.state', Enum__Tui_Api__Cond_Op.EXISTS, '')],      STATE)[0] is True
    assert check.evaluate([_pc('slug.missing', Enum__Tui_Api__Cond_Op.ABSENT, '')],    STATE)[0] is True
    assert check.evaluate([_pc('slug.missing', Enum__Tui_Api__Cond_Op.EXISTS, '')],    STATE)[0] is False
