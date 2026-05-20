# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: tests for the data sources + snapshot builder
# Exercises both sources end-to-end with no mocks: the Local source over a real
# file-backed stack in a temp dir, the AWS source over Route53__AWS__Client__
# In_Memory. Asserts the normalised snapshot (zone/wildcard/fleet/slug-state/issues/
# capabilities) and the action seams (local mutates, AWS raises until Slice 5).
# ═══════════════════════════════════════════════════════════════════════════════

import shutil
import tempfile
from unittest import TestCase

from tests.unit.sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client__In_Memory import Route53__AWS__Client__In_Memory
from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type import Enum__Route53__Record_Type
from sg_compute_specs.sg_edge.service.SG_Edge__DNS__Helper                     import SG_Edge__DNS__Helper
from sg_compute_specs.sg_edge.local.Local__Edge__Stack                         import Local__Edge__Stack
from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Capability         import Enum__SG_Edge__TUI__Capability
from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Slug_State         import Enum__SG_Edge__TUI__Slug_State
from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Target             import Enum__SG_Edge__TUI__Target
from sg_compute_specs.sg_edge.tui.source.SG_Edge__TUI__Local_Source            import SG_Edge__TUI__Local_Source
from sg_compute_specs.sg_edge.tui.source.SG_Edge__TUI__AWS_Source              import SG_Edge__TUI__AWS_Source

A   = Enum__Route53__Record_Type.A
TXT = Enum__Route53__Record_Type.TXT


class test_SG_Edge__TUI__Local_Source(TestCase):

    def setUp(self):
        self.dir    = tempfile.mkdtemp(prefix='sg-edge-tui-')
        self.source = SG_Edge__TUI__Local_Source(stack=Local__Edge__Stack(state_dir=self.dir))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_snapshot__not_deployed(self):
        snap = self.source.snapshot()
        assert snap.target      == Enum__SG_Edge__TUI__Target.LOCAL
        assert snap.deployed    is False
        assert snap.zone_exists is False
        assert Enum__SG_Edge__TUI__Capability.TOPOLOGY in list(snap.capabilities)
        assert Enum__SG_Edge__TUI__Capability.COST     not in list(snap.capabilities)   # pending — never fabricated
        assert any('not provisioned' in str(i.message) for i in snap.issues)

    def test_snapshot__after_setup_and_register(self):
        self.source.setup()
        self.source.register('alice')
        self.source.register('bob', with_backend=False)
        snap = self.source.snapshot()
        assert snap.deployed         is True
        assert snap.zone_exists      is True
        assert snap.wildcard         is True
        assert list(snap.fleet_ips)  == ['127.0.0.1']
        states = {s.slug: str(s.state) for s in snap.slugs}
        assert states == {'alice': 'live', 'bob': 'dormant'}
        alice  = next(s for s in snap.slugs if s.slug == 'alice')
        assert alice.backend_ip   == '127.0.0.1'
        assert alice.backend_port == 8080

    def test_snapshot__clean_when_healthy(self):
        self.source.setup()
        self.source.register('alice')
        snap = self.source.snapshot()
        bad  = [i for i in snap.issues if str(i.severity) in ('warn', 'error')]
        assert bad == []

    def test_can_act_and_actions_delegate(self):
        assert self.source.can_act() is True
        self.source.setup()
        self.source.register('carol')
        assert self.source.request('carol').status_code == 200
        assert self.source.unregister('carol')           is True
        assert self.source.teardown()                    is True


class test_SG_Edge__TUI__AWS_Source(TestCase):
    PARENT = 'edge.sg-labs.app'

    def setUp(self):
        self.r53    = Route53__AWS__Client__In_Memory()
        self.helper = SG_Edge__DNS__Helper(route53=self.r53)
        self.source = SG_Edge__TUI__AWS_Source(dns=self.helper, parent_zone=self.PARENT)

    def provision(self):
        self.r53.seed_zone(self.PARENT)
        self.helper.add_proxy_ip(self.PARENT, '10.0.0.1')
        self.r53.upsert_record(self.PARENT, f'*.{self.PARENT}', A, ['10.0.0.1'], ttl=300)

    def register(self, slug, with_backend=True):
        self.r53.upsert_record(self.PARENT, f'{slug}.{self.PARENT}', A, ['10.0.0.1'], ttl=300)
        if with_backend:
            self.r53.upsert_record(self.PARENT, f'_sg.{slug}.{self.PARENT}', TXT,
                                   ['"v=1;ip=10.0.1.5;port=8080;type=ec2;launched=1"'], ttl=30)

    def test_snapshot__zone_missing(self):
        snap = self.source.snapshot()
        assert snap.target      == Enum__SG_Edge__TUI__Target.AWS
        assert snap.zone_exists is False
        assert snap.deployed    is False                                              # derived from zone presence
        assert any('not provisioned' in str(i.message) for i in snap.issues)

    def test_snapshot__provisioned_with_live_slug(self):
        self.provision()
        self.register('alice')
        snap = self.source.snapshot()
        assert snap.zone_exists     is True
        assert snap.deployed        is True
        assert snap.wildcard        is True
        assert list(snap.fleet_ips) == ['10.0.0.1']
        alice = next(s for s in snap.slugs if s.slug == 'alice')
        assert alice.state        == Enum__SG_Edge__TUI__Slug_State.LIVE
        assert alice.backend_ip   == '10.0.1.5'
        assert alice.backend_port == 8080

    def test_snapshot__orphan_backend_is_warn(self):
        self.provision()
        self.r53.upsert_record(self.PARENT, f'_sg.ghost.{self.PARENT}', TXT,
                               ['"v=1;ip=10.0.1.5;port=8080;type=ec2;launched=1"'], ttl=30)
        snap  = self.source.snapshot()
        ghost = next(s for s in snap.slugs if s.slug == 'ghost')
        assert ghost.state == Enum__SG_Edge__TUI__Slug_State.ORPHAN_BACKEND
        assert any(str(i.severity) == 'warn' and 'orphan' in str(i.message) for i in snap.issues)

    def test_snapshot__missing_wildcard_and_fleet_are_errors(self):
        self.r53.seed_zone(self.PARENT)                                               # zone but nothing else
        snap   = self.source.snapshot()
        errors = {i.area for i in snap.issues if str(i.severity) == 'error'}
        assert 'wildcard' in errors
        assert 'fleet'    in errors

    def test_cannot_act_and_mutations_raise(self):
        assert self.source.can_act() is False
        for call in (lambda: self.source.setup(),
                     lambda: self.source.register('x'),
                     lambda: self.source.unregister('x'),
                     lambda: self.source.request('x'),
                     lambda: self.source.teardown()):
            with self.assertRaises(NotImplementedError):
                call()
