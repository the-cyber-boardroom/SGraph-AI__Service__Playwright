# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate — Phase__Timer
# Accumulates per-phase timing records via a context-manager API.
# progress_cb, if set, is called with (name, status, detail='') on enter+exit.
# _Phase__CM is an internal helper — plain Python, not Type_Safe.
# ═══════════════════════════════════════════════════════════════════════════════

import time
from datetime import datetime, timezone

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_app.fargate.collections.List__Schema__Phase__Result import List__Schema__Phase__Result
from sg_compute_specs.vault_app.fargate.enums.Enum__VAF__Phase__Status          import Enum__VAF__Phase__Status
from sg_compute_specs.vault_app.fargate.schemas.Schema__Phase__Result           import Schema__Phase__Result


class _Phase__CM:                                                                # context manager — internal, not exported
    def __init__(self, timer, name: str):
        self.timer   = timer
        self.name    = name
        self._t0     = None
        self._result = None

    def __enter__(self):
        self._t0 = time.monotonic()
        self._result = Schema__Phase__Result(
            name       = self.name,
            status     = Enum__VAF__Phase__Status.RUNNING,
            started_at = datetime.now(timezone.utc).isoformat(),
        )
        if self.timer.progress_cb:
            self.timer.progress_cb(self.name, Enum__VAF__Phase__Status.RUNNING)
        return self._result

    def __exit__(self, exc_type, exc, tb):
        duration_ms = int((time.monotonic() - self._t0) * 1000)
        if exc_type is None:
            self._result.status      = Enum__VAF__Phase__Status.OK
            self._result.duration_ms = duration_ms
        else:
            self._result.status      = Enum__VAF__Phase__Status.ERROR
            self._result.duration_ms = duration_ms
            self._result.error       = str(exc)
        if self.timer.results is None:
            self.timer.results = List__Schema__Phase__Result()
        self.timer.results.append(self._result)
        if self.timer.progress_cb:
            self.timer.progress_cb(self.name, self._result.status,
                                   self._result.detail)
        return False                                                              # never swallow exceptions


class Phase__Timer(Type_Safe):
    results     : List__Schema__Phase__Result = None                             # accumulated phase records
    progress_cb : object                      = None                             # callable(name, status, detail='') or None

    def phase(self, name: str) -> _Phase__CM:                                   # returns a context manager for one named phase
        return _Phase__CM(timer=self, name=name)

    def total_ms(self) -> int:                                                   # sum of all recorded phase durations
        return int(sum(r.duration_ms for r in (self.results or [])))

    def cumulative_through(self, phase_name: str) -> int:                       # ms from first phase start through end of phase_name (inclusive)
        total = 0
        for r in (self.results or []):
            total += r.duration_ms
            if r.name == phase_name:
                return total
        return 0                                                                 # phase_name not found

    def result_for(self, phase_name: str):                                       # Schema__Phase__Result for phase_name, or None
        for r in (self.results or []):
            if r.name == phase_name:
                return r
        return None
