# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Docker__Health__Checker
# Polls until the EC2 instance reaches RUNNING + SSM reachable, then probes
# Docker by running `docker version`. Three-stage: EC2 state, Docker version,
# then sp-host-control container status.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.docker.enums.Enum__Docker__Stack__State      import Enum__Docker__Stack__State
from sgraph_ai_service_playwright__cli.docker.schemas.Schema__Docker__Health__Response import Schema__Docker__Health__Response


class Docker__Health__Checker(Type_Safe):
    instance  : object = None                                                       # Docker__Instance__Helper (injected by Docker__Service.setup())

    def check(self, region: str, stack_name: str,
              timeout_sec: int = 300, poll_sec: int = 10) -> Schema__Docker__Health__Response:
        deadline = time.monotonic() + timeout_sec
        t0       = time.monotonic()

        while True:
            details = self.instance.find_by_stack_name(region, stack_name)
            if details is None:
                return Schema__Docker__Health__Response(stack_name = stack_name          ,
                                                         message    = 'stack not found'  ,
                                                         elapsed_ms = int((time.monotonic()-t0)*1000))
            state_str = (details.get('State') or {}).get('Name', '')
            if state_str in ('shutting-down', 'terminated'):
                return Schema__Docker__Health__Response(
                    stack_name = stack_name                                               ,
                    state      = Enum__Docker__Stack__State.TERMINATED                   ,
                    message    = f'instance is {state_str}'                              ,
                    elapsed_ms = int((time.monotonic()-t0)*1000)                         )

            if state_str == 'running':
                iid       = details.get('InstanceId', '')
                public_ip = details.get('PublicIpAddress', '')
                if self.instance.is_ssm_reachable(region, iid):
                    docker_ver       = self.instance.get_docker_version(region, iid)
                    docker_ok        = bool(docker_ver)
                    hc_status        = self.instance.get_host_control_status(region, iid)
                    host_control_ok  = (hc_status == 'running')
                    healthy          = docker_ok and host_control_ok
                    if healthy:
                        message = 'ready'
                    elif docker_ok:
                        message = 'docker ready, host control starting'
                    else:
                        message = 'docker not ready yet'
                    if healthy or time.monotonic() >= deadline:                     # Return immediately when both ready or timed out
                        return Schema__Docker__Health__Response(
                            stack_name      = stack_name                                   ,
                            state           = Enum__Docker__Stack__State.RUNNING           ,
                            healthy         = healthy                                      ,
                            ssm_reachable   = True                                         ,
                            docker_ok       = docker_ok                                    ,
                            host_control_ok = host_control_ok                              ,
                            docker_version  = docker_ver                                   ,
                            public_ip       = public_ip                                    ,
                            message         = message                                      ,
                            elapsed_ms      = int((time.monotonic()-t0)*1000)              )

            if time.monotonic() >= deadline:
                break
            time.sleep(poll_sec)

        return Schema__Docker__Health__Response(
            stack_name = stack_name                                                       ,
            state      = Enum__Docker__Stack__State.UNKNOWN                              ,
            message    = f'timed out after {timeout_sec}s'                               ,
            elapsed_ms = int((time.monotonic()-t0)*1000)                                 )
