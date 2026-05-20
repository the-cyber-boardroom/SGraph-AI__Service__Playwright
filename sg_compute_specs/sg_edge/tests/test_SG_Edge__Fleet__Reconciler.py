# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: tests for SG_Edge__Fleet__Reconciler
# Drives the convergent control loop against the in-memory Route 53 fake with
# fake launcher / terminator / clock seams (no mocks, no patches).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from tests.unit.sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client__In_Memory import Route53__AWS__Client__In_Memory
from sg_compute_specs.sg_edge.schemas.Schema__SG_Edge__Proxy        import Schema__SG_Edge__Proxy
from sg_compute_specs.sg_edge.service.SG_Edge__DNS__Helper          import SG_Edge__DNS__Helper
from sg_compute_specs.sg_edge.service.SG_Edge__Fleet__Reconciler    import SG_Edge__Fleet__Reconciler

PARENT = 'cv.sgraph.ai'


class test_SG_Edge__Fleet__Reconciler(TestCase):

    def setUp(self):
        self.r53 = Route53__AWS__Client__In_Memory()
        self.r53.seed_zone(PARENT)
        self.dns        = SG_Edge__DNS__Helper(route53=self.r53)
        self._n         = 0
        self.terminated = []
        self.reconciler = SG_Edge__Fleet__Reconciler(dns            = self.dns               ,
                                                     parent         = PARENT                 ,
                                                     _launcher      = lambda: self._fake_launch()  ,
                                                     _terminator    = lambda ip: self._fake_term(ip),
                                                     _now           = lambda: 1000           )

    def _fake_launch(self) -> Schema__SG_Edge__Proxy:
        self._n += 1
        return Schema__SG_Edge__Proxy(instance_id=f'i-{self._n:017x}', ip=f'10.0.0.{self._n}')

    def _fake_term(self, ip):
        self.terminated.append(ip)

    def _seed_vault(self, slug):                                                     # make active_slug_count > 0
        self.r53.seed_record(PARENT, f'_sg.{slug}.{PARENT}', 'TXT',
                             ['"v=1;ip=10.9.9.9;port=8080;type=ec2;launched=1747700000"'])

    # ── ensure_booting (cold-cold) ──────────────────────────────────────────────

    def test_ensure_booting__boots_one_when_empty(self):
        proxy = self.reconciler.ensure_booting()
        assert proxy is not None
        assert self.dns.proxy_count(PARENT)      == 1
        assert str(proxy.ip) in self.dns.list_proxy_ips(PARENT)

    def test_ensure_booting__noop_when_fleet_present(self):
        self.reconciler.ensure_booting()
        assert self.reconciler.ensure_booting() is None                              # already up
        assert self.dns.proxy_count(PARENT) == 1

    # ── desired_target ──────────────────────────────────────────────────────────

    def test_desired_target__zero_when_no_vaults(self):
        assert self.reconciler.desired_target() == 0

    def test_desired_target__target_count_when_vaults_active(self):
        self._seed_vault('alice')
        assert self.reconciler.desired_target() == self.reconciler.target_count

    # ── reconcile (scheduled scale check) ───────────────────────────────────────

    def test_reconcile__no_vaults_launches_nothing(self):
        result = self.reconciler.reconcile()
        assert result['target']   == 0
        assert result['launched'] == []
        assert self.dns.proxy_count(PARENT) == 0

    def test_reconcile__launches_up_to_target(self):
        self._seed_vault('alice')
        result = self.reconciler.reconcile()
        assert result['target'] == 2
        assert len(result['launched']) == 2
        assert self.dns.proxy_count(PARENT) == 2

    def test_reconcile__noop_when_at_target(self):
        self._seed_vault('alice')
        self.reconciler.reconcile()                                                  # brings fleet to 2
        result = self.reconciler.reconcile()                                         # already at target
        assert result['launched'] == []
        assert self.dns.proxy_count(PARENT) == 2

    # ── idle_check (teardown counter) ────────────────────────────────────────────

    def test_idle_check__resets_when_active(self):
        self._seed_vault('alice')
        result = self.reconciler.idle_check()
        assert result['action']      == 'reset'
        assert result['zero_streak'] == 0

    def test_idle_check__increments_below_threshold(self):
        r1 = self.reconciler.idle_check()
        assert r1 == {'active': 0, 'zero_streak': 1, 'action': 'increment'}
        r2 = self.reconciler.idle_check()
        assert r2['zero_streak'] == 2
        assert r2['action']      == 'increment'

    def test_idle_check__tears_down_at_threshold(self):
        self.reconciler.ensure_booting()                                             # one proxy up
        ip = self.dns.list_proxy_ips(PARENT)[0]
        self.reconciler.idle_check()                                                 # streak 1
        self.reconciler.idle_check()                                                 # streak 2
        result = self.reconciler.idle_check()                                        # streak 3 == threshold -> teardown
        assert result['action']  == 'teardown'
        assert result['drained'] == [ip]
        assert self.terminated   == [ip]
        assert self.dns.proxy_count(PARENT)              == 0
        assert int(self.dns.read_state(PARENT).zero_streak) == 0                     # streak reset after teardown

    def test_idle_check__teardown_drains_whole_fleet(self):
        self.dns.add_proxy_ip(PARENT, '10.0.0.1')                                    # two proxies up, no active vaults
        self.dns.add_proxy_ip(PARENT, '10.0.0.2')
        self.reconciler.idle_threshold = 1                                           # tear down on the first idle check
        result = self.reconciler.idle_check()
        assert result['action']           == 'teardown'
        assert sorted(result['drained'])  == ['10.0.0.1', '10.0.0.2']
        assert sorted(self.terminated)    == ['10.0.0.1', '10.0.0.2']
        assert self.dns.proxy_count(PARENT) == 0
