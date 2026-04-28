# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Linux__Health__Checker
# Polls until the EC2 instance reaches RUNNING state and the SSM agent is
# reachable. Health for a Linux stack is entirely SSM-based (no HTTP probe).
# Single responsibility: wait + reachability check.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.linux.enums.Enum__Linux__Stack__State        import Enum__Linux__Stack__State
from sgraph_ai_service_playwright__cli.linux.schemas.Schema__Linux__Health__Check   import Schema__Linux__Health__Check
from sgraph_ai_service_playwright__cli.linux.schemas.Schema__Linux__Health__Response import Schema__Linux__Health__Response


class Linux__Health__Checker(Type_Safe):
    instance  : object = None                                                       # Linux__Instance__Helper (injected by Linux__Service.setup())

    def check(self, request: Schema__Linux__Health__Check) -> Schema__Linux__Health__Response:
        region     = str(request.region    )
        stack_name = str(request.stack_name)
        deadline   = time.monotonic() + request.timeout_sec
        t0         = time.monotonic()

        while time.monotonic() < deadline:
            details = self.instance.find_by_stack_name(region, stack_name)
            if details is None:
                return Schema__Linux__Health__Response(stack_name  = stack_name               ,
                                                        message     = 'stack not found'        ,
                                                        elapsed_ms  = int((time.monotonic()-t0)*1000))
            state_str = (details.get('State') or {}).get('Name', '')
            if state_str in ('shutting-down', 'terminated'):
                return Schema__Linux__Health__Response(stack_name  = stack_name                   ,
                                                        state       = Enum__Linux__Stack__State.TERMINATED,
                                                        message     = f'instance is {state_str}'   ,
                                                        elapsed_ms  = int((time.monotonic()-t0)*1000))

            if state_str == 'running':
                iid    = details.get('InstanceId', '')
                ok     = self.instance.is_ssm_reachable(region, iid)
                if ok:
                    return Schema__Linux__Health__Response(
                        stack_name    = stack_name                            ,
                        state         = Enum__Linux__Stack__State.RUNNING     ,
                        healthy       = True                                  ,
                        ssm_reachable = True                                  ,
                        message       = 'instance running and SSM reachable'  ,
                        elapsed_ms    = int((time.monotonic()-t0)*1000)       )

            time.sleep(request.poll_sec)

        return Schema__Linux__Health__Response(stack_name = stack_name                                          ,
                                                state      = Enum__Linux__Stack__State.UNKNOWN                  ,
                                                message    = f'timed out after {request.timeout_sec}s'          ,
                                                elapsed_ms = int((time.monotonic()-t0)*1000)                    )
