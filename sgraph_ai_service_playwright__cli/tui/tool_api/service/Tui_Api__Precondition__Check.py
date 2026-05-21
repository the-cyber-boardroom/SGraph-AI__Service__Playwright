# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api: Tui_Api__Precondition__Check
# Evaluates flat preconditions against a provider's state() dict (dotted-path lookup).
# Returns (ok, failing_note). Pure — no AWS.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Cond_Op import Enum__Tui_Api__Cond_Op


class Tui_Api__Precondition__Check(Type_Safe):

    def evaluate(self, preconditions, state: dict) -> tuple:
        for precondition in preconditions:
            actual = self.dig(state, str(precondition.state_path))
            if not self.apply(precondition.op, actual, str(precondition.value)):
                return (False, str(precondition.note) or f'{precondition.state_path} {precondition.op} {precondition.value}')
        return (True, '')

    def dig(self, state, path: str):                                              # dotted-path lookup into a nested dict
        node = state
        for part in path.split('.'):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return None
        return node

    def apply(self, op, actual, value: str) -> bool:
        if op == Enum__Tui_Api__Cond_Op.EQ:     return str(actual) == value
        if op == Enum__Tui_Api__Cond_Op.NEQ:    return str(actual) != value
        if op == Enum__Tui_Api__Cond_Op.IN:     return str(actual) in self._set(value)
        if op == Enum__Tui_Api__Cond_Op.NOT_IN: return str(actual) not in self._set(value)
        if op == Enum__Tui_Api__Cond_Op.EXISTS: return actual is not None
        if op == Enum__Tui_Api__Cond_Op.ABSENT: return actual is None
        return False

    def _set(self, value: str):
        return [item.strip() for item in value.split(',')]
