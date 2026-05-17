# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Lambda__Click__Group
# Covers: list_commands, get_command, VERB_REGISTRY, fuzzy resolution,
#         ambiguity error, not-found error, help output.
# Uses in-memory resolver so no AWS calls needed.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
from click.testing                                                                import CliRunner

from sgraph_ai_service_playwright__cli.aws.lambda_.cli.Lambda__Click__Group       import Lambda__App__Group, VERB_REGISTRY, VERB_ORDER
from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__Name__Resolver import Lambda__Name__Resolver
from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Name import Safe_Str__Lambda__Name
from sgraph_ai_service_playwright__cli.aws.lambda_.schemas.Schema__Lambda__Deploy__Request import Schema__Lambda__Deploy__Request
from tests.unit.sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__AWS__Client__In_Memory import (
    Lambda__AWS__Client__In_Memory,
    Lambda__Deployer__In_Memory,
)

_NAMES = ['sg-compute-vault-publish-waker', 'sg-playwright-dev', 'sp-playwright-cli-dev', 'other-lambda']


def _resolver(names=_NAMES) -> Lambda__Name__Resolver:
    client = Lambda__AWS__Client__In_Memory()
    for name in names:
        dep = Lambda__Deployer__In_Memory(aws_client=client)
        req = Schema__Lambda__Deploy__Request(
            name        = Safe_Str__Lambda__Name(name),
            folder_path = '/tmp/fake',
            handler     = 'h:h',
            role_arn    = 'arn:aws:iam::123456789012:role/r',
        )
        dep.deploy_from_folder(req)
    return Lambda__Name__Resolver(aws_client=client)


def _app(names=_NAMES) -> Lambda__App__Group:
    return Lambda__App__Group(resolver=_resolver(names))


# ═══════════════════════════════════════════════════════════════════════════════
class TestVerbRegistry:

    def test_all_verbs_present(self):
        for verb in VERB_ORDER:
            assert verb in VERB_REGISTRY, f'Missing verb: {verb}'

    def test_verb_registry_count(self):
        assert len(VERB_REGISTRY) == len(VERB_ORDER)


# ═══════════════════════════════════════════════════════════════════════════════
class TestLambdaAppGroupListCommands:

    def test_list_in_top_level(self):
        app     = _app()
        ctx     = None
        cmds    = app.list_commands(ctx)
        assert 'list' in cmds

    def test_function_names_in_top_level(self):
        app  = _app()
        cmds = app.list_commands(None)
        for name in _NAMES:
            assert name in cmds

    def test_list_is_first(self):
        app  = _app()
        cmds = app.list_commands(None)
        assert cmds[0] == 'list'


# ═══════════════════════════════════════════════════════════════════════════════
class TestGetCommand:

    def test_get_list_command(self):
        app = _app()
        cmd = app.get_command(None, 'list')
        assert cmd is not None
        assert cmd.name == 'list'

    def test_get_function_group_by_exact_name(self):
        app   = _app()
        group = app.get_command(None, 'sg-compute-vault-publish-waker')
        assert group is not None
        assert group.name == 'sg-compute-vault-publish-waker'

    def test_fuzzy_resolve_prefix(self):
        app   = _app()
        group = app.get_command(None, 'sg-compute')   # prefix of waker
        assert group is not None
        assert 'waker' in group.name

    def test_fuzzy_resolve_substring(self):
        app   = _app()
        group = app.get_command(None, 'waker')
        assert group is not None
        assert 'waker' in group.name

    def test_ambiguous_returns_none(self):
        app   = _app()
        group = app.get_command(None, 'sg')            # matches both sg-compute and sp-playwright
        assert group is None                           # resolver prints error, returns None

    def test_not_found_returns_none(self):
        app   = _app()
        group = app.get_command(None, 'xyz-completely-unknown')
        assert group is None


# ═══════════════════════════════════════════════════════════════════════════════
class TestLambdaFunctionGroupVerbs:

    def test_function_group_has_all_verbs(self):
        app   = _app()
        group = app.get_command(None, 'waker')
        assert group is not None
        cmds  = group.list_commands(None)
        for verb in VERB_ORDER:
            assert verb in cmds

    def test_info_verb_accessible(self):
        app   = _app()
        group = app.get_command(None, 'waker')
        assert group is not None
        cmd   = group.get_command(None, 'info')
        assert cmd is not None
        assert cmd.name == 'info'


# ═══════════════════════════════════════════════════════════════════════════════
class TestHelpRendering:

    def test_top_level_help_renders(self):
        runner = CliRunner()
        app    = _app(names=[])
        result = runner.invoke(app, ['--help'])
        assert result.exit_code == 0
        assert 'list' in result.output

    def test_list_help_renders(self):
        runner = CliRunner()
        app    = _app(names=[])
        result = runner.invoke(app, ['list', '--help'])
        assert result.exit_code == 0
        assert '--json' in result.output
