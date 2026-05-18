# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__SG__Repl dynamic-group navigation
#
# 2026-05-18: `lambda` at `sg/aws>` does nothing (no help, no navigation).
#
# Root cause: _click_node / _children used node.commands.get() / .items()
# directly — these only cover commands registered via add_command(). The
# lambda group is injected dynamically via _AwsGroup.get_command() / .list_commands()
# and so was invisible to the REPL's tree walker.
#
# Fix: _click_node now uses click's get_command() API; _children uses
# list_commands() + get_command(). Lambda__App__Group also gained
# no_args_is_help=True so direct invocation shows help.
# ═══════════════════════════════════════════════════════════════════════════════

import click
import typer
from typer.core import TyperGroup
from unittest import TestCase

from sg_compute.cli.Cli__SG__Repl import _click_node, _children, _is_group, _match


# ── synthetic tree with a dynamically injected command ───────────────────────

class _FakeCmd(click.Group):                                                     # simulates Lambda__App__Group — injected via get_command, not add_command
    def __init__(self):
        super().__init__(name='dynamic', no_args_is_help=True)
        self.add_command(click.Command('sub'), 'sub')                            # one real child

    def list_commands(self, ctx):
        return ['sub', 'dyn-child']                                              # dyn-child: not in .commands

    def get_command(self, ctx, name):
        if name == 'sub':
            return self.commands['sub']
        if name == 'dyn-child':
            return click.Command('dyn-child')
        return None


class _DynGroup(TyperGroup):                                                     # simulates _AwsGroup pattern
    def list_commands(self, ctx):
        base = list(super().list_commands(ctx))
        if 'dynamic' not in base:
            base = sorted(set(base + ['dynamic']))
        return base

    def get_command(self, ctx, name):
        if name == 'dynamic':
            return _FakeCmd()
        return super().get_command(ctx, name)


def _build_dynamic_tree() -> typer.Typer:
    root = typer.Typer(name='sg', no_args_is_help=True)
    sub  = typer.Typer(name='sub', cls=_DynGroup)

    @sub.command('static')
    def _static(): pass

    root.add_typer(sub, name='sub')
    return root


# ── tests ─────────────────────────────────────────────────────────────────────

class test_click_node_dynamic_group(TestCase):

    def setUp(self):
        self.app = _build_dynamic_tree()

    def test__static_command_walkable(self):                                     # baseline — normal commands must still work
        node = _click_node(self.app, ['sub'])
        assert node is not None

    def test__dynamic_command_walkable(self):                                    # _click_node must use get_command(), not .commands.get()
        node = _click_node(self.app, ['sub', 'dynamic'])
        assert node is not None, "'dynamic' not found via get_command() API"
        assert isinstance(node, _FakeCmd)

    def test__missing_command_returns_none(self):
        assert _click_node(self.app, ['sub', 'no-such']) is None

    def test__too_deep_returns_none(self):
        assert _click_node(self.app, ['sub', 'dynamic', 'sub', 'extra']) is None


class test_children_dynamic_group(TestCase):

    def setUp(self):
        self.app = _build_dynamic_tree()

    def test__static_command_in_children(self):                                  # normal commands still visible
        kids = _children(self.app, ['sub'])
        assert 'static' in kids

    def test__dynamic_command_in_children(self):                                 # _children must use list_commands(), not .commands.items()
        kids = _children(self.app, ['sub'])
        assert 'dynamic' in kids, "'dynamic' missing from _children — list_commands() not being used"

    def test__dyn_child_visible_inside_dynamic_node(self):                       # children of the dynamic node itself
        kids = _children(self.app, ['sub', 'dynamic'])
        assert 'sub' in kids
        assert 'dyn-child' in kids


class test_is_group_dynamic(TestCase):

    def setUp(self):
        self.app = _build_dynamic_tree()

    def test__dynamic_node_is_a_group(self):
        assert _is_group(self.app, ['sub', 'dynamic'])


class test_match_dynamic_prefix(TestCase):

    def setUp(self):
        self.app = _build_dynamic_tree()

    def test__prefix_matches_dynamic_child(self):
        kids = _children(self.app, ['sub'])
        hits, kind = _match('dyn', kids)
        assert 'dynamic' in hits
        assert kind == 'prefix'

    def test__exact_name_matches_dynamic_child(self):
        kids = _children(self.app, ['sub'])
        hits, kind = _match('dynamic', kids)
        assert hits == ['dynamic']
        assert kind == 'prefix'


# ── real CLI: lambda at sg/aws> ───────────────────────────────────────────────

class test_aws_lambda_navigation(TestCase):

    @classmethod
    def setUpClass(cls):
        from sg_compute.cli.Cli__SG import app as sg_app
        cls.sg_app = sg_app

    def test__lambda_in_aws_children(self):                                      # was missing before the fix
        kids = _children(self.sg_app, ['aws'])
        assert 'lambda' in kids, "'lambda' not visible to REPL — _AwsGroup.list_commands() not used"

    def test__lambda_click_node_is_not_none(self):                               # was None before the fix
        node = _click_node(self.sg_app, ['aws', 'lambda'])
        assert node is not None, "_click_node returned None for 'aws/lambda'"

    def test__lambda_is_a_group(self):
        assert _is_group(self.sg_app, ['aws', 'lambda'])

    def test__lam_prefix_matches_lambda(self):
        kids = _children(self.sg_app, ['aws'])
        hits, kind = _match('lam', kids)
        assert 'lambda' in hits, "'lam' prefix does not match 'lambda'"

    def test__lambda_no_args_is_help(self):                                      # Lambda__App__Group must have no_args_is_help=True
        from sgraph_ai_service_playwright__cli.aws.lambda_.cli.Lambda__Click__Group import Lambda__App__Group
        grp = Lambda__App__Group()
        assert grp.no_args_is_help, "Lambda__App__Group must have no_args_is_help=True"
