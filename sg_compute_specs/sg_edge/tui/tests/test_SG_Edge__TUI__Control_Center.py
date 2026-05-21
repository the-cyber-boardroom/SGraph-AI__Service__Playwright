# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: tests for the Control Center (render + pilot)
# Pure render (3.11): state / actions-gating / preview / request prediction. Pilot
# (gated): drives the real screen over a real Local source (no mocks) — setup,
# register via the Input, request, unregister-with-confirm — and asserts the AWS
# source greys actions (no mutation, no raise) per the capability gate.
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
import shutil
import tempfile
from unittest import TestCase, skipUnless

from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Slug_State        import Enum__SG_Edge__TUI__Slug_State
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Slug          import Schema__SG_Edge__TUI__Slug
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Snapshot      import Schema__SG_Edge__TUI__Snapshot
from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Control__Render       import (
    control_state_markup, control_actions_markup, control_preview_markup, request_prediction)

try:
    import textual                                                                   # noqa: F401
    HAS_TEXTUAL = True
except Exception:
    HAS_TEXTUAL = False

LIVE    = Enum__SG_Edge__TUI__Slug_State.LIVE
DORMANT = Enum__SG_Edge__TUI__Slug_State.DORMANT


def snap(slugs=(), wildcard=True, zone=True, parent='edge.sg-labs.local'):
    s = Schema__SG_Edge__TUI__Snapshot(parent=parent, captured_at=100, zone_exists=zone, wildcard=wildcard, deployed=zone)
    if zone:
        s.fleet_ips.append('127.0.0.1')
    for name, state in slugs:
        s.slugs.append(Schema__SG_Edge__TUI__Slug(slug=name, fqdn=f'{name}.{parent}', state=state,
                                                  backend_ip='127.0.0.1' if state == LIVE else '',
                                                  backend_port=8080 if state == LIVE else 0))
    return s


class test_control_render(TestCase):

    def test_state(self):
        out = control_state_markup(snap(slugs=[('alice', LIVE)]))
        assert 'STATE' in out and 'deployed' in out and 'fleet' in out
        assert 'not provisioned' in control_state_markup(snap(zone=False))

    def test_actions_gating(self):
        assert 'register' in control_actions_markup(True)
        disabled = control_actions_markup(False, 'pending Slice 5')
        assert 'disabled' in disabled and 'pending Slice 5' in disabled

    def test_request_prediction(self):
        s = snap(slugs=[('alice', LIVE), ('bob', DORMANT)])
        assert '200 welcome' in request_prediction(s, 'alice')
        assert '503'          in request_prediction(s, 'bob')
        assert '404'          in request_prediction(s, 'ghost')

    def test_preview_registered_vs_new(self):
        s = snap(slugs=[('alice', LIVE)])
        assert 'unregister' in control_preview_markup(s, 'alice')                    # known slug → request + unregister
        assert 'register'   in control_preview_markup(s, 'newone')                   # unknown → register


@skipUnless(HAS_TEXTUAL, 'textual not installed')
class test_SG_Edge__TUI__Screen__Control_Center(TestCase):

    def setUp(self):
        from sg_compute_specs.sg_edge.local.Local__Edge__Stack            import Local__Edge__Stack
        from sg_compute_specs.sg_edge.tui.source.SG_Edge__TUI__Local_Source import SG_Edge__TUI__Local_Source
        self.dir    = tempfile.mkdtemp(prefix='sg-edge-cc-')
        self.source = SG_Edge__TUI__Local_Source(stack=Local__Edge__Stack(state_dir=self.dir))   # not set up yet

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def screen(self, source=None):
        from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Screen__Control_Center import SG_Edge__TUI__Screen__Control_Center
        return SG_Edge__TUI__Screen__Control_Center(source=source or self.source, refresh_seconds=0)

    def set_input(self, app, value):
        from textual.widgets import Input
        app.query_one('#cc-slug-input', Input).value = value

    def test_setup_register_request_via_actions(self):
        asyncio.run(self.scenario_actions())

    async def scenario_actions(self):
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.snapshot.deployed is False
            await pilot.press('S')                                                   # setup
            await pilot.pause()
            assert app.snapshot.deployed is True
            self.set_input(app, 'carol')
            await pilot.press('n')                                                   # register the typed slug
            await pilot.pause()
            assert 'carol' in {s.slug for s in app.snapshot.slugs}
            await pilot.press('g')                                                   # request carol (still in the Input) → live
            await pilot.pause()
            assert any('request carol' in e.message for e in app.debug_log.events)

    def test_unregister_requires_confirm(self):
        asyncio.run(self.scenario_confirm())

    async def scenario_confirm(self):
        self.source.setup()
        self.source.register('dave')
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            self.set_input(app, 'dave')
            await pilot.press('u')                                                   # → confirm modal
            await pilot.pause()
            assert len(app.screen_stack) == 2                                        # destructive action gated behind a confirm
            await pilot.press('y')                                                   # confirm
            await pilot.pause()
            assert 'dave' not in {s.slug for s in app.snapshot.slugs}

    def test_aws_target_greys_actions_no_mutation(self):
        asyncio.run(self.scenario_aws())

    async def scenario_aws(self):
        from sg_compute_specs.sg_edge.service.SG_Edge__DNS__Helper          import SG_Edge__DNS__Helper
        from sg_compute_specs.sg_edge.tui.source.SG_Edge__TUI__AWS_Source   import SG_Edge__TUI__AWS_Source
        from tests.unit.sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client__In_Memory import Route53__AWS__Client__In_Memory
        aws = SG_Edge__TUI__AWS_Source(dns=SG_Edge__DNS__Helper(route53=Route53__AWS__Client__In_Memory()))
        app = self.screen(source=aws)
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.source.can_act() is False
            self.set_input(app, 'nope')
            await pilot.press('n')                                                   # gated → notify only, no source call
            await pilot.pause()
            assert app.debug_log.count() == 0                                        # nothing was performed/logged
