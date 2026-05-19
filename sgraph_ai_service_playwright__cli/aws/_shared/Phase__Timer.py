# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/_shared — Phase__Timer
# Accumulates per-phase timing records via a context-manager API.
# progress_cb, if set, is called with (name, status, detail='') on enter+exit.
# _Phase__CM is an internal helper — plain Python, not Type_Safe.
# Mirrors sg_compute_specs/vault_app/fargate Phase__Timer for the aws/* surface
# so the VPC stack provisioner can use the same idiom without importing from
# vault_app/* (forbidden by domain boundaries).
# ═══════════════════════════════════════════════════════════════════════════════

import time
from datetime import datetime, timezone

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.collections.List__Schema__AWS__Phase__Result import List__Schema__AWS__Phase__Result
from sgraph_ai_service_playwright__cli.aws._shared.enums.Enum__AWS__Phase__Status              import Enum__AWS__Phase__Status
from sgraph_ai_service_playwright__cli.aws._shared.schemas.Schema__AWS__Phase__Result          import Schema__AWS__Phase__Result


class _Phase__CM:                                                                # context manager — internal, not exported
    def __init__(self, timer, name: str):
        self.timer   = timer
        self.name    = name
        self._t0     = None
        self._result = None

    def __enter__(self):
        self._t0 = time.monotonic()
        self._result = Schema__AWS__Phase__Result(
            name       = self.name,
            status     = Enum__AWS__Phase__Status.RUNNING,
            started_at = datetime.now(timezone.utc).isoformat(),
        )
        if self.timer.progress_cb:
            self.timer.progress_cb(self.name, Enum__AWS__Phase__Status.RUNNING)
        return self._result

    def __exit__(self, exc_type, exc, tb):
        duration_ms = int((time.monotonic() - self._t0) * 1000)
        if exc_type is None:
            if self._result.status == Enum__AWS__Phase__Status.RUNNING:          # phase didn't set a final status → default to OK
                self._result.status  = Enum__AWS__Phase__Status.OK
            self._result.duration_ms = duration_ms
        else:
            self._result.status      = Enum__AWS__Phase__Status.ERROR
            self._result.duration_ms = duration_ms
            self._result.error       = str(exc)
        if self.timer.results is None:
            self.timer.results = List__Schema__AWS__Phase__Result()
        self.timer.results.append(self._result)
        if self.timer.progress_cb:
            self.timer.progress_cb(self.name, self._result.status,
                                   self._result.detail)
        return False                                                              # never swallow exceptions


class Phase__Timer(Type_Safe):
    results     : List__Schema__AWS__Phase__Result = None
    progress_cb : object                           = None        # callable(name, status, detail='') or None

    def phase(self, name: str) -> _Phase__CM:                                   # context manager for one named phase
        return _Phase__CM(timer=self, name=name)

    def total_ms(self) -> int:                                                   # sum of all recorded phase durations
        return int(sum(r.duration_ms for r in (self.results or [])))

    def result_for(self, phase_name: str):                                       # Schema__AWS__Phase__Result for phase_name, or None
        for r in (self.results or []):
            if r.name == phase_name:
                return r
        return None
