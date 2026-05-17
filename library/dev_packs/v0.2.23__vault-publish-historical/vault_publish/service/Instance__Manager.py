# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Instance__Manager
# Lifecycle of the per-slug vault EC2 instances: state, start, stop, idle-timer.
#
# Storage backend: _instances (in-memory dict keyed by slug string), the same
# pattern as Vault__Spec__Writer. The real implementation drives EC2 through
# osbot-aws (never boto3 directly) — start() runs / starts the instance and
# returns while it is PENDING; the instance becomes RUNNING asynchronously after
# boot. Those EC2 calls are the marked seams below; the state-machine logic,
# idempotency and idle-timer arming run here in-memory exactly as they will
# against AWS. mark_ready() simulates the async PENDING → RUNNING transition for
# tests and local composition.
# ═══════════════════════════════════════════════════════════════════════════════

import hashlib

from osbot_utils.type_safe.Type_Safe                         import Type_Safe

from vault_publish.schemas.Enum__Instance__State             import Enum__Instance__State
from vault_publish.schemas.Safe_Str__Instance__Id            import Safe_Str__Instance__Id
from vault_publish.schemas.Safe_Str__Slug                    import Safe_Str__Slug
from vault_publish.schemas.Schema__Instance__Record          import Schema__Instance__Record


class Instance__Manager(Type_Safe):
    _instances : dict                                                        # slug(str) → Schema__Instance__Record

    def record(self, slug: Safe_Str__Slug) -> Schema__Instance__Record:
        key = str(slug)
        rec = self._instances.get(key)
        if rec is None:
            rec = Schema__Instance__Record(slug  = Safe_Str__Slug(key)            ,
                                           state = Enum__Instance__State.UNKNOWN  )
            self._instances[key] = rec
        return rec

    def state(self, slug: Safe_Str__Slug) -> Enum__Instance__State:
        return self.record(slug).state

    def start(self, slug: Safe_Str__Slug) -> tuple:                          # -> (record, was_already_running)
        rec = self.record(slug)
        if rec.state == Enum__Instance__State.RUNNING:
            self.arm_idle_timer(slug)                                        # re-arm on every cold hit
            return rec, True
        if not str(rec.instance_id):
            rec.instance_id = Safe_Str__Instance__Id(self._allocate_instance_id(slug))
        # ── seam: real impl calls osbot-aws ec2 run/start here; it returns while
        #    the instance is PENDING and the instance reaches RUNNING async.
        rec.state = Enum__Instance__State.PENDING
        self.arm_idle_timer(slug)
        return rec, False

    def stop(self, slug: Safe_Str__Slug) -> Schema__Instance__Record:
        rec = self.record(slug)
        # ── seam: real impl calls osbot-aws ec2 stop here.
        rec.state            = Enum__Instance__State.STOPPED
        rec.idle_timer_armed = False
        return rec

    def mark_ready(self, slug: Safe_Str__Slug) -> Schema__Instance__Record:   # simulate async PENDING → RUNNING
        rec = self.record(slug)
        rec.state = Enum__Instance__State.RUNNING
        return rec

    def arm_idle_timer(self, slug: Safe_Str__Slug) -> None:
        # Reuses the existing `sg lc` shutdown-timer pattern: the instance arms an
        # idle-shutdown timer on boot; the waker re-arms it on each cold hit.
        self.record(slug).idle_timer_armed = True

    def _allocate_instance_id(self, slug: Safe_Str__Slug) -> str:
        # deterministic placeholder; the real impl uses the EC2-assigned id.
        return 'i-' + hashlib.sha256(str(slug).encode()).hexdigest()[:17]
