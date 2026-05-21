# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api tests: Tui_Api__Execution_Center
# Uses two tiny in-test providers (a mutating counter + a state-gated action) — no
# mocks, no AWS. Asserts the gate order: precondition → params → SG/Role → mutation
# gate → dispatch → audit. Pure — 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

import os

from sgraph_ai_service_playwright__cli.aws.creds.service.Creds__Scope__Catalogue        import Creds__Scope__Catalogue
from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Cond_Op         import Enum__Tui_Api__Cond_Op
from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Exec_Mode       import Enum__Tui_Api__Exec_Mode
from sgraph_ai_service_playwright__cli.tui.tool_api.enums.Enum__Tui_Api__Tier            import Enum__Tui_Api__Tier
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Action         import List__Tui_Api__Action
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Precondition   import List__Tui_Api__Precondition
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Tier           import List__Tui_Api__Tier
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Action       import Schema__Tui_Api__Action
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Grant        import Schema__Tui_Api__Grant
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Manifest     import Schema__Tui_Api__Manifest
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Precondition import Schema__Tui_Api__Precondition
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Result       import Schema__Tui_Api__Result
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Scope        import Schema__Tui_Api__Scope
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Execution_Center     import Tui_Api__Execution_Center
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Privilege__Resolver  import Tui_Api__Privilege__Resolver
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Provider             import Tui_Api__Provider
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry             import Tui_Api__Registry

_MUT_ENV = 'SG_TUI_API__TEST_MUT'


def _action(name, tier, capability, *, supports_dry_run=False, props=None, preconditions=None):
    action = Schema__Tui_Api__Action(name=name, tier=tier,
                                    scope=Schema__Tui_Api__Scope(api='demo.counter', capability=capability),
                                    input_schema={'type': 'object', 'properties': props or {}, 'required': []},
                                    supports_dry_run=supports_dry_run)
    if preconditions is not None:
        action.preconditions = preconditions
    return action


class _Counter_Provider(Tui_Api__Provider):
    count : int = 0

    def manifest(self):
        actions = List__Tui_Api__Action()
        actions.append(_action('peek', Enum__Tui_Api__Tier.READ_ONLY, 'read'))
        actions.append(_action('bump', Enum__Tui_Api__Tier.WRITE, 'write',
                               supports_dry_run=True, props={'by': {'type': 'integer'}}))
        tiers = List__Tui_Api__Tier()
        tiers.append(Enum__Tui_Api__Tier.READ_ONLY)
        tiers.append(Enum__Tui_Api__Tier.WRITE)
        return Schema__Tui_Api__Manifest(slug='demo.counter', tool='demo', name='Counter',
                                        tiers=tiers, actions=actions)

    def state(self):
        return {'count': self.count}

    def dry_run(self, action, params):
        if action == 'bump':
            return {'count_before': self.count, 'count_after': self.count + int(params.get('by', 1))}
        return {}

    def dispatch(self, action, params):
        if action == 'peek':
            return Schema__Tui_Api__Result(ok=True, data={'count': self.count})
        if action == 'bump':
            self.count += int(params.get('by', 1))
            return Schema__Tui_Api__Result(ok=True, data={'count': self.count})
        return Schema__Tui_Api__Result(ok=False, error='unknown')


class _Gated_Provider(Tui_Api__Provider):
    ready : bool = False

    def manifest(self):
        preconditions = List__Tui_Api__Precondition()
        preconditions.append(Schema__Tui_Api__Precondition(state_path='ready', op=Enum__Tui_Api__Cond_Op.EQ,
                                                          value='True', note='not ready yet'))
        actions = List__Tui_Api__Action()
        actions.append(Schema__Tui_Api__Action(name='go', tier=Enum__Tui_Api__Tier.READ_ONLY,
                                              scope=Schema__Tui_Api__Scope(api='demo.gate', capability='read'),
                                              input_schema={'type': 'object', 'properties': {}, 'required': []},
                                              preconditions=preconditions))
        tiers = List__Tui_Api__Tier(); tiers.append(Enum__Tui_Api__Tier.READ_ONLY)
        return Schema__Tui_Api__Manifest(slug='demo.gate', tool='demo', name='Gate', tiers=tiers, actions=actions)

    def state(self):
        return {'ready': self.ready}

    def dispatch(self, action, params):
        return Schema__Tui_Api__Result(ok=True, data={'went': True})


def _center(provider, tmp_path, mode=Enum__Tui_Api__Exec_Mode.AUTO):
    resolver = Tui_Api__Privilege__Resolver(creds_catalogue=Creds__Scope__Catalogue(catalogue_path=str(tmp_path / 'scopes.json')))
    registry = Tui_Api__Registry().register(provider)
    return Tui_Api__Execution_Center(mode=mode, registry=registry, resolver=resolver, mutation_env=_MUT_ENV)


def test_read_only_auto_dispatches_and_audits(tmp_path):
    center = _center(_Counter_Provider(count=5), tmp_path)
    result = center.execute('demo.counter', 'peek', {})
    assert result.ok is True and result.data['count'] == 5
    assert len(center.log) == 1 and center.log[0].result_ok is True


def test_invalid_params_refused_before_dispatch(tmp_path):
    provider = _Counter_Provider(count=5)
    result   = _center(provider, tmp_path).execute('demo.counter', 'bump', {'by': 'NaN'})
    assert result.ok is False and 'invalid params' in result.error
    assert provider.count == 5


def test_sg_role_miss_refused(tmp_path):
    grants = [Schema__Tui_Api__Grant(scope=Schema__Tui_Api__Scope(api='demo.counter', capability='read'))]
    result = _center(_Counter_Provider(), tmp_path).execute('demo.counter', 'bump', {}, grants=grants)
    assert result.ok is False and 'not granted' in result.error


def test_write_without_mutations_returns_preview_and_does_not_mutate(tmp_path):
    os.environ.pop(_MUT_ENV, None)
    provider = _Counter_Provider(count=5)
    result   = _center(provider, tmp_path).execute('demo.counter', 'bump', {'by': 3})
    assert result.ok is False and result.dry_run is True
    assert result.preview['count_after'] == 8
    assert provider.count == 5


def test_write_with_allow_mutations_dispatches(tmp_path):
    provider = _Counter_Provider(count=5)
    os.environ[_MUT_ENV] = '1'
    try:
        result = _center(provider, tmp_path).execute('demo.counter', 'bump', {'by': 3})
        assert result.ok is True and provider.count == 8
    finally:
        os.environ.pop(_MUT_ENV, None)


def test_confirm_false_refuses_and_does_not_mutate(tmp_path):
    os.environ.pop(_MUT_ENV, None)
    provider = _Counter_Provider(count=5)
    center   = _center(provider, tmp_path, mode=Enum__Tui_Api__Exec_Mode.CONFIRM)
    result   = center.execute('demo.counter', 'bump', {'by': 1}, on_confirm=lambda a, p, prev: False)
    assert result.ok is False and 'not confirmed' in result.error
    assert provider.count == 5


def test_precondition_blocks_then_allows(tmp_path):
    provider = _Gated_Provider(ready=False)
    center   = _center(provider, tmp_path)
    blocked  = center.execute('demo.gate', 'go', {})
    assert blocked.ok is False and 'not ready yet' in blocked.error
    provider.ready = True
    assert center.execute('demo.gate', 'go', {}).ok is True


def test_available_actions_filtered_by_precondition(tmp_path):
    assert [str(a.name) for a in _center(_Gated_Provider(ready=False), tmp_path).available_actions('demo.gate')] == []
    assert [str(a.name) for a in _center(_Gated_Provider(ready=True),  tmp_path).available_actions('demo.gate')] == ['go']


def test_audit_masks_secret_params(tmp_path):
    center = _center(_Counter_Provider(count=0), tmp_path)
    center.execute('demo.counter', 'peek', {'token': 'abc', 'note': 'hi'})
    call = center.log[-1]
    assert call.params['token'] == '***'
    assert call.params['note']  == 'hi'
