# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Ollama__Service
# Orchestrator for the ollama stack. Wires helpers, implements the five mandatory
# service methods: create_stack, list_stacks, get_stack_info, delete_stack, health.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.ollama.schemas.Schema__Ollama__Create__Request  import Schema__Ollama__Create__Request
from sg_compute_specs.ollama.schemas.Schema__Ollama__Create__Response import Schema__Ollama__Create__Response
from sg_compute_specs.ollama.schemas.Schema__Ollama__Delete__Response import Schema__Ollama__Delete__Response
from sg_compute_specs.ollama.schemas.Schema__Ollama__Info             import Schema__Ollama__Info
from sg_compute_specs.ollama.schemas.Schema__Ollama__List             import Schema__Ollama__List
from typing import Optional

from sg_compute_specs.ollama.service.Ollama__AWS__Client        import Ollama__AWS__Client
from sg_compute_specs.ollama.service.Ollama__User_Data__Builder import Ollama__User_Data__Builder
from sg_compute_specs.ollama.service.Ollama__Stack__Mapper      import Ollama__Stack__Mapper
from sg_compute_specs.ollama.service.Ollama__Stack__Mapper            import STACK_TYPE, TAG_MODEL
from sg_compute.platforms.ec2.networking.Caller__IP__Detector          import Caller__IP__Detector
from sg_compute.platforms.ec2.networking.Stack__Name__Generator        import Stack__Name__Generator

DEFAULT_REGION        = 'eu-west-2'
DEFAULT_INSTANCE_TYPE = 'g4dn.xlarge'
GPU_INSTANCE_PREFIXES = ('g4dn', 'g5', 'g6', 'p3', 'p4', 'p5')


def _is_gpu_instance(instance_type: str) -> bool:
    prefix = instance_type.split('.')[0] if '.' in instance_type else ''
    return any(prefix.startswith(p) for p in GPU_INSTANCE_PREFIXES)


class Ollama__Service(Type_Safe):
    aws_client        : Optional[Ollama__AWS__Client]        = None
    user_data_builder : Optional[Ollama__User_Data__Builder] = None
    mapper            : Optional[Ollama__Stack__Mapper]      = None
    ip_detector       : Optional[Caller__IP__Detector]       = None
    name_gen          : Optional[Stack__Name__Generator]     = None

    def setup(self) -> 'Ollama__Service':
        self.aws_client        = Ollama__AWS__Client       ().setup()
        self.user_data_builder = Ollama__User_Data__Builder()
        self.mapper            = Ollama__Stack__Mapper     ()
        self.ip_detector       = Caller__IP__Detector      ()
        self.name_gen          = Stack__Name__Generator    ()
        return self

    def create_stack(self, request : Schema__Ollama__Create__Request,
                           creator : str = '') -> Schema__Ollama__Create__Response:
        t0          = time.monotonic()
        stack_name  = request.stack_name    or self.name_gen.generate()
        region      = request.region        or DEFAULT_REGION
        caller_ip   = request.caller_ip     or self.ip_detector.detect()
        if not caller_ip:
            raise ValueError(
                'Could not detect your public IP automatically.\n'
                '  Pass it explicitly: sp ollama create --caller-ip <your-ip>\n'
                '  Find it with:       curl https://checkip.amazonaws.com')
        ami_id      = request.from_ami      or self.aws_client.ami.latest_al2023_ami(region)
        itype       = request.instance_type or DEFAULT_INSTANCE_TYPE
        allowed_cidr = request.allowed_cidr or f'{caller_ip}/32'
        gpu_required = request.gpu_required and _is_gpu_instance(itype)

        sg_id = self.aws_client.sg.ensure_security_group(
            region, stack_name, caller_ip,
            inbound_ports=[],
            extra_cidrs={11434: allowed_cidr})

        extra = {TAG_MODEL: request.model_name}
        tags  = self.aws_client.tags.build(stack_name, caller_ip, creator, extra_tags=extra)

        user_data = self.user_data_builder.render(
            stack_name   = stack_name        ,
            region       = region            ,
            model_name   = request.model_name,
            gpu_required = gpu_required      ,
            pull_on_boot = request.pull_on_boot,
            max_hours    = request.max_hours ,
        )
        iid = self.aws_client.launch.run_instance(
            region        = region           ,
            ami_id        = ami_id           ,
            sg_id         = sg_id            ,
            user_data     = user_data        ,
            tags          = tags             ,
            instance_type = itype            ,
            max_hours     = request.max_hours,
        )
        info = Schema__Ollama__Info(
            instance_id       = iid                    ,
            stack_name        = stack_name             ,
            region            = region                 ,
            ami_id            = ami_id                 ,
            instance_type     = itype                  ,
            security_group_id = sg_id                  ,
            model_name        = request.model_name     ,
            state             = 'pending'              ,
        )
        return Schema__Ollama__Create__Response(
            stack_info = info                                 ,
            message    = f'Instance {iid} launching'         ,
            elapsed_ms = int((time.monotonic() - t0) * 1000) ,
        )

    def list_stacks(self, region: str = '') -> Schema__Ollama__List:
        region = region or DEFAULT_REGION
        raw    = self.aws_client.instance.list_by_stack_type(region, STACK_TYPE)
        stacks = [self.mapper.to_info(d, region) for d in raw.values()]
        return Schema__Ollama__List(region=region, stacks=stacks, total=len(stacks))

    def get_stack_info(self, region: str, stack_name: str):
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        return self.mapper.to_info(details, region) if details else None

    def delete_stack(self, region: str, stack_name: str) -> Schema__Ollama__Delete__Response:
        t0      = time.monotonic()
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        if not details:
            return Schema__Ollama__Delete__Response(
                stack_name = stack_name       ,
                message    = 'stack not found',
                elapsed_ms = int((time.monotonic() - t0) * 1000))
        iid   = details.get('InstanceId', '')
        sg_id = (details.get('SecurityGroups') or [{}])[0].get('GroupId', '')
        ok    = self.aws_client.instance.terminate(region, iid)
        if ok and sg_id:
            self.aws_client.sg.delete_security_group(region, sg_id)
        return Schema__Ollama__Delete__Response(
            stack_name = stack_name                                         ,
            deleted    = ok                                                 ,
            message    = f'terminated {iid}' if ok else 'terminate failed' ,
            elapsed_ms = int((time.monotonic() - t0) * 1000)               ,
        )
