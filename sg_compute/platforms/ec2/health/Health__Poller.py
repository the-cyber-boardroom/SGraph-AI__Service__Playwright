# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Health__Poller
# Two-phase poll: (1) wait for EC2 state=running, (2) HTTP probe the app.
# Injected with EC2__Instance__Helper and Health__HTTP__Probe for testability.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from typing import Optional

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.platforms.ec2.helpers.EC2__Instance__Helper import EC2__Instance__Helper
from sg_compute.platforms.ec2.health.Health__HTTP__Probe    import Health__HTTP__Probe


class Health__Poller(Type_Safe):
    instance : Optional[EC2__Instance__Helper] = None
    probe    : Optional[Health__HTTP__Probe]   = None

    def wait_healthy(self, region       : str ,
                           instance_id  : str ,
                           public_ip    : str ,
                           health_path  : str = '/api/agents',
                           port         : int = 443          ,
                           timeout_sec  : int = 600          ,
                           poll_sec     : int = 15           ) -> bool:
        deadline = time.monotonic() + timeout_sec

        # Phase 1 — wait for EC2 running state
        while time.monotonic() < deadline:
            if self.instance.wait_for_running(region, instance_id,
                                              timeout_sec = min(30, deadline - time.monotonic()),
                                              poll_sec    = poll_sec):
                break
            if time.monotonic() >= deadline:
                return False

        # Phase 2 — HTTP probe until app responds
        url = f'https://{public_ip}:{port}{health_path}' if port != 443 else \
              f'https://{public_ip}{health_path}'
        while time.monotonic() < deadline:
            if self.probe.check(url, timeout_sec=10):
                return True
            time.sleep(poll_sec)

        return False
