# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Linux__Service
# Tier-1 pure-logic orchestrator for sp linux. Composes the per-concern helpers
# and exposes operations consumed by both the typer CLI (Tier 2A) and FastAPI
# routes (Tier 2B). No print(), no Console — ergonomics live in wrappers.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from typing                                                                         import Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.linux.collections.List__Schema__Linux__Info  import List__Schema__Linux__Info
from sgraph_ai_service_playwright__cli.linux.enums.Enum__Linux__Stack__State        import Enum__Linux__Stack__State
from sgraph_ai_service_playwright__cli.linux.schemas.Schema__Linux__Create__Request import Schema__Linux__Create__Request
from sgraph_ai_service_playwright__cli.linux.schemas.Schema__Linux__Create__Response import Schema__Linux__Create__Response
from sgraph_ai_service_playwright__cli.linux.schemas.Schema__Linux__Delete__Response import Schema__Linux__Delete__Response
from sgraph_ai_service_playwright__cli.linux.schemas.Schema__Linux__Health__Check   import Schema__Linux__Health__Check
from sgraph_ai_service_playwright__cli.linux.schemas.Schema__Linux__Health__Response import Schema__Linux__Health__Response
from sgraph_ai_service_playwright__cli.linux.schemas.Schema__Linux__Info            import Schema__Linux__Info
from sgraph_ai_service_playwright__cli.linux.schemas.Schema__Linux__List            import Schema__Linux__List
from sgraph_ai_service_playwright__cli.linux.service.Linux__AWS__Client             import LINUX_NAMING


DEFAULT_REGION        = 'eu-west-2'
DEFAULT_INSTANCE_TYPE = 't3.medium'
PROFILE_NAME          = 'playwright-ec2'                                            # Reuses the existing IAM instance profile (has AmazonSSMManagedInstanceCore)


class Linux__Service(Type_Safe):
    aws_client        : object = None                                               # Linux__AWS__Client           (lazy via setup())
    health_checker    : object = None                                               # Linux__Health__Checker       (lazy via setup())
    mapper            : object = None                                               # Linux__Stack__Mapper         (lazy via setup())
    ip_detector       : object = None                                               # Caller__IP__Detector         (lazy via setup())
    name_gen          : object = None                                               # Random__Stack__Name__Generator (lazy via setup())
    user_data_builder : object = None                                               # Linux__User_Data__Builder    (lazy via setup())

    def setup(self) -> 'Linux__Service':
        from sgraph_ai_service_playwright__cli.linux.service.Caller__IP__Detector       import Caller__IP__Detector
        from sgraph_ai_service_playwright__cli.linux.service.Linux__AWS__Client         import Linux__AWS__Client
        from sgraph_ai_service_playwright__cli.linux.service.Linux__Health__Checker     import Linux__Health__Checker
        from sgraph_ai_service_playwright__cli.linux.service.Linux__Instance__Helper    import Linux__Instance__Helper
        from sgraph_ai_service_playwright__cli.linux.service.Linux__Stack__Mapper       import Linux__Stack__Mapper
        from sgraph_ai_service_playwright__cli.linux.service.Linux__User_Data__Builder  import Linux__User_Data__Builder
        from sgraph_ai_service_playwright__cli.linux.service.Random__Stack__Name__Generator import Random__Stack__Name__Generator
        self.aws_client        = Linux__AWS__Client()     .setup()
        self.mapper            = Linux__Stack__Mapper()
        self.ip_detector       = Caller__IP__Detector()
        self.name_gen          = Random__Stack__Name__Generator()
        self.user_data_builder = Linux__User_Data__Builder()
        checker                = Linux__Health__Checker()
        checker.instance       = Linux__Instance__Helper()
        self.health_checker    = checker
        return self

    def create_stack(self, request: Schema__Linux__Create__Request, creator: str = '') -> Schema__Linux__Create__Response:
        t0         = time.monotonic()
        stack_name = str(request.stack_name)   or self.name_gen.generate()
        region     = str(request.region    )   or DEFAULT_REGION
        caller_ip  = str(request.caller_ip )   or str(self.ip_detector.detect())
        ami_id     = str(request.from_ami  )   or self.aws_client.ami.latest_al2023_ami_id(region)
        itype      = str(request.instance_type) or DEFAULT_INSTANCE_TYPE

        sg_id      = self.aws_client.sg.ensure_security_group(region, stack_name, caller_ip,
                                                               extra_ports=request.extra_ports)
        tags       = self.aws_client.tags.build(stack_name, caller_ip, creator)
        user_data  = self.user_data_builder.render(stack_name, region)
        iid        = self.aws_client.launch.run_instance(region, ami_id, sg_id, user_data, tags,
                                                         instance_type         = itype        ,
                                                         instance_profile_name = PROFILE_NAME )
        info       = Schema__Linux__Info(
            stack_name        = stack_name                               ,
            aws_name_tag      = LINUX_NAMING.aws_name_for_stack(stack_name),
            instance_id       = iid                                      ,
            region            = region                                   ,
            ami_id            = ami_id                                   ,
            instance_type     = itype                                    ,
            security_group_id = sg_id                                    ,
            allowed_ip        = caller_ip                                ,
            state             = Enum__Linux__Stack__State.PENDING        )
        return Schema__Linux__Create__Response(stack_info  = info                                             ,
                                                message     = f'Instance {iid} launching'                     ,
                                                elapsed_ms  = int((time.monotonic()-t0)*1000)                 )

    def list_stacks(self, region: str) -> Schema__Linux__List:
        raw    = self.aws_client.instance.list_stacks(region)
        stacks = List__Schema__Linux__Info()
        for details in raw.values():
            stacks.append(self.mapper.to_info(details, region))
        return Schema__Linux__List(region=region, stacks=stacks, total=len(stacks))

    def get_stack_info(self, region: str, stack_name: str) -> Optional[Schema__Linux__Info]:
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        return self.mapper.to_info(details, region) if details else None

    def delete_stack(self, region: str, stack_name: str) -> Schema__Linux__Delete__Response:
        t0      = time.monotonic()
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        if not details:
            return Schema__Linux__Delete__Response(stack_name = stack_name                         ,
                                                    message    = 'stack not found'                  ,
                                                    elapsed_ms = int((time.monotonic()-t0)*1000)    )
        iid = details.get('InstanceId', '')
        ok  = self.aws_client.instance.terminate_instance(region, iid)
        return Schema__Linux__Delete__Response(stack_name = stack_name                                        ,
                                                deleted    = ok                                               ,
                                                message    = f'terminated {iid}' if ok else 'terminate failed',
                                                elapsed_ms = int((time.monotonic()-t0)*1000)                  )

    def health(self, region: str, stack_name: str,
               timeout_sec: int = 300, poll_sec: int = 10) -> Schema__Linux__Health__Response:
        req = Schema__Linux__Health__Check(stack_name  = stack_name ,
                                            region      = region     ,
                                            timeout_sec = timeout_sec,
                                            poll_sec    = poll_sec   )
        return self.health_checker.check(req)
