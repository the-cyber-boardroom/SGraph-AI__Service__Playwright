# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Podman: Podman__Health__Checker
# Polls until EC2 reaches RUNNING + SSM reachable, then probes Podman version.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.podman.enums.Enum__Podman__Stack__State                       import Enum__Podman__Stack__State
from sg_compute_specs.podman.schemas.Schema__Podman__Health__Response               import Schema__Podman__Health__Response


class Podman__Health__Checker(Type_Safe):
    instance  : object = None                                                       # Podman__Instance__Helper (injected by Podman__Service.setup())

    def check(self, region: str, stack_name: str,
              timeout_sec: int = 300, poll_sec: int = 10) -> Schema__Podman__Health__Response:
        deadline = time.monotonic() + timeout_sec
        t0       = time.monotonic()

        while time.monotonic() < deadline:
            details = self.instance.find_by_stack_name(region, stack_name)
            if details is None:
                return Schema__Podman__Health__Response(stack_name = stack_name         ,
                                                        message    = 'stack not found'  ,
                                                        elapsed_ms = int((time.monotonic()-t0)*1000))
            state_str = (details.get('State') or {}).get('Name', '')
            if state_str in ('shutting-down', 'terminated'):
                return Schema__Podman__Health__Response(
                    stack_name = stack_name                                              ,
                    state      = Enum__Podman__Stack__State.TERMINATED                  ,
                    message    = f'instance is {state_str}'                             ,
                    elapsed_ms = int((time.monotonic()-t0)*1000)                        )

            if state_str == 'running':
                iid = details.get('InstanceId', '')
                if self.instance.is_ssm_reachable(region, iid):
                    podman_ver = self.instance.get_podman_version(region, iid)
                    podman_ok  = bool(podman_ver)
                    return Schema__Podman__Health__Response(
                        stack_name     = stack_name                                       ,
                        state          = Enum__Podman__Stack__State.RUNNING               ,
                        healthy        = podman_ok                                        ,
                        ssm_reachable  = True                                             ,
                        podman_ok      = podman_ok                                        ,
                        podman_version = podman_ver                                       ,
                        message        = 'podman ready' if podman_ok else 'podman not ready yet',
                        elapsed_ms     = int((time.monotonic()-t0)*1000)                  )

            time.sleep(poll_sec)

        return Schema__Podman__Health__Response(
            stack_name = stack_name                                                      ,
            state      = Enum__Podman__Stack__State.UNKNOWN                             ,
            message    = f'timed out after {timeout_sec}s'                              ,
            elapsed_ms = int((time.monotonic()-t0)*1000)                                )
