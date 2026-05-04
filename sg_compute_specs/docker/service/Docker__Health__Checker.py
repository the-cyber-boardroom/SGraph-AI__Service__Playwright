# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Docker: Docker__Health__Checker
# Polls until EC2 reaches RUNNING + SSM reachable, then probes Docker version.
# Two-stage: EC2 state first, Docker version probe second.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.docker.enums.Enum__Docker__Stack__State                       import Enum__Docker__Stack__State
from sg_compute_specs.docker.schemas.Schema__Docker__Health__Response               import Schema__Docker__Health__Response


class Docker__Health__Checker(Type_Safe):
    instance  : object = None                                                       # Docker__Instance__Helper (injected by Docker__Service.setup())

    def check(self, region: str, stack_name: str,
              timeout_sec: int = 300, poll_sec: int = 10) -> Schema__Docker__Health__Response:
        deadline = time.monotonic() + timeout_sec
        t0       = time.monotonic()

        while time.monotonic() < deadline:
            details = self.instance.find_by_stack_name(region, stack_name)
            if details is None:
                return Schema__Docker__Health__Response(stack_name = stack_name         ,
                                                        message    = 'stack not found'  ,
                                                        elapsed_ms = int((time.monotonic()-t0)*1000))
            state_str = (details.get('State') or {}).get('Name', '')
            if state_str in ('shutting-down', 'terminated'):
                return Schema__Docker__Health__Response(
                    stack_name = stack_name                                              ,
                    state      = Enum__Docker__Stack__State.TERMINATED                  ,
                    message    = f'instance is {state_str}'                             ,
                    elapsed_ms = int((time.monotonic()-t0)*1000)                        )

            if state_str == 'running':
                iid = details.get('InstanceId', '')
                if self.instance.is_ssm_reachable(region, iid):
                    docker_ver = self.instance.get_docker_version(region, iid)
                    docker_ok  = bool(docker_ver)
                    return Schema__Docker__Health__Response(
                        stack_name     = stack_name                                       ,
                        state          = Enum__Docker__Stack__State.RUNNING               ,
                        healthy        = docker_ok                                        ,
                        ssm_reachable  = True                                             ,
                        docker_ok      = docker_ok                                        ,
                        docker_version = docker_ver                                       ,
                        message        = 'docker ready' if docker_ok else 'docker not ready yet',
                        elapsed_ms     = int((time.monotonic()-t0)*1000)                  )

            time.sleep(poll_sec)

        return Schema__Docker__Health__Response(
            stack_name = stack_name                                                      ,
            state      = Enum__Docker__Stack__State.UNKNOWN                             ,
            message    = f'timed out after {timeout_sec}s'                              ,
            elapsed_ms = int((time.monotonic()-t0)*1000)                                )
