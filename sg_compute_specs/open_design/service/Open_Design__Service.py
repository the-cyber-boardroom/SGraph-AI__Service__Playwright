# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Open_Design__Service
# Orchestrator for the open-design stack. Wires helpers, implements the five
# mandatory service methods: create_stack, list_stacks, get_stack_info,
# delete_stack, health.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.open_design.schemas.Schema__Open_Design__Create__Request  import Schema__Open_Design__Create__Request
from sg_compute_specs.open_design.schemas.Schema__Open_Design__Create__Response import Schema__Open_Design__Create__Response
from sg_compute_specs.open_design.schemas.Schema__Open_Design__Delete__Response import Schema__Open_Design__Delete__Response
from sg_compute_specs.open_design.schemas.Schema__Open_Design__Info             import Schema__Open_Design__Info
from sg_compute_specs.open_design.schemas.Schema__Open_Design__List             import Schema__Open_Design__List
from sg_compute_specs.open_design.service.Open_Design__Stack__Mapper            import STACK_TYPE, TAG_OLLAMA

DEFAULT_REGION        = 'eu-west-2'
DEFAULT_INSTANCE_TYPE = 't3.large'
PROFILE_NAME          = 'playwright-ec2'                                            # IAM: AmazonSSMManagedInstanceCore + ECR read


class Open_Design__Service(Type_Safe):
    aws_client        : object = None   # Open_Design__AWS__Client
    user_data_builder : object = None   # Open_Design__User_Data__Builder
    mapper            : object = None   # Open_Design__Stack__Mapper
    ip_detector       : object = None   # Caller__IP__Detector
    name_gen          : object = None   # Stack__Name__Generator

    def setup(self) -> 'Open_Design__Service':
        from sg_compute_specs.open_design.service.Open_Design__AWS__Client       import Open_Design__AWS__Client
        from sg_compute_specs.open_design.service.Open_Design__User_Data__Builder import Open_Design__User_Data__Builder
        from sg_compute_specs.open_design.service.Open_Design__Stack__Mapper     import Open_Design__Stack__Mapper
        from sg_compute.helpers.networking.Caller__IP__Detector                   import Caller__IP__Detector
        from sg_compute.helpers.networking.Stack__Name__Generator                 import Stack__Name__Generator
        self.aws_client        = Open_Design__AWS__Client       ().setup()
        self.user_data_builder = Open_Design__User_Data__Builder()
        self.mapper            = Open_Design__Stack__Mapper     ()
        self.ip_detector       = Caller__IP__Detector           ()
        self.name_gen          = Stack__Name__Generator         ()
        return self

    def create_stack(self, request : Schema__Open_Design__Create__Request,
                           creator : str = '') -> Schema__Open_Design__Create__Response:
        t0         = time.monotonic()
        stack_name = request.stack_name     or self.name_gen.generate()
        region     = request.region         or DEFAULT_REGION
        caller_ip  = request.caller_ip      or self.ip_detector.detect()
        if not caller_ip:
            raise ValueError(
                'Could not detect your public IP automatically.\n'
                '  Pass it explicitly: sp od create --caller-ip <your-ip>\n'
                '  Find it with:       curl https://checkip.amazonaws.com')
        ami_id     = request.from_ami       or self.aws_client.ami.latest_al2023_ami(region)
        itype      = request.instance_type  or DEFAULT_INSTANCE_TYPE

        sg_id = self.aws_client.sg.ensure_security_group(
            region, stack_name, caller_ip, inbound_ports=[443])

        extra = {TAG_OLLAMA: request.ollama_base_url} if request.ollama_base_url else {}
        tags  = self.aws_client.tags.build(stack_name, caller_ip, creator, extra_tags=extra)

        user_data = self.user_data_builder.render(
            stack_name      = stack_name            ,
            region          = region                ,
            api_key         = request.api_key       ,
            ollama_base_url = request.ollama_base_url,
            open_design_ref = request.open_design_ref,
            fast_boot       = request.fast_boot     ,
            max_hours       = request.max_hours     ,
        )
        iid = self.aws_client.launch.run_instance(
            region           = region           ,
            ami_id           = ami_id           ,
            sg_id            = sg_id            ,
            user_data        = user_data        ,
            tags             = tags             ,
            instance_type    = itype            ,
            instance_profile = PROFILE_NAME     ,
            max_hours        = request.max_hours,
        )
        info = Schema__Open_Design__Info(
            instance_id       = iid        ,
            stack_name        = stack_name ,
            region            = region     ,
            ami_id            = ami_id     ,
            instance_type     = itype      ,
            security_group_id = sg_id      ,
            caller_ip         = caller_ip  ,
            state             = 'pending'  ,
            viewer_url        = ''         ,
            has_ollama        = bool(request.ollama_base_url),
        )
        return Schema__Open_Design__Create__Response(
            stack_info = info                                         ,
            message    = f'Instance {iid} launching'                 ,
            elapsed_ms = int((time.monotonic() - t0) * 1000)         ,
        )

    def list_stacks(self, region: str = '') -> Schema__Open_Design__List:
        region = region or DEFAULT_REGION
        raw    = self.aws_client.instance.list_by_stack_type(region, STACK_TYPE)
        stacks = [self.mapper.to_info(d, region) for d in raw.values()]
        return Schema__Open_Design__List(region=region, stacks=stacks, total=len(stacks))

    def get_stack_info(self, region: str, stack_name: str):
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        return self.mapper.to_info(details, region) if details else None

    def delete_stack(self, region: str, stack_name: str) -> Schema__Open_Design__Delete__Response:
        t0      = time.monotonic()
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        if not details:
            return Schema__Open_Design__Delete__Response(
                stack_name = stack_name     ,
                message    = 'stack not found',
                elapsed_ms = int((time.monotonic() - t0) * 1000))
        iid   = details.get('InstanceId', '')
        sg_id = (details.get('SecurityGroups') or [{}])[0].get('GroupId', '')
        ok    = self.aws_client.instance.terminate(region, iid)
        if ok and sg_id:
            self.aws_client.sg.delete_security_group(region, sg_id)
        return Schema__Open_Design__Delete__Response(
            stack_name = stack_name                                          ,
            deleted    = ok                                                  ,
            message    = f'terminated {iid}' if ok else 'terminate failed'  ,
            elapsed_ms = int((time.monotonic() - t0) * 1000)                ,
        )
