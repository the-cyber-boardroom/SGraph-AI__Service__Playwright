# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: pilot tests for Screen 3 (Local vs Edge)
# Drives the real Textual app with TWO in-memory sources — a Local source over a temp
# stack and an AWS source over Route53__AWS__Client__In_Memory — no mocks. Verifies
# both snapshots load, drift is reflected, and q/r work. @skipUnless textual; the
# screen is imported lazily so this module loads on 3.11 without textual.
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
import shutil
import tempfile
from unittest import TestCase, skipUnless

try:
    import textual                                                                   # noqa: F401
    HAS_TEXTUAL = True
except Exception:
    HAS_TEXTUAL = False

from tests.unit.sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client__In_Memory import Route53__AWS__Client__In_Memory
from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type import Enum__Route53__Record_Type
from sg_compute_specs.sg_edge.service.SG_Edge__DNS__Helper                     import SG_Edge__DNS__Helper
from sg_compute_specs.sg_edge.local.Local__Edge__Stack                         import Local__Edge__Stack
from sg_compute_specs.sg_edge.tui.source.SG_Edge__TUI__Local_Source            import SG_Edge__TUI__Local_Source
from sg_compute_specs.sg_edge.tui.source.SG_Edge__TUI__AWS_Source              import SG_Edge__TUI__AWS_Source

A = Enum__Route53__Record_Type.A


@skipUnless(HAS_TEXTUAL, 'textual not installed')
class test_SG_Edge__TUI__Screen__Compare(TestCase):
    AWS_PARENT = 'edge.sg-labs.app'

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='sg-edge-tui-s3-')
        local_stack = Local__Edge__Stack(state_dir=self.dir)
        local_stack.setup()
        local_stack.register('alice')                                                # local has alice
        self.local_source = SG_Edge__TUI__Local_Source(stack=local_stack)

        self.r53 = Route53__AWS__Client__In_Memory()
        self.r53.seed_zone(self.AWS_PARENT)
        helper = SG_Edge__DNS__Helper(route53=self.r53)
        helper.add_proxy_ip(self.AWS_PARENT, '10.0.0.1')
        self.r53.upsert_record(self.AWS_PARENT, f'*.{self.AWS_PARENT}', A, ['10.0.0.1'], ttl=300)
        self.r53.upsert_record(self.AWS_PARENT, f'bob.{self.AWS_PARENT}', A, ['10.0.0.1'], ttl=300)  # edge has bob only
        self.aws_source = SG_Edge__TUI__AWS_Source(dns=helper, parent_zone=self.AWS_PARENT)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def screen(self):
        from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Screen__Compare import SG_Edge__TUI__Screen__Compare
        return SG_Edge__TUI__Screen__Compare(local_source=self.local_source, aws_source=self.aws_source, refresh_seconds=0)

    def test_loads_both_and_reflects_drift(self):
        asyncio.run(self.scenario_drift())

    async def scenario_drift(self):
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.local_snapshot is not None
            assert app.aws_snapshot   is not None
            assert {s.slug for s in app.local_snapshot.slugs} == {'alice'}            # alice local-only
            assert {s.slug for s in app.aws_snapshot.slugs}   == {'bob'}              # bob edge-only

    def test_refresh_and_quit(self):
        asyncio.run(self.scenario_refresh_quit())

    async def scenario_refresh_quit(self):
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            self.local_source.register('carol')                                      # mutate local behind the screen
            await pilot.press('r')
            await pilot.pause()
            assert 'carol' in {s.slug for s in app.local_snapshot.slugs}
            await pilot.press('q')
            await pilot.pause()
            assert app.exited is True
