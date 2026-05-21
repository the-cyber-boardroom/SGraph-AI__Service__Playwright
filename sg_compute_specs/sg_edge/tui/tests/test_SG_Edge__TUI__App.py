# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: pilot tests for the composite dashboard app
# Drives the real tabbed app with in-memory sources — no mocks. Verifies the tab
# bar mounts on Deployment, 1..6 switch tabs (and render), ↑/↓ select on the Topology
# and Slug tabs, the Events tab accumulates a Differ event after a change + poll, and
# q quits. @skipUnless textual; the app is imported lazily so this loads on 3.11.
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

from sg_compute.host_plane.pods.service.Pod__Runtime                    import Pod__Runtime
from sg_compute.host_plane.pods.schemas.Schema__Pod__List               import Schema__Pod__List
from sg_compute_specs.sg_edge.local.Local__Edge__Stack                  import Local__Edge__Stack
from sg_compute_specs.sg_edge.tui.source.SG_Edge__TUI__Local_Source     import SG_Edge__TUI__Local_Source
from sg_compute_specs.sg_edge.tui.source.SG_Edge__TUI__AWS_Source       import SG_Edge__TUI__AWS_Source
from sg_compute_specs.sg_edge.tui.source.SG_Edge__TUI__Docker__Source   import SG_Edge__TUI__Docker__Source
from sg_compute_specs.sg_edge.service.SG_Edge__DNS__Helper              import SG_Edge__DNS__Helper
from tests.unit.sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client__In_Memory import Route53__AWS__Client__In_Memory


class _Empty_Runtime(Pod__Runtime):
    def list(self) -> Schema__Pod__List:
        return Schema__Pod__List()


@skipUnless(HAS_TEXTUAL, 'textual not installed')
class test_SG_Edge__TUI__App(TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='sg-edge-tui-app-')
        stack    = Local__Edge__Stack(state_dir=self.dir)
        stack.setup()
        stack.register('alice')
        stack.register('bob')
        self.local_source  = SG_Edge__TUI__Local_Source(stack=stack)
        self.aws_source    = SG_Edge__TUI__AWS_Source(dns=SG_Edge__DNS__Helper(route53=Route53__AWS__Client__In_Memory()))
        self.docker_source = SG_Edge__TUI__Docker__Source(runtime=_Empty_Runtime())

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def app(self):
        from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__App import SG_Edge__TUI__App
        return SG_Edge__TUI__App(local_source=self.local_source, aws_source=self.aws_source,
                                 docker_source=self.docker_source, refresh_seconds=0)

    def test_tabs_switch_and_render(self):
        asyncio.run(self.scenario_tabs())

    async def scenario_tabs(self):
        app = self.app()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.active_tab == 'deployment'                                    # default tab
            assert app.local_snapshot is not None
            await pilot.press('3')                                                   # → Compare
            await pilot.pause()
            assert app.active_tab == 'compare'
            assert app.aws_snapshot is not None                                      # compare fetched the AWS side
            await pilot.press('6')                                                   # → Docker
            await pilot.pause()
            assert app.active_tab == 'docker'

    def test_topology_and_slug_navigation(self):
        asyncio.run(self.scenario_nav())

    async def scenario_nav(self):
        app = self.app()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press('2')                                                   # → Topology
            await pilot.pause()
            assert app.topo_index == 0
            await pilot.press('down')
            assert app.topo_index == 1
            await pilot.press('down')                                                # clamp (2 slugs)
            assert app.topo_index == 1
            await pilot.press('4')                                                   # → Slug
            await pilot.pause()
            assert app.slug_focus in ('alice', 'bob')
            first = app.slug_focus
            await pilot.press('down')
            assert app.slug_focus != first or len(app.slug_names()) == 1

    def test_events_tab_accumulates_after_change(self):
        asyncio.run(self.scenario_events())

    async def scenario_events(self):
        app = self.app()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press('5')                                                   # → Events (seeded, empty)
            await pilot.pause()
            self.local_source.register('carol')
            await pilot.press('r')                                                   # poll → Differ sees carol
            await pilot.pause()
            assert any('carol' in e.detail for e in app.events)
            await pilot.press('q')
            await pilot.pause()
            assert app.exited is True
