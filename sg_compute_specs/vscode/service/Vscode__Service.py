# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode: Vscode__Service
# Orchestrator for the vscode stack. Extends Spec__Service__Base —
# exec/connect_target inherited (connect_target gives the SSM-shell terminal
# path); health overridden to probe code-server over SSM (loopback-bound).
# Slice 2: SSM_FORWARD mode only. PUBLIC_HTTPS lands in Slice 3.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import secrets
import time
from datetime import datetime, timezone, timedelta

from typing import Optional

from sg_compute.core.spec.Spec__Service__Base                     import Spec__Service__Base
from sg_compute.platforms.ec2.networking.Caller__IP__Detector     import Caller__IP__Detector
from sg_compute.platforms.ec2.networking.Stack__Name__Generator   import Stack__Name__Generator

from sg_compute_specs.vscode.enums.Enum__Vscode__Ingress              import Enum__Vscode__Ingress
from sg_compute_specs.vscode.schemas.Schema__Vscode__Create__Request  import Schema__Vscode__Create__Request
from sg_compute_specs.vscode.schemas.Schema__Vscode__Create__Response import Schema__Vscode__Create__Response
from sg_compute_specs.vscode.schemas.Schema__Vscode__Delete__Response import Schema__Vscode__Delete__Response
from sg_compute_specs.vscode.schemas.Schema__Vscode__Info             import Schema__Vscode__Info
from sg_compute_specs.vscode.schemas.Schema__Vscode__List             import Schema__Vscode__List
from sg_compute_specs.vscode.service.Vscode__AMI__Helper              import Vscode__AMI__Helper
from sg_compute_specs.vscode.service.Vscode__AWS__Client              import Vscode__AWS__Client
from sg_compute_specs.vscode.service.Vscode__Stack__Mapper            import (Vscode__Stack__Mapper ,
                                                                              STACK_TYPE            ,
                                                                              EDITOR_PORT           ,
                                                                              TAG_DISTRIBUTION      ,
                                                                              TAG_INGRESS           ,
                                                                              TAG_TERMINATE_AT      ,
                                                                              ssm_forward_command   ,
                                                                              ssm_session_command   ,
                                                                              vscode_url_for        )
from sg_compute_specs.vscode.service.Vscode__User_Data__Builder       import Vscode__User_Data__Builder

DEFAULT_REGION        = os.environ.get('AWS_DEFAULT_REGION', 'eu-west-2')
DEFAULT_INSTANCE_TYPE = 't3.large'
PROFILE_NAME          = 'playwright-ec2'             # IAM profile granting SSM + ECR access


class Vscode__Service(Spec__Service__Base):
    aws_client        : Optional[Vscode__AWS__Client]        = None
    user_data_builder : Optional[Vscode__User_Data__Builder] = None
    mapper            : Optional[Vscode__Stack__Mapper]      = None
    ip_detector       : Optional[Caller__IP__Detector]       = None
    name_gen          : Optional[Stack__Name__Generator]     = None
    ami_helper        : Optional[Vscode__AMI__Helper]        = None

    def setup(self) -> 'Vscode__Service':
        self.aws_client        = Vscode__AWS__Client       ().setup()
        self.user_data_builder = Vscode__User_Data__Builder()
        self.mapper            = Vscode__Stack__Mapper     ()
        self.ip_detector       = Caller__IP__Detector      ()
        self.name_gen          = Stack__Name__Generator    ()
        self.ami_helper        = Vscode__AMI__Helper       ()
        return self

    def cli_spec(self):
        from sg_compute.cli.base.Schema__Spec__CLI__Spec import Schema__Spec__CLI__Spec
        return Schema__Spec__CLI__Spec(
            spec_id               = 'vscode'                              ,
            display_name          = 'VS Code'                            ,
            default_instance_type = DEFAULT_INSTANCE_TYPE                 ,
            create_request_cls    = Schema__Vscode__Create__Request       ,
            service_factory       = lambda: Vscode__Service().setup()     ,
            health_path           = '/healthz'                            ,
            health_port           = EDITOR_PORT                           ,
            health_scheme         = 'http'                                ,
        )

    def create_stack(self, request : Schema__Vscode__Create__Request,
                           creator : str = '') -> Schema__Vscode__Create__Response:
        t0           = time.monotonic()
        is_public    = request.ingress == Enum__Vscode__Ingress.PUBLIC_HTTPS
        stack_name   = str(request.stack_name)    or self.name_gen.generate()
        region       = str(request.region)        or DEFAULT_REGION
        caller_ip    = str(request.caller_ip)     or self.ip_detector.detect()
        if not caller_ip:
            raise ValueError(
                'Could not detect your public IP automatically.\n'
                '  Pass it explicitly: sg vscode create --caller-ip <your-ip>')
        password     = str(request.password)      or secrets.token_urlsafe(18)
        ami_id       = str(request.from_ami)      or self.ami_helper.resolve(region)
        itype        = str(request.instance_type) or DEFAULT_INSTANCE_TYPE
        disk_gb      = int(request.disk_size_gb)

        # SSM_FORWARD: editor binds to loopback — open NO inbound ports.
        # PUBLIC_HTTPS: Caddy serves :443 (+:80 for ACM) — open to caller /32, or
        #               0.0.0.0/0 when --public (code-server's password still gates).
        if is_public and request.public_ingress:
            inbound_ports, extra_cidrs = [], {443: '0.0.0.0/0', 80: '0.0.0.0/0'}
        elif is_public:
            inbound_ports, extra_cidrs = [443, 80], {}
        else:
            inbound_ports, extra_cidrs = [], {}
        sg_id = self.aws_client.sg.ensure_security_group(
            region, stack_name, caller_ip,
            inbound_ports=inbound_ports,
            extra_cidrs=extra_cidrs)

        extra = {
            TAG_DISTRIBUTION: request.distribution.value ,
            TAG_INGRESS     : request.ingress.value      ,
        }
        if float(request.max_hours) > 0:
            terminate_at = datetime.now(timezone.utc) + timedelta(hours=float(request.max_hours))
            extra[TAG_TERMINATE_AT] = terminate_at.strftime('%Y-%m-%dT%H:%M:%SZ')
        tags = self.aws_client.tags.build(stack_name, caller_ip, creator, extra_tags=extra)

        user_data = self.user_data_builder.render(
            stack_name   = stack_name              ,
            region       = region                  ,
            password     = password                ,
            distribution = request.distribution    ,
            ingress      = request.ingress         ,
            max_hours    = float(request.max_hours),
        )
        iid = self.aws_client.launch.run_instance(
            region                = region                  ,
            ami_id                = ami_id                  ,
            sg_id                 = sg_id                   ,
            user_data             = user_data               ,
            tags                  = tags                    ,
            instance_type         = itype                   ,
            max_hours             = float(request.max_hours),
            instance_profile_name = PROFILE_NAME            ,
            disk_size_gb          = disk_gb                 ,
            use_spot              = bool(request.use_spot)  ,
        )
        info = Schema__Vscode__Info(
            instance_id       = iid                                            ,
            stack_name        = stack_name                                     ,
            region            = region                                         ,
            ami_id            = ami_id                                         ,
            instance_type     = itype                                          ,
            security_group_id = sg_id                                          ,
            distribution      = request.distribution.value                     ,
            ingress           = request.ingress.value                          ,
            vscode_url        = vscode_url_for(request.ingress.value, '')       ,
            ssm_forward       = ssm_forward_command(iid, region)               ,
            ssm_session       = ssm_session_command(iid, region)               ,
            disk_size_gb      = disk_gb                                        ,
            state             = 'pending'                                      ,
        )
        return Schema__Vscode__Create__Response(
            stack_info = info                                 ,
            password   = password                             ,
            message    = f'Instance {iid} launching'          ,
            elapsed_ms = int((time.monotonic() - t0) * 1000)  ,
        )

    def list_stacks(self, region: str = '') -> Schema__Vscode__List:
        region = region or DEFAULT_REGION
        raw    = self.aws_client.instance.list_by_stack_type(region, STACK_TYPE)
        stacks = [self.mapper.to_info(d, region) for d in raw.values()]
        return Schema__Vscode__List(region=region, stacks=stacks, total=len(stacks))

    def get_stack_info(self, region: str, stack_name: str):
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        return self.mapper.to_info(details, region) if details else None

    def delete_stack(self, region: str, stack_name: str) -> Schema__Vscode__Delete__Response:
        t0      = time.monotonic()
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        if not details:
            return Schema__Vscode__Delete__Response(
                stack_name = stack_name        ,
                message    = 'stack not found' ,
                elapsed_ms = int((time.monotonic() - t0) * 1000))
        iid   = details.get('InstanceId', '')
        sg_id = (details.get('SecurityGroups') or [{}])[0].get('GroupId', '')
        ok    = self.aws_client.instance.terminate(region, iid)
        if ok and sg_id:
            self.aws_client.sg.delete_security_group(region, sg_id)
        return Schema__Vscode__Delete__Response(
            stack_name = stack_name                                         ,
            deleted    = ok                                                 ,
            message    = f'terminated {iid}' if ok else 'terminate failed' ,
            elapsed_ms = int((time.monotonic() - t0) * 1000)               ,
        )

    # ── health: code-server binds to 127.0.0.1 — probe it over SSM. ───────────

    def health(self, region: str, name: str, timeout_sec: int = 0, poll_sec: int = 10):
        from sg_compute.cli.base.schemas.Schema__CLI__Health__Probe import Schema__CLI__Health__Probe
        t0       = time.monotonic()
        probe    = Schema__CLI__Health__Probe()
        deadline = time.monotonic() + max(timeout_sec, 0)
        while True:
            try:
                marker = self.exec(region, name,
                                   'test -f /var/lib/sg-compute-boot-failed && '
                                   'tail -n 30 /var/log/ephemeral-ec2-boot.log || true',
                                   timeout_sec=30)
                tail = str(getattr(marker, 'stdout', '') or '').strip()
                if tail:
                    probe.healthy    = False
                    probe.state      = 'failed'
                    probe.last_error = tail[:1500]
                    break
            except Exception:
                pass
            try:
                result = self.exec(region, name,
                                   f'curl -sf http://127.0.0.1:{EDITOR_PORT}/healthz',
                                   timeout_sec=30)
                stdout = str(getattr(result, 'stdout', '') or '')
                if 'alive' in stdout or stdout.strip().startswith('{'):
                    probe.healthy    = True
                    probe.state      = 'running'
                    probe.last_error = ''
                    break
                probe.state      = 'starting'
                probe.last_error = (stdout[:256] if stdout else 'no response from code-server')
            except Exception as exc:
                probe.state      = 'starting'
                probe.last_error = str(exc)[:512]
            if time.monotonic() >= deadline:
                break
            time.sleep(poll_sec)
        probe.elapsed_ms = int((time.monotonic() - t0) * 1000)
        return probe
