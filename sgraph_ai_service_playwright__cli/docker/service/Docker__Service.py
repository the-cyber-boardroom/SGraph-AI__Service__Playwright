# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Docker__Service
# Tier-1 pure-logic orchestrator for sp docker. Mirrors Linux__Service with
# Docker-specific user-data and health checks.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from typing                                                                         import Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.core.event_bus.Event__Bus                    import event_bus
from sgraph_ai_service_playwright__cli.core.event_bus.schemas.Schema__Stack__Event  import Schema__Stack__Event
from sgraph_ai_service_playwright__cli.docker.collections.List__Schema__Docker__Info import List__Schema__Docker__Info
from sgraph_ai_service_playwright__cli.docker.enums.Enum__Docker__Stack__State      import Enum__Docker__Stack__State
from sgraph_ai_service_playwright__cli.docker.schemas.Schema__Docker__Create__Request import Schema__Docker__Create__Request
from sgraph_ai_service_playwright__cli.docker.schemas.Schema__Docker__Create__Response import Schema__Docker__Create__Response
from sgraph_ai_service_playwright__cli.docker.schemas.Schema__Docker__Delete__Response import Schema__Docker__Delete__Response
from sgraph_ai_service_playwright__cli.docker.schemas.Schema__Docker__Health__Response import Schema__Docker__Health__Response
from sgraph_ai_service_playwright__cli.docker.schemas.Schema__Docker__Info          import Schema__Docker__Info
from sgraph_ai_service_playwright__cli.docker.schemas.Schema__Docker__List          import Schema__Docker__List
from sgraph_ai_service_playwright__cli.docker.service.Docker__AWS__Client           import DOCKER_NAMING


DEFAULT_REGION        = 'eu-west-2'
DEFAULT_INSTANCE_TYPE = 't3.medium'
PROFILE_NAME          = 'playwright-ec2'                                            # IAM instance profile: AmazonSSMManagedInstanceCore + ECR read


class Docker__Service(Type_Safe):
    aws_client        : object = None                                               # Docker__AWS__Client           (lazy via setup())
    health_checker    : object = None                                               # Docker__Health__Checker       (lazy via setup())
    mapper            : object = None                                               # Docker__Stack__Mapper         (lazy via setup())
    ip_detector       : object = None                                               # Caller__IP__Detector         (lazy via setup())
    name_gen          : object = None                                               # Random__Stack__Name__Generator (lazy via setup())
    user_data_builder : object = None                                               # Docker__User_Data__Builder    (lazy via setup())

    def setup(self) -> 'Docker__Service':
        from sgraph_ai_service_playwright__cli.docker.service.Caller__IP__Detector       import Caller__IP__Detector
        from sgraph_ai_service_playwright__cli.docker.service.Docker__AWS__Client        import Docker__AWS__Client
        from sgraph_ai_service_playwright__cli.docker.service.Docker__Health__Checker    import Docker__Health__Checker
        from sgraph_ai_service_playwright__cli.docker.service.Docker__Instance__Helper   import Docker__Instance__Helper
        from sgraph_ai_service_playwright__cli.docker.service.Docker__Stack__Mapper      import Docker__Stack__Mapper
        from sgraph_ai_service_playwright__cli.docker.service.Docker__User_Data__Builder import Docker__User_Data__Builder
        from sgraph_ai_service_playwright__cli.docker.service.Random__Stack__Name__Generator import Random__Stack__Name__Generator
        self.aws_client        = Docker__AWS__Client()     .setup()
        self.mapper            = Docker__Stack__Mapper()
        self.ip_detector       = Caller__IP__Detector()
        self.name_gen          = Random__Stack__Name__Generator()
        self.user_data_builder = Docker__User_Data__Builder()
        checker                = Docker__Health__Checker()
        checker.instance       = Docker__Instance__Helper()
        self.health_checker    = checker
        return self

    def create_stack(self, request: Schema__Docker__Create__Request, creator: str = '') -> Schema__Docker__Create__Response:
        t0         = time.monotonic()
        stack_name = str(request.stack_name)    or self.name_gen.generate()
        region     = str(request.region    )    or DEFAULT_REGION
        caller_ip  = str(request.caller_ip )    or str(self.ip_detector.detect())
        ami_id     = str(request.from_ami  )    or self.aws_client.ami.latest_al2023_ami_id(region)
        itype      = str(request.instance_type) or DEFAULT_INSTANCE_TYPE

        sg_id     = self.aws_client.sg.ensure_security_group(region, stack_name, caller_ip,
                                                              extra_ports=request.extra_ports)
        tags      = self.aws_client.tags.build(stack_name, caller_ip, creator)
        user_data = self.user_data_builder.render(stack_name, region, max_hours=request.max_hours)
        iid       = self.aws_client.launch.run_instance(region, ami_id, sg_id, user_data, tags,
                                                        instance_type         = itype        ,
                                                        instance_profile_name = PROFILE_NAME )
        info      = Schema__Docker__Info(
            stack_name        = stack_name                                  ,
            aws_name_tag      = DOCKER_NAMING.aws_name_for_stack(stack_name),
            instance_id       = iid                                         ,
            region            = region                                      ,
            ami_id            = ami_id                                      ,
            instance_type     = itype                                       ,
            security_group_id = sg_id                                       ,
            allowed_ip        = caller_ip                                   ,
            state             = Enum__Docker__Stack__State.PENDING          )
        event_bus.emit('docker:stack.created', Schema__Stack__Event(
            type_id     = Enum__Stack__Type.DOCKER,
            stack_name  = stack_name              ,
            region      = region                  ,
            instance_id = str(iid)                ))
        return Schema__Docker__Create__Response(stack_info = info                                             ,
                                                 message    = f'Instance {iid} launching'                     ,
                                                 elapsed_ms = int((time.monotonic()-t0)*1000)                 )

    def list_stacks(self, region: str) -> Schema__Docker__List:
        region = region or DEFAULT_REGION
        raw    = self.aws_client.instance.list_stacks(region)
        stacks = List__Schema__Docker__Info()
        for details in raw.values():
            stacks.append(self.mapper.to_info(details, region))
        return Schema__Docker__List(region=region, stacks=stacks, total=len(stacks))

    def get_stack_info(self, region: str, stack_name: str) -> Optional[Schema__Docker__Info]:
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        return self.mapper.to_info(details, region) if details else None

    def delete_stack(self, region: str, stack_name: str) -> Schema__Docker__Delete__Response:
        t0      = time.monotonic()
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        if not details:
            return Schema__Docker__Delete__Response(stack_name = stack_name                        ,
                                                     message    = 'stack not found'                ,
                                                     elapsed_ms = int((time.monotonic()-t0)*1000)  )
        iid = details.get('InstanceId', '')
        ok  = self.aws_client.instance.terminate_instance(region, iid)
        if ok:
            event_bus.emit('docker:stack.deleted', Schema__Stack__Event(
                type_id     = Enum__Stack__Type.DOCKER,
                stack_name  = stack_name              ,
                region      = region                  ,
                instance_id = iid                     ))
        return Schema__Docker__Delete__Response(stack_name = stack_name                                       ,
                                                 deleted    = ok                                              ,
                                                 message    = f'terminated {iid}' if ok else 'terminate failed',
                                                 elapsed_ms = int((time.monotonic()-t0)*1000)                 )

    def health(self, region: str, stack_name: str,
               timeout_sec: int = 300, poll_sec: int = 10) -> Schema__Docker__Health__Response:
        return self.health_checker.check(region, stack_name, timeout_sec=timeout_sec, poll_sec=poll_sec)
