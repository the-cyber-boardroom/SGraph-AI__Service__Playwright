# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge local: tests for Local__Edge__Stack + Local__Edge__Proxy
# Drives the local edge against a file-backed DNS in a temp state dir (no AWS, no
# mocks). Covers the full lifecycle (setup → register → request → check → teardown),
# the three proxy outcomes (welcome / dormant / not-recognised), persistence across
# fresh stack instances, and the deviation findings from check().
# ═══════════════════════════════════════════════════════════════════════════════

import shutil
import tempfile
from unittest import TestCase

from sg_compute_specs.sg_edge.local.Local__Edge__Stack                     import Local__Edge__Stack
from sg_compute_specs.sg_edge.local.Local__Route53__Client                 import Local__Route53__Client
from sg_compute_specs.sg_edge.local.enums.Enum__Local__Edge__Response_Kind import Enum__Local__Edge__Response_Kind
from sg_compute_specs.sg_edge.local.enums.Enum__Local__Edge__Severity      import Enum__Local__Edge__Severity


class test_Local__Edge__Stack(TestCase):

    def setUp(self):
        self.dir   = tempfile.mkdtemp(prefix='sg-edge-test-')
        self.stack = Local__Edge__Stack(state_dir=self.dir)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def test_setup__deploys_zone_wildcard_and_proxy(self):
        assert self.stack.is_deployed() is False
        st = self.stack.setup()
        assert st.deployed       is True
        assert st.zone_exists    is True
        assert st.wildcard       is True
        assert list(st.proxy_ips) == ['127.0.0.1']

    def test_setup__is_idempotent(self):
        self.stack.setup()
        st = self.stack.setup()
        assert list(st.proxy_ips) == ['127.0.0.1']                                   # one proxy, not two

    def test_teardown__removes_state(self):
        self.stack.setup()
        assert self.stack.teardown() is True
        assert self.stack.is_deployed() is False
        assert self.stack.status().zone_exists is False

    # ── registration + proxy outcomes ──────────────────────────────────────────

    def test_register_then_request__welcome(self):
        self.stack.setup()
        self.stack.register('alice')
        resp = self.stack.request('alice')
        assert resp.status_code == 200
        assert resp.kind        == Enum__Local__Edge__Response_Kind.WELCOME
        assert 'Welcome to the alice vault' in resp.body
        assert resp.backend     == '127.0.0.1:8080'

    def test_request_unknown__not_recognised(self):
        self.stack.setup()
        resp = self.stack.request('ghost')
        assert resp.status_code == 404
        assert resp.kind        == Enum__Local__Edge__Response_Kind.NOT_RECOGNISED
        assert resp.backend     == ''

    def test_register_no_backend__dormant(self):
        self.stack.setup()
        self.stack.register('bob', with_backend=False)
        resp = self.stack.request('bob')
        assert resp.status_code == 503
        assert resp.kind        == Enum__Local__Edge__Response_Kind.DORMANT

    def test_unregister__stops_resolving(self):
        self.stack.setup()
        self.stack.register('carol')
        assert self.stack.request('carol').kind == Enum__Local__Edge__Response_Kind.WELCOME
        assert self.stack.unregister('carol') is True
        assert self.stack.request('carol').kind == Enum__Local__Edge__Response_Kind.NOT_RECOGNISED

    def test_unregister_absent__returns_false(self):
        self.stack.setup()
        assert self.stack.unregister('nobody') is False

    # ── persistence across fresh instances (separate CLI processes) ─────────────

    def test_state_persists_across_instances(self):
        self.stack.setup()
        self.stack.register('dave')
        fresh = Local__Edge__Stack(state_dir=self.dir)                                # mimics a separate `sg edge local` process
        assert fresh.is_deployed() is True
        assert fresh.request('dave').kind == Enum__Local__Edge__Response_Kind.WELCOME

    # ── status + check ───────────────────────────────────────────────────────────

    def test_status__lists_registered_and_dormant_slugs(self):
        self.stack.setup()
        self.stack.register('alice')
        self.stack.register('bob', with_backend=False)
        st    = self.stack.status()
        slugs = {s.slug: (s.has_a, s.has_txt) for s in st.slugs}
        assert slugs == {'alice': (True, True), 'bob': (True, False)}

    def test_check__clean_when_healthy(self):
        self.stack.setup()
        self.stack.register('alice')
        st  = self.stack.check()
        bad = [i for i in st.issues if i.severity in (Enum__Local__Edge__Severity.WARN,
                                                      Enum__Local__Edge__Severity.ERROR)]
        assert bad == []

    def test_check__flags_dormant_as_info(self):
        self.stack.setup()
        self.stack.register('bob', with_backend=False)
        st   = self.stack.check()
        infos = [i for i in st.issues if i.severity == Enum__Local__Edge__Severity.INFO]
        assert any('dormant' in i.message for i in infos)

    def test_check__flags_orphan_backend_as_warn(self):
        self.stack.setup()
        client = Local__Route53__Client(dns_path=self.stack.dns_path())              # write a TXT with no matching A (orphan backend)
        from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type import Enum__Route53__Record_Type
        client.upsert_record(self.stack.parent, f'_sg.orphan.{self.stack.parent}',
                             Enum__Route53__Record_Type.TXT,
                             ['"v=1;ip=127.0.0.1;port=8080;type=ec2;launched=1"'], ttl=30)
        st    = self.stack.check()
        warns = [i for i in st.issues if i.severity == Enum__Local__Edge__Severity.WARN]
        assert any('orphan' in i.message for i in warns)

    def test_check__not_deployed_is_info(self):
        st = self.stack.check()
        assert st.deployed is False
        assert any(i.area == 'stack' for i in st.issues)


class test_Local__Edge__Usecases(TestCase):

    def test_run_all__every_usecase_passes(self):
        from sg_compute_specs.sg_edge.local.usecases.Local__Edge__Usecases import Local__Edge__Usecases
        results = Local__Edge__Usecases().run_all()
        assert len(results) == 6
        for r in results:
            assert r.passed is True, f'{r.id} failed: {[(s.label, s.ok) for s in r.steps if not s.ok]}'

    def test_run_unknown__raises(self):
        from sg_compute_specs.sg_edge.local.usecases.Local__Edge__Usecases import Local__Edge__Usecases
        with self.assertRaises(ValueError):
            Local__Edge__Usecases().run('UC-99')

    def test_run_single__by_id(self):
        from sg_compute_specs.sg_edge.local.usecases.Local__Edge__Usecases import Local__Edge__Usecases
        result = Local__Edge__Usecases().run('UC-02')
        assert result.id     == 'UC-02'
        assert result.passed is True
