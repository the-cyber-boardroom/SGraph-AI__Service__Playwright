# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Lambda REPL wiring
# Verifies the full Click-tree path: sg → aws → lambda → <function> → verb.
# Uses the REPL helper functions directly to simulate REPL navigation.
# No AWS calls needed — uses in-memory resolver.
# ═══════════════════════════════════════════════════════════════════════════════

import typer.main

from sgraph_ai_service_playwright__cli.aws.cli.Cli__Aws import app as aws_app
from sgraph_ai_service_playwright__cli.aws.lambda_.cli.Lambda__Click__Group import Lambda__App__Group, VERB_ORDER
from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__Name__Resolver import Lambda__Name__Resolver
from sgraph_ai_service_playwright__cli.aws.lambda_.primitives.Safe_Str__Lambda__Name import Safe_Str__Lambda__Name
from sgraph_ai_service_playwright__cli.aws.lambda_.schemas.Schema__Lambda__Deploy__Request import Schema__Lambda__Deploy__Request
from tests.unit.sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__AWS__Client__In_Memory import (
    Lambda__AWS__Client__In_Memory,
    Lambda__Deployer__In_Memory,
)

_FUNCTIONS = ['sg-compute-vault-publish-waker', 'sp-playwright-cli-dev']


def _make_app_with_functions() -> Lambda__App__Group:
    client = Lambda__AWS__Client__In_Memory()
    for name in _FUNCTIONS:
        dep = Lambda__Deployer__In_Memory(aws_client=client)
        req = Schema__Lambda__Deploy__Request(
            name        = Safe_Str__Lambda__Name(name),
            folder_path = '/tmp/fake',
            handler     = 'h:h',
            role_arn    = 'arn:aws:iam::123456789012:role/r',
        )
        dep.deploy_from_folder(req)
    resolver = Lambda__Name__Resolver(aws_client=client)
    return Lambda__App__Group(resolver=resolver)


class TestREPLTree:

    def test_lambda_accessible_under_aws(self):
        click_aws = typer.main.get_command(aws_app)
        lambda_cmd = click_aws.get_command(None, 'lambda')
        assert lambda_cmd is not None
        assert isinstance(lambda_cmd, Lambda__App__Group)

    def test_list_in_lambda_commands(self):
        lambda_app = _make_app_with_functions()
        cmds       = lambda_app.list_commands(None)
        assert 'list' in cmds

    def test_function_names_in_lambda_commands(self):
        lambda_app = _make_app_with_functions()
        cmds       = lambda_app.list_commands(None)
        for fn in _FUNCTIONS:
            assert fn in cmds, f'{fn!r} missing from list_commands'

    def test_prefix_navigation_to_function(self):
        lambda_app   = _make_app_with_functions()
        fn_group     = lambda_app.get_command(None, 'sg-compute')  # prefix
        assert fn_group is not None
        assert 'waker' in fn_group.name

    def test_verb_accessible_under_function(self):
        lambda_app   = _make_app_with_functions()
        fn_group     = lambda_app.get_command(None, 'waker')
        assert fn_group is not None
        for verb in VERB_ORDER:
            cmd = fn_group.get_command(None, verb)
            assert cmd is not None, f'Verb {verb!r} missing from function group'

    def test_verb_list_matches_registry(self):
        lambda_app = _make_app_with_functions()
        fn_group   = lambda_app.get_command(None, 'sp-playwright')  # prefix match
        assert fn_group is not None
        cmds       = fn_group.list_commands(None)
        assert set(cmds) == set(VERB_ORDER)
