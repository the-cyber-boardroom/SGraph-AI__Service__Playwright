# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — EC2__Instance__Wait
# Polls until an EC2 instance reaches a target state (or times out).
#
# Backoff schedule: 2s → 5s → 10s → 15s → capped at 15s.
# Default timeout: 300s (5 min).
# ═══════════════════════════════════════════════════════════════════════════════

import time

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.ec2.enums.Enum__EC2__Instance__State import Enum__EC2__Instance__State
from sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client         import EC2__AWS__Client


_BACKOFF = [2, 5, 10, 15]                                                     # seconds between polls; last value is capped


class EC2__Instance__Wait(Type_Safe):

    ec2_client : EC2__AWS__Client

    def setup(self):
        if self.ec2_client is None:
            self.ec2_client = EC2__AWS__Client()
        return self

    def wait(self, instance_id: str, target_state: Enum__EC2__Instance__State,
             timeout: int = 300) -> bool:                                      # Returns True if state reached before timeout
        deadline  = time.time() + timeout
        backoff   = iter(_BACKOFF)
        delay     = next(backoff)
        while time.time() < deadline:
            detail = self.ec2_client.describe_instance(instance_id)
            if detail and detail.state == target_state:
                return True
            time.sleep(delay)
            try:
                delay = next(backoff)
            except StopIteration:
                delay = _BACKOFF[-1]                                            # cap at last value
        return False
