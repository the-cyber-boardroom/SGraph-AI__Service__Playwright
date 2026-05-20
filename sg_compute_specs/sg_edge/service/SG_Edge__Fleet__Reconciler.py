# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: SG_Edge__Fleet__Reconciler
# The Edge Waker's convergent control loop (brief 02 — "no locking"). It reads
# ground truth from DNS (via SG_Edge__DNS__Helper) and reconciles the proxy fleet
# toward a target count. There is NO coordinator: two racing invocations cost one
# extra proxy for a few minutes, which idle-teardown reclaims. All operations are
# idempotent (UPSERT A records, terminate-by-ip).
#
# Three entry points:
#   ensure_booting()  cold-cold failover — boot one proxy if the fleet is empty
#   reconcile()       scheduled scale check — converge proxy count to the target
#   idle_check()      scheduled teardown — track zero_streak in the _state TXT,
#                     drain the fleet once the idle threshold is reached
#
# Side-effecting AWS work is behind injected seams so the loop is unit-tested
# against the in-memory DNS fake with no mocks:
#   _launcher   () -> Schema__SG_Edge__Proxy   launch one proxy, return when ready
#   _terminator (ip: str) -> None              find instance by ip + terminate
#   _now        () -> int                       unix-ts source (deterministic tests)
# ═══════════════════════════════════════════════════════════════════════════════

import time
from typing import Callable, Optional

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute_specs.sg_edge.primitives.Safe_Str__SG_Edge__Parent_Domain     import Safe_Str__SG_Edge__Parent_Domain
from sg_compute_specs.sg_edge.schemas.Schema__SG_Edge__Proxy                  import Schema__SG_Edge__Proxy
from sg_compute_specs.sg_edge.schemas.Schema__SG_Edge__State__Record          import Schema__SG_Edge__State__Record
from sg_compute_specs.sg_edge.service.SG_Edge__DNS__Helper                    import SG_Edge__DNS__Helper

EDGE_PROXY_TARGET_COUNT  = 2                                                         # static for MVP (brief 02 — auto-scale is Phase 3)
IDLE_TEARDOWN_THRESHOLD  = 3                                                         # consecutive zero-vault idle-checks before teardown (~15 min at 5-min cadence)


class SG_Edge__Fleet__Reconciler(Type_Safe):
    dns            : SG_Edge__DNS__Helper
    parent         : Safe_Str__SG_Edge__Parent_Domain = ''
    target_count   : int                              = EDGE_PROXY_TARGET_COUNT
    idle_threshold : int                              = IDLE_TEARDOWN_THRESHOLD
    _launcher      : Optional[Callable]               = None                         # () -> Schema__SG_Edge__Proxy
    _terminator    : Optional[Callable]               = None                         # (ip: str) -> None
    _now           : Optional[Callable]               = None                         # () -> int

    # ── target decision ─────────────────────────────────────────────────────────

    def desired_target(self) -> int:                                                 # active vaults drive the steady-state target
        if self.dns.active_slug_count(self.parent) == 0:
            return 0
        return int(self.target_count)

    # ── entry points ─────────────────────────────────────────────────────────────

    def ensure_booting(self) -> Optional[Schema__SG_Edge__Proxy]:                    # cold-cold: boot one proxy if the fleet is empty
        if self.dns.proxy_count(self.parent) > 0:
            return None                                                              # already up (or booting via a racing invocation) — no-op
        return self._launch_and_register()

    def reconcile(self) -> dict:                                                      # scheduled scale check — converge toward desired_target
        current  = self.dns.proxy_count(self.parent)
        target   = self.desired_target()
        launched = []
        if current < target:
            for _ in range(target - current):
                launched.append(str(self._launch_and_register().instance_id))
        return {'current'  : current,
                'target'   : target,
                'launched' : launched}

    def idle_check(self) -> dict:                                                     # scheduled teardown — zero_streak in the _state TXT
        active = self.dns.active_slug_count(self.parent)
        if active > 0:                                                                # traffic present — reset the streak
            self._write_streak(0)
            return {'active': active, 'zero_streak': 0, 'action': 'reset'}

        streak = int(self.dns.read_state(self.parent).zero_streak) + 1
        if streak >= int(self.idle_threshold):                                        # idle long enough — drain the fleet
            drained = self._drain_all()
            self._write_streak(0)
            return {'active': 0, 'zero_streak': 0, 'action': 'teardown', 'drained': drained}

        self._write_streak(streak)
        return {'active': 0, 'zero_streak': streak, 'action': 'increment'}

    # ── internals ────────────────────────────────────────────────────────────────

    def _launch_and_register(self) -> Schema__SG_Edge__Proxy:                        # launcher returns a health-green proxy; we publish its IP
        proxy = self._launch()
        self.dns.add_proxy_ip(self.parent, str(proxy.ip))
        return proxy

    def _drain_all(self) -> list:                                                     # terminate every proxy and clear its A-record value
        drained = []
        for ip in list(self.dns.list_proxy_ips(self.parent)):
            self._terminate(ip)
            self.dns.remove_proxy_ip(self.parent, ip)
            drained.append(ip)
        return drained

    def _write_streak(self, streak: int) -> None:
        self.dns.write_state(self.parent, Schema__SG_Edge__State__Record(zero_streak=streak, updated=self._ts()))

    def _ts(self) -> int:
        return self._now() if self._now else int(time.time())

    def _launch(self) -> Schema__SG_Edge__Proxy:
        if self._launcher is None:
            raise NotImplementedError('SG_Edge__Fleet__Reconciler._launcher seam not wired '
                                      '(the deployed Edge Waker injects an EC2-backed launcher; '
                                      'unit tests inject a fake)')
        return self._launcher()

    def _terminate(self, ip: str) -> None:
        if self._terminator is None:
            raise NotImplementedError('SG_Edge__Fleet__Reconciler._terminator seam not wired')
        self._terminator(ip)
