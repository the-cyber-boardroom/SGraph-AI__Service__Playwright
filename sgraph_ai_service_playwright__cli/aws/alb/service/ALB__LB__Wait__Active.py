# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — ALB__LB__Wait__Active
# Polls describe_load_balancer every 5s until state == active or timeout.
# Returns (ok, attempts, last_state).
# ═══════════════════════════════════════════════════════════════════════════════

import time

from osbot_utils.type_safe.Type_Safe import Type_Safe


_POLL_INTERVAL_S = 5


class ALB__LB__Wait__Active(Type_Safe):
    alb_client : object = None                                                     # ALB__AWS__Client — injected
    sleep_fn   : object = None                                                     # callable(seconds) — for tests
    clock_fn   : object = None                                                     # callable() -> float — for tests

    def setup(self):
        if self.sleep_fn is None:
            self.sleep_fn = time.sleep
        if self.clock_fn is None:
            self.clock_fn = time.monotonic

    def wait(self, lb_arn_or_name: str, timeout_s: int) -> tuple:
        self.setup()
        deadline   = self.clock_fn() + max(int(timeout_s), 0)
        attempts   = 0
        last_state = ''
        while True:
            attempts += 1
            try:
                lb = self.alb_client.describe_load_balancer(lb_arn_or_name)
            except Exception as exc:                                                # noqa: BLE001
                last_state = f'error:{exc.__class__.__name__}'
                lb         = None
            if lb is not None:
                last_state = str(lb.state) if lb.state is not None else ''
                if last_state.lower() == 'active':
                    return (True, attempts, last_state)
            if self.clock_fn() >= deadline:
                return (False, attempts, last_state)
            self.sleep_fn(_POLL_INTERVAL_S)
