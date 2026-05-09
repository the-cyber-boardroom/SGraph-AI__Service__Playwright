# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Docker: Docker__Service
# Tier-1 pure-logic orchestrator for the docker compute spec.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from typing                                                                         import Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sg_compute.core.event_bus.Event__Bus                    import event_bus
from sg_compute.core.event_bus.schemas.Schema__Stack__Event  import Schema__Stack__Event
from sg_compute.primitives.Safe_Str__AWS__Region             import Safe_Str__AWS__Region
from sg_compute.primitives.Safe_Str__SSM__Path               import Safe_Str__SSM__Path
from sg_compute.primitives.Safe_Str__Stack__Name             import Safe_Str__Stack__Name

from sg_compute_specs.docker.collections.List__Schema__Docker__Info                 import List__Schema__Docker__Info
from sg_compute_specs.docker.enums.Enum__Docker__Stack__State                       import Enum__Docker__Stack__State
from sg_compute_specs.docker.schemas.Schema__Docker__Create__Request                import Schema__Docker__Create__Request
from sg_compute_specs.docker.schemas.Schema__Docker__Create__Response               import Schema__Docker__Create__Response
from sg_compute_specs.docker.schemas.Schema__Docker__Delete__Response               import Schema__Docker__Delete__Response
from sg_compute_specs.docker.schemas.Schema__Docker__Health__Response               import Schema__Docker__Health__Response
from sg_compute_specs.docker.schemas.Schema__Docker__Info                           import Schema__Docker__Info
from sg_compute_specs.docker.schemas.Schema__Docker__List                           import Schema__Docker__List
from typing import Optional

from sg_compute_specs.docker.service.Caller__IP__Detector       import Caller__IP__Detector
from sg_compute_specs.docker.service.Docker__AWS__Client        import Docker__AWS__Client
from sg_compute_specs.docker.service.Docker__Tags                            import DOCKER_NAMING
from sg_compute_specs.docker.service.Docker__Health__Checker    import Docker__Health__Checker
from sg_compute_specs.docker.service.Docker__Instance__Helper   import Docker__Instance__Helper
from sg_compute_specs.docker.service.Docker__Stack__Mapper      import Docker__Stack__Mapper
from sg_compute_specs.docker.service.Docker__User_Data__Builder import Docker__User_Data__Builder
from sg_compute_specs.docker.service.Random__Stack__Name__Generator import Random__Stack__Name__Generator


DEFAULT_REGION        = 'eu-west-2'
DEFAULT_INSTANCE_TYPE = 't3.medium'
PROFILE_NAME          = 'playwright-ec2'


class Docker__Service(Type_Safe):
    aws_client        : Optional[Docker__AWS__Client]            = None
    health_checker    : Optional[Docker__Health__Checker]        = None
    mapper            : Optional[Docker__Stack__Mapper]          = None
    ip_detector       : Optional[Caller__IP__Detector]           = None
    name_gen          : Optional[Random__Stack__Name__Generator] = None
    user_data_builder : Optional[Docker__User_Data__Builder]     = None

    def setup(self) -> 'Docker__Service':
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
        user_data = self.user_data_builder.render(stack_name                    ,
                                                          region                         ,
                                                          registry         = str(request.registry      or ''),
                                                          api_key_name     = str(request.api_key_name  or 'X-API-Key'),
                                                          api_key_ssm_path = str(request.api_key_ssm_path or ''),
                                                          max_hours        = request.max_hours         ,
                                                          enable_shell     = bool(request.enable_shell))
        iid       = self.aws_client.launch.run_instance(region, ami_id, sg_id, user_data, tags,
                                                        instance_type         = itype                  ,
                                                        instance_profile_name = PROFILE_NAME           ,
                                                        disk_size_gb          = int(request.disk_size_gb))
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

    def create_node(self, base_request, api_key_ssm_path: Safe_Str__SSM__Path = Safe_Str__SSM__Path()) -> 'Schema__Node__Info':
        from sg_compute.core.node.schemas.Schema__Node__Info import Schema__Node__Info
        from sg_compute.primitives.enums.Enum__Node__State   import Enum__Node__State
        docker_req = Schema__Docker__Create__Request(
            stack_name       = base_request.node_name     ,
            region           = base_request.region        ,
            instance_type    = base_request.instance_type ,
            from_ami         = base_request.ami_id        ,
            caller_ip        = base_request.caller_ip     ,
            max_hours        = base_request.max_hours     ,
            api_key_ssm_path = api_key_ssm_path           ,
        )
        resp = self.create_stack(docker_req)
        info = resp.stack_info
        return Schema__Node__Info(
            node_id              = str(info.stack_name)      ,
            spec_id              = 'docker'                  ,
            region               = base_request.region       ,
            state                = Enum__Node__State.BOOTING ,
            public_ip            = str(info.public_ip)       ,
            instance_id          = str(info.instance_id)     ,
            instance_type        = str(info.instance_type)   ,
            host_api_key_ssm_path= api_key_ssm_path          ,
        )

    def list_stacks(self, region: Safe_Str__AWS__Region) -> Schema__Docker__List:
        region = region or DEFAULT_REGION
        raw    = self.aws_client.instance.list_stacks(region)
        stacks = List__Schema__Docker__Info()
        for details in raw.values():
            stacks.append(self.mapper.to_info(details, region))
        return Schema__Docker__List(region=region, stacks=stacks, total=len(stacks))

    def get_stack_info(self, region: Safe_Str__AWS__Region, stack_name: Safe_Str__Stack__Name) -> Optional[Schema__Docker__Info]:
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        return self.mapper.to_info(details, region) if details else None

    def delete_stack(self, region: Safe_Str__AWS__Region, stack_name: Safe_Str__Stack__Name) -> Schema__Docker__Delete__Response:
        t0      = time.monotonic()
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        if not details:
            return Schema__Docker__Delete__Response(stack_name = stack_name                       ,
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
        return Schema__Docker__Delete__Response(stack_name = stack_name                                        ,
                                                deleted    = ok                                               ,
                                                message    = f'terminated {iid}' if ok else 'terminate failed',
                                                elapsed_ms = int((time.monotonic()-t0)*1000)                  )

    def health(self, region: Safe_Str__AWS__Region, stack_name: Safe_Str__Stack__Name,
               timeout_sec: int = 300, poll_sec: int = 10) -> Schema__Docker__Health__Response:
        return self.health_checker.check(region, stack_name, timeout_sec=timeout_sec, poll_sec=poll_sec)
