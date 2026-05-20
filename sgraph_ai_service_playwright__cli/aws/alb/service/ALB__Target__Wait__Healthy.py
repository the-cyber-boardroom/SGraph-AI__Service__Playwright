# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — ALB__Target__Wait__Healthy
# Polls describe_target_health every 5s until the matching target reports
# state == healthy or timeout. Returns (ok, attempts, last_state).
# ═══════════════════════════════════════════════════════════════════════════════

import time

from osbot_utils.type_safe.Type_Safe import Type_Safe


_POLL_INTERVAL_S = 5


class ALB__Target__Wait__Healthy(Type_Safe):
    alb_client : object = None                                                     # ALB__AWS__Client — injected
    sleep_fn   : object = None                                                     # callable(seconds) — for tests
    clock_fn   : object = None                                                     # callable() -> float — for tests

    def setup(self):
        if self.sleep_fn is None:
            self.sleep_fn = time.sleep
        if self.clock_fn is None:
            self.clock_fn = time.monotonic

    def wait(self, tg_arn: str, target_id: str, timeout_s: int) -> tuple:
        self.setup()
        deadline   = self.clock_fn() + max(int(timeout_s), 0)
        attempts   = 0
        last_state = ''
        while True:
            attempts += 1
            try:
                items = self.alb_client.describe_target_health(tg_arn)
            except Exception as exc:                                                # noqa: BLE001
                last_state = f'error:{exc.__class__.__name__}'
                items      = []
            for item in (items or []):
                tid = str(getattr(item, 'target_id', '') or '')
                if tid == target_id:
                    health = getattr(item, 'health_status', None)
                    last_state = str(health) if health is not None else ''
                    if last_state.lower() == 'healthy':
                        return (True, attempts, last_state)
                    break
            if self.clock_fn() >= deadline:
                return (False, attempts, last_state)
            self.sleep_fn(_POLL_INTERVAL_S)
