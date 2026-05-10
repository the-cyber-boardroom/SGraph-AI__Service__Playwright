# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Ollama__Service
# Orchestrator for the ollama stack. Extends Spec__Service__Base — health/exec/
# connect_target inherited; spec-specific bits below.
# ═══════════════════════════════════════════════════════════════════════════════

import time

from typing import Optional

from sg_compute.core.spec.Spec__Service__Base                                 import Spec__Service__Base
from sg_compute.platforms.ec2.networking.Caller__IP__Detector                 import Caller__IP__Detector
from sg_compute.platforms.ec2.networking.Stack__Name__Generator               import Stack__Name__Generator

from sg_compute_specs.ollama.enums.Enum__Ollama__AMI__Base                    import Enum__Ollama__AMI__Base
from sg_compute_specs.ollama.schemas.Schema__Ollama__Create__Request          import Schema__Ollama__Create__Request
from sg_compute_specs.ollama.schemas.Schema__Ollama__Create__Response         import Schema__Ollama__Create__Response
from sg_compute_specs.ollama.schemas.Schema__Ollama__Delete__Response         import Schema__Ollama__Delete__Response
from sg_compute_specs.ollama.schemas.Schema__Ollama__Info                     import Schema__Ollama__Info
from sg_compute_specs.ollama.schemas.Schema__Ollama__List                     import Schema__Ollama__List
from sg_compute_specs.ollama.service.Ollama__AMI__Helper                      import Ollama__AMI__Helper
from sg_compute_specs.ollama.service.Ollama__AWS__Client                      import Ollama__AWS__Client
from sg_compute_specs.ollama.service.Ollama__Stack__Mapper                    import (Ollama__Stack__Mapper ,
                                                                                       STACK_TYPE            ,
                                                                                       TAG_MODEL             )
from sg_compute_specs.ollama.service.Ollama__User_Data__Builder               import Ollama__User_Data__Builder

DEFAULT_REGION         = 'eu-west-2'
DEFAULT_INSTANCE_TYPE  = 'g5.xlarge'                              # R4 — gpt-oss:20b needs ≥24 GiB VRAM
GPU_INSTANCE_PREFIXES  = ('g4dn', 'g5', 'g6', 'p3', 'p4', 'p5')
PULL_TIMEOUT_SEC       = 900                                      # ollama pull is slow for 20B-class models


def _is_gpu_instance(instance_type: str) -> bool:
    prefix = instance_type.split('.')[0] if '.' in instance_type else ''
    return any(prefix.startswith(p) for p in GPU_INSTANCE_PREFIXES)


class Ollama__Service(Spec__Service__Base):
    aws_client        : Optional[Ollama__AWS__Client]        = None
    user_data_builder : Optional[Ollama__User_Data__Builder] = None
    mapper            : Optional[Ollama__Stack__Mapper]      = None
    ip_detector       : Optional[Caller__IP__Detector]       = None
    name_gen          : Optional[Stack__Name__Generator]     = None
    ami_helper        : Optional[Ollama__AMI__Helper]        = None

    def setup(self) -> 'Ollama__Service':
        self.aws_client        = Ollama__AWS__Client       ().setup()
        self.user_data_builder = Ollama__User_Data__Builder()
        self.mapper            = Ollama__Stack__Mapper     ()
        self.ip_detector       = Caller__IP__Detector      ()
        self.name_gen          = Stack__Name__Generator    ()
        self.ami_helper        = Ollama__AMI__Helper       ()
        return self

    def cli_spec(self):
        from sg_compute.cli.base.Schema__Spec__CLI__Spec import Schema__Spec__CLI__Spec
        return Schema__Spec__CLI__Spec(
            spec_id               = 'ollama'                          ,
            display_name          = 'Ollama'                          ,
            default_instance_type = DEFAULT_INSTANCE_TYPE              ,
            create_request_cls    = Schema__Ollama__Create__Request    ,
            service_factory       = lambda: Ollama__Service().setup()  ,
            health_path           = '/api/tags'                       ,
            health_port           = 11434                              ,
        )

    def create_stack(self, request : Schema__Ollama__Create__Request,
                           creator : str = '') -> Schema__Ollama__Create__Response:
        t0          = time.monotonic()
        stack_name  = str(request.stack_name)    or self.name_gen.generate()
        region      = str(request.region)        or DEFAULT_REGION
        caller_ip   = str(request.caller_ip)     or self.ip_detector.detect()
        if not caller_ip:
            raise ValueError(
                'Could not detect your public IP automatically.\n'
                '  Pass it explicitly: sg-compute spec ollama create --caller-ip <your-ip>')
        ami_id      = str(request.from_ami)      or self.ami_helper.resolve_for_base(region, request.ami_base)
        itype       = str(request.instance_type) or DEFAULT_INSTANCE_TYPE
        allowed_cidr = str(request.allowed_cidr) or f'{caller_ip}/32'
        gpu_required = request.gpu_required and _is_gpu_instance(itype)

        sg_id = self.aws_client.sg.ensure_security_group(
            region, stack_name, caller_ip,
            inbound_ports=[],
            extra_cidrs={11434: allowed_cidr})

        extra = {TAG_MODEL: str(request.model_name)}
        tags  = self.aws_client.tags.build(stack_name, caller_ip, creator, extra_tags=extra)

        user_data = self.user_data_builder.render(
            stack_name   = stack_name                  ,
            region       = region                      ,
            model_name   = str(request.model_name)     ,
            gpu_required = gpu_required                ,
            pull_on_boot = request.pull_on_boot        ,
            max_hours    = request.max_hours           ,
            with_claude  = request.with_claude         ,
            expose_api   = request.expose_api          ,
        )
        iid = self.aws_client.launch.run_instance(
            region        = region            ,
            ami_id        = ami_id            ,
            sg_id         = sg_id             ,
            user_data     = user_data         ,
            tags          = tags              ,
            instance_type = itype             ,
            max_hours     = request.max_hours ,
        )
        info = Schema__Ollama__Info(
            instance_id       = iid                ,
            stack_name        = stack_name         ,
            region            = region             ,
            ami_id            = ami_id             ,
            instance_type     = itype              ,
            security_group_id = sg_id              ,
            model_name        = str(request.model_name),
            state             = 'pending'          ,
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

    # ── ollama-specific extras ────────────────────────────────────────────────

    def pull_model(self, region: str, name: str, model_name: str):
        return self.exec(region, name, f'ollama pull {model_name}', timeout_sec=PULL_TIMEOUT_SEC)

    def claude_session(self, region: str, name: str) -> str:
        return self.connect_target(region, name)

    def create_node(self, base_request, api_key_ssm_path=None) -> 'Schema__Node__Info':
        from sg_compute.core.node.schemas.Schema__Node__Info import Schema__Node__Info
        from sg_compute.primitives.enums.Enum__Node__State   import Enum__Node__State
        ollama_req = Schema__Ollama__Create__Request(
            stack_name    = str(base_request.node_name)     ,
            region        = str(base_request.region)        ,
            instance_type = str(base_request.instance_type) ,
            from_ami      = str(base_request.ami_id)        ,
            caller_ip     = str(base_request.caller_ip)     ,
            max_hours     = int(base_request.max_hours)     ,
        )
        resp = self.create_stack(ollama_req)
        info = resp.stack_info
        return Schema__Node__Info(
            node_id       = str(info.stack_name)      ,
            spec_id       = 'ollama'                  ,
            region        = str(base_request.region)  ,
            state         = Enum__Node__State.BOOTING ,
            instance_id   = str(info.instance_id)     ,
            instance_type = str(info.instance_type)   ,
        )
