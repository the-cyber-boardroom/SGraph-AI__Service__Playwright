# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Cli__Compute (root app)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                 import TestCase

from typer.testing                                                            import CliRunner

from sg_compute.cli.Cli__Compute                                             import app


class test_Cli__Compute(TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_help_shows_four_subgroups(self):
        result = self.runner.invoke(app, ['--help'])
        assert result.exit_code == 0
        assert 'spec'  in result.output
        assert 'node'  in result.output
        assert 'pod'   in result.output
        assert 'stack' in result.output

    def test_spec_subgroup_reachable(self):
        result = self.runner.invoke(app, ['spec', 'list'])
        assert result.exit_code == 0
        assert 'docker' in result.output

    def test_node_subgroup_reachable(self):
        result = self.runner.invoke(app, ['node', 'list'])
        assert result.exit_code == 0

    def test_pod_subgroup_reachable(self):
        result = self.runner.invoke(app, ['pod', 'list'])
        assert result.exit_code == 0

    def test_stack_subgroup_reachable(self):
        result = self.runner.invoke(app, ['stack', 'list'])
        assert result.exit_code == 0

    def test_node_list_empty_placeholder(self):
        result = self.runner.invoke(app, ['node', 'list'])
        assert result.exit_code == 0
        assert 'No nodes found' in result.output

    def test_pod_list_empty_placeholder(self):
        result = self.runner.invoke(app, ['pod', 'list'])
        assert result.exit_code == 0
        assert 'No pods found' in result.output

    def test_stack_list_empty_placeholder(self):
        result = self.runner.invoke(app, ['stack', 'list'])
        assert result.exit_code == 0
        assert 'No stacks found' in result.output
