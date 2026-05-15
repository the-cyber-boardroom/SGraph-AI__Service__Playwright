# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — playwright: Playwright__Service
# Orchestrator for the playwright stack. Extends Spec__Service__Base —
# health/exec/connect_target inherited; spec-specific bits below.
#
# Containers on the launched node:
#   default          — host-plane + sg-playwright                (2 containers)
#   --with-mitmproxy — + agent-mitmproxy                         (3 containers)
# ═══════════════════════════════════════════════════════════════════════════════

import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing   import Optional

from sg_compute.core.spec.Spec__Service__Base                   import Spec__Service__Base
from sg_compute.platforms.ec2.networking.Caller__IP__Detector   import Caller__IP__Detector
from sg_compute.platforms.ec2.networking.Stack__Name__Generator import Stack__Name__Generator

from sg_compute_specs.playwright.schemas.Schema__Playwright__Create__Request  import Schema__Playwright__Create__Request
from sg_compute_specs.playwright.schemas.Schema__Playwright__Create__Response import Schema__Playwright__Create__Response
from sg_compute_specs.playwright.schemas.Schema__Playwright__Delete__Response import Schema__Playwright__Delete__Response
from sg_compute_specs.playwright.schemas.Schema__Playwright__List             import Schema__Playwright__List
from sg_compute_specs.playwright.service.Playwright__AMI__Helper              import Playwright__AMI__Helper
from sg_compute_specs.playwright.service.Playwright__AWS__Client              import Playwright__AWS__Client, ecr_registry_host
from sg_compute_specs.playwright.service.Playwright__Stack__Mapper            import (Playwright__Stack__Mapper,
                                                                                       STACK_TYPE               ,
                                                                                       TAG_TERMINATE_AT         ,
                                                                                       TAG_WITH_MITMPROXY       )
from sg_compute_specs.playwright.service.Playwright__User_Data__Builder       import Playwright__User_Data__Builder

DEFAULT_REGION        = os.environ.get('AWS_DEFAULT_REGION', 'eu-west-2')
DEFAULT_INSTANCE_TYPE = 't3.medium'
PROFILE_NAME          = 'playwright-ec2'             # IAM profile granting SSM + ECR access
PLAYWRIGHT_PORT       = 8000                         # sg-playwright FastAPI — the public surface
SIDECAR_ADMIN_PORT    = 8001                         # agent-mitmproxy admin API — published only with --with-mitmproxy


class Playwright__Service(Spec__Service__Base):
    aws_client        : Optional[Playwright__AWS__Client]        = None
    user_data_builder : Optional[Playwright__User_Data__Builder] = None
    mapper            : Optional[Playwright__Stack__Mapper]      = None
    ip_detector       : Optional[Caller__IP__Detector]          = None
    name_gen          : Optional[Stack__Name__Generator]        = None
    ami_helper        : Optional[Playwright__AMI__Helper]        = None

    def setup(self) -> 'Playwright__Service':
        self.aws_client        = Playwright__AWS__Client       ().setup()
        self.user_data_builder = Playwright__User_Data__Builder()
        self.mapper            = Playwright__Stack__Mapper     ()
        self.ip_detector       = Caller__IP__Detector          ()
        self.name_gen          = Stack__Name__Generator        ()
        self.ami_helper        = Playwright__AMI__Helper       ()
        return self

    def cli_spec(self):
        from sg_compute.cli.base.Schema__Spec__CLI__Spec import Schema__Spec__CLI__Spec
        return Schema__Spec__CLI__Spec(
            spec_id               = 'playwright'                               ,
            display_name          = 'Playwright'                               ,
            default_instance_type = DEFAULT_INSTANCE_TYPE                      ,
            create_request_cls    = Schema__Playwright__Create__Request         ,
            service_factory       = lambda: Playwright__Service().setup()      ,
            health_path           = '/health/status'                           ,
            health_port           = PLAYWRIGHT_PORT                            ,
            health_scheme         = 'http'                                     ,
        )

    def create_stack(self, request : Schema__Playwright__Create__Request,
                           creator : str = '') -> Schema__Playwright__Create__Response:
        t0           = time.monotonic()
        stack_name   = str(request.stack_name)    or self.name_gen.generate()
        region       = str(request.region)        or DEFAULT_REGION
        caller_ip    = str(request.caller_ip)     or self.ip_detector.detect()
        if not caller_ip:
            raise ValueError(
                'Could not detect your public IP automatically.\n'
                '  Pass it explicitly: sg playwright create --caller-ip <your-ip>')
        ami_id       = str(request.from_ami)      or self.ami_helper.resolve(region)
        itype        = str(request.instance_type) or DEFAULT_INSTANCE_TYPE
        api_key      = str(request.api_key)       or secrets.token_urlsafe(24)
        ecr_registry = ecr_registry_host(region)

        # sg-playwright (:8000) is always published; agent-mitmproxy's admin API
        # (:8001) only when --with-mitmproxy. host-plane stays internal.
        inbound_ports = [PLAYWRIGHT_PORT]
        if bool(request.with_mitmproxy):
            inbound_ports.append(SIDECAR_ADMIN_PORT)
        sg_id = self.aws_client.sg.ensure_security_group(
            region, stack_name, caller_ip,
            inbound_ports=inbound_ports,
            extra_cidrs={})

        extra = {TAG_WITH_MITMPROXY: 'true' if request.with_mitmproxy else 'false'}
        if float(request.max_hours) > 0:
            terminate_at = datetime.now(timezone.utc) + timedelta(hours=float(request.max_hours))
            extra[TAG_TERMINATE_AT] = terminate_at.strftime('%Y-%m-%dT%H:%M:%SZ')
        tags = self.aws_client.tags.build(stack_name, caller_ip, creator, extra_tags=extra)

        user_data = self.user_data_builder.render(
            stack_name       = stack_name                    ,
            region           = region                        ,
            ecr_registry     = ecr_registry                  ,
            api_key          = api_key                        ,
            with_mitmproxy   = bool(request.with_mitmproxy)   ,
            intercept_script = str(request.intercept_script)  ,
            image_tag        = str(request.image_tag) or 'latest' ,
            max_hours        = float(request.max_hours)       )
        iid = self.aws_client.launch.run_instance(
            region                = region                   ,
            ami_id                = ami_id                   ,
            sg_id                 = sg_id                    ,
            user_data             = user_data                ,
            tags                  = tags                     ,
            instance_type         = itype                    ,
            max_hours             = int(request.max_hours)    ,
            instance_profile_name = PROFILE_NAME              ,
            disk_size_gb          = int(request.disk_size_gb) ,
            use_spot              = bool(request.use_spot)    )
        info = self.mapper.to_info({'InstanceId'    : iid                  ,
                                    'InstanceType'  : itype                ,
                                    'ImageId'       : ami_id               ,
                                    'State'         : {'Name': 'pending'}  ,
                                    'SecurityGroups': [{'GroupId': sg_id}] ,
                                    'Tags'          : tags                 },
                                   region)
        mode = 'with-mitmproxy (3 containers)' if request.with_mitmproxy else 'default (2 containers)'
        return Schema__Playwright__Create__Response(
            stack_info = info                                       ,
            api_key    = api_key                                    ,
            message    = f'Instance {iid} launching ({mode})'      ,
            elapsed_ms = int((time.monotonic() - t0) * 1000)        )

    def list_stacks(self, region: str = '') -> Schema__Playwright__List:
        region = region or DEFAULT_REGION
        raw    = self.aws_client.instance.list_by_stack_type(region, STACK_TYPE)
        stacks = [self.mapper.to_info(d, region) for d in raw.values()]
        return Schema__Playwright__List(region=region, stacks=stacks, total=len(stacks))

    def get_stack_info(self, region: str, stack_name: str):
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        return self.mapper.to_info(details, region) if details else None

    def delete_stack(self, region: str, stack_name: str) -> Schema__Playwright__Delete__Response:
        t0      = time.monotonic()
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        if not details:
            return Schema__Playwright__Delete__Response(
                stack_name = stack_name       ,
                message    = 'stack not found',
                elapsed_ms = int((time.monotonic() - t0) * 1000))
        iid   = details.get('InstanceId', '')
        sg_id = (details.get('SecurityGroups') or [{}])[0].get('GroupId', '')
        ok    = self.aws_client.instance.terminate(region, iid)
        if ok and sg_id:
            self.aws_client.sg.delete_security_group(region, sg_id)
        return Schema__Playwright__Delete__Response(
            stack_name = stack_name                                         ,
            deleted    = ok                                                 ,
            message    = f'terminated {iid}' if ok else 'terminate failed' ,
            elapsed_ms = int((time.monotonic() - t0) * 1000)               )
