# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api/testing: Tui_Api__Contract__Asserts
# Reusable contract gate every provider must satisfy (the pure half of the B5 tester).
# Any area's test calls assert_ok(provider) to prove its manifest is well-formed:
# real JSON-Schema inputs, scoped actions, tiers declared, unique names. No AWS.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Tui_Api__Contract__Asserts(Type_Safe):

    def check(self, provider) -> list:                                            # returns a list of problems (empty == compliant)
        problems = []
        manifest = provider.manifest()
        if not str(manifest.slug):  problems.append('manifest.slug is empty')
        if not str(manifest.tool):  problems.append('manifest.tool is empty')
        if len(manifest.tiers) == 0: problems.append('manifest.tiers is empty')

        declared_tiers = {str(tier) for tier in manifest.tiers}
        seen_names     = set()
        for action in manifest.actions:
            name = str(action.name)
            if not name:               problems.append('action with an empty name')
            if name in seen_names:     problems.append(f'duplicate action name: {name}')
            seen_names.add(name)
            if not isinstance(action.input_schema, dict) or action.input_schema.get('type') != 'object':
                problems.append(f'{name}: input_schema is not a JSON-Schema object')
            if not str(action.scope.api):        problems.append(f'{name}: scope.api is empty')
            if not str(action.scope.capability): problems.append(f'{name}: scope.capability is empty')
            if str(action.tier) not in declared_tiers:
                problems.append(f'{name}: tier "{action.tier}" not declared in manifest.tiers')
        return problems

    def assert_ok(self, provider) -> None:
        problems = self.check(provider)
        assert problems == [], f'TUI API contract violations: {problems}'
