# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api tests: Tui_Api__Loadout__Assembler
# --tools / workflow → Loadout; granted_actions filters by scope coverage; whole-API
# '*' grants everything; an over-narrow grant grants nothing. Pure — 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

from tests.unit.sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client__In_Memory import S3__AWS__Client__In_Memory

from sgraph_ai_service_playwright__cli.aws.creds.service.Creds__Scope__Catalogue         import Creds__Scope__Catalogue
from sgraph_ai_service_playwright__cli.aws.s3.tui_api.S3__Tui_Api__Provider              import S3__Tui_Api__Provider
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Workflow    import Schema__Tui_Api__Workflow
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Loadout__Assembler  import Tui_Api__Loadout__Assembler
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Privilege__Resolver import Tui_Api__Privilege__Resolver
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry            import Tui_Api__Registry


def _registry():
    return Tui_Api__Registry().register(S3__Tui_Api__Provider(client=S3__AWS__Client__In_Memory().add_bucket('demo-bucket')))


def _resolver(tmp_path):
    return Tui_Api__Privilege__Resolver(creds_catalogue=Creds__Scope__Catalogue(catalogue_path=str(tmp_path / 's.json')))


def test_from_tools_parses_grants():
    loadout = Tui_Api__Loadout__Assembler().from_tools('sg-aws.s3:read, sg-edge.slugs:*')
    assert len(loadout.grants) == 2
    assert str(loadout.grants[0].scope.api)        == 'sg-aws.s3'
    assert str(loadout.grants[1].scope.capability) == '*'


def test_from_workflow_carries_name_and_grants():
    assembler = Tui_Api__Loadout__Assembler()
    workflow  = Schema__Tui_Api__Workflow(name='diagnose', grants=assembler.from_tools('sg-aws.s3:read').grants)
    loadout   = assembler.from_workflow(workflow)
    assert loadout.workflow == 'diagnose' and len(loadout.grants) == 1


def test_granted_actions_filters_by_scope(tmp_path):
    assembler, registry, resolver = Tui_Api__Loadout__Assembler(), _registry(), _resolver(tmp_path)

    read_grant = assembler.from_tools('sg-aws.s3:read')
    granted    = {str(action.name) for _slug, action in assembler.granted_actions(read_grant, registry, resolver)}
    assert granted == {'list_buckets', 'list_objects', 'head_object'}

    write_grant = assembler.from_tools('sg-aws.s3:write')                          # s3 actions need 'read' → write grant covers nothing
    assert assembler.granted_actions(write_grant, registry, resolver) == []

    star_grant = assembler.from_tools('sg-aws.s3:*')                               # whole-API grant covers all
    assert len(assembler.granted_actions(star_grant, registry, resolver)) == 3


def test_skills_markup_includes_granted_provider(tmp_path):
    assembler = Tui_Api__Loadout__Assembler()
    markup    = assembler.skills_markup(assembler.from_tools('sg-aws.s3:read'), _registry(), _resolver(tmp_path))
    assert 'list_objects' in markup
