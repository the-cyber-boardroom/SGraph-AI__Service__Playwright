# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: tests for `sg edge tui` CLI
# Exercises the deployment command's no-TTY fallback (CliRunner stdout is not a
# terminal → static ASCII card, no textual needed) and the help surface. Uses the
# _source_factory seam to inject an in-memory Local source over a temp stack — no
# mocks. @skipUnless typer (like the other CLI suites).
# ═══════════════════════════════════════════════════════════════════════════════

import shutil
import tempfile
from unittest import TestCase, skipUnless

try:
    import typer                                                                     # noqa: F401
    from typer.testing import CliRunner
    HAS_TYPER = True
except Exception:
    HAS_TYPER = False

from sg_compute_specs.sg_edge.local.Local__Edge__Stack                  import Local__Edge__Stack
from sg_compute_specs.sg_edge.tui.source.SG_Edge__TUI__Local_Source     import SG_Edge__TUI__Local_Source


@skipUnless(HAS_TYPER, 'typer not installed')
class test_Cli__SG_Edge__Tui(TestCase):

    def setUp(self):
        from sg_compute_specs.sg_edge.tui.cli import Cli__SG_Edge__Tui as mod
        self.mod    = mod
        self.runner = CliRunner()
        self.dir    = tempfile.mkdtemp(prefix='sg-edge-tui-cli-')
        stack = Local__Edge__Stack(state_dir=self.dir)
        stack.setup()
        stack.register('alice')
        self.source         = SG_Edge__TUI__Local_Source(stack=stack)
        mod._source_factory = lambda target, parent: self.source

    def tearDown(self):
        self.mod._source_factory = None
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_deployment__no_tty_falls_back_to_card(self):
        result = self.runner.invoke(self.mod.app, ['deployment'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'SG/Edge' in result.output
        assert 'alice'   in result.output
        assert 'pending' in result.output                                            # honest pending panes survive into the card

    def test_help_lists_commands(self):
        result = self.runner.invoke(self.mod.app, ['--help'])
        assert result.exit_code == 0
        for cmd in ('deployment', 'topology', 'compare'):
            assert cmd in result.output, cmd

    def test_topology__no_tty_falls_back_to_card(self):
        result = self.runner.invoke(self.mod.app, ['topology'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'SG/Edge' in result.output
        assert 'alice'   in result.output

    def test_compare__no_tty_falls_back_to_plain_diff(self):
        from tests.unit.sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client__In_Memory import Route53__AWS__Client__In_Memory
        from sg_compute_specs.sg_edge.service.SG_Edge__DNS__Helper             import SG_Edge__DNS__Helper
        from sg_compute_specs.sg_edge.tui.source.SG_Edge__TUI__AWS_Source      import SG_Edge__TUI__AWS_Source
        r53    = Route53__AWS__Client__In_Memory()
        r53.seed_zone('edge.sg-labs.app')
        aws    = SG_Edge__TUI__AWS_Source(dns=SG_Edge__DNS__Helper(route53=r53), parent_zone='edge.sg-labs.app')
        self.mod._compare_sources_factory = lambda lp, ap: (self.source, aws)        # local has alice; aws empty
        try:
            result = self.runner.invoke(self.mod.app, ['compare'], catch_exceptions=False)
        finally:
            self.mod._compare_sources_factory = None
        assert result.exit_code == 0
        assert 'Local vs Edge' in result.output
        assert 'slug:alice'    in result.output                                      # alice present locally, absent on edge
        assert 'local only'    in result.output
        assert '[green]'       not in result.output                                  # plain (no markup) in the no-TTY path
