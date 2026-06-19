# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Content_Proxy__Service
# Tier-1 orchestrator. Launches the content-transformation proxy EC2 stack via the
# SAME shared EC2 foundation `sg va create` uses (Content_Proxy__AWS__Client →
# EC2__* helpers). health/exec/connect inherited from Spec__Service__Base.
# ═══════════════════════════════════════════════════════════════════════════════

import math
import os
import secrets
import time

from typing                                                                         import Optional

from sg_compute.cli.base.Schema__Spec__CLI__Spec                                    import Schema__Spec__CLI__Spec
from sg_compute.core.spec.Spec__Service__Base                                       import Spec__Service__Base
from sg_compute.platforms.ec2.networking.Caller__IP__Detector                       import Caller__IP__Detector
from sg_compute.platforms.ec2.networking.Stack__Name__Generator                     import Stack__Name__Generator

from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Tls                    import Enum__Content_Proxy__Tls
from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__Create__Request   import Schema__Content_Proxy__Create__Request
from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__Create__Response  import Schema__Content_Proxy__Create__Response
from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__Delete__Response  import Schema__Content_Proxy__Delete__Response
from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__List              import Schema__Content_Proxy__List
from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__Stack__Info       import Schema__Content_Proxy__Stack__Info
from sg_compute_specs.content_proxy.service.Content_Proxy__AWS__Client               import Content_Proxy__AWS__Client, STACK_TYPE
from sg_compute_specs.content_proxy.service.Content_Proxy__Stack__Mapper             import Content_Proxy__Stack__Mapper, TAG_MODE, TAG_TLS
from sg_compute_specs.content_proxy.service.Content_Proxy__User_Data__Builder        import Content_Proxy__User_Data__Builder


DEFAULT_REGION        = 'eu-west-2'
DEFAULT_INSTANCE_TYPE = 't3.large'
PROFILE_NAME          = 'playwright-ec2'                                            # IAM instance profile (SSM + ECR), shared


def _parse_env(text: str) -> dict:                                                  # KEY=VALUE lines from a .env string
    env = {}
    for line in (text or '').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip()
    return env
EXT_PROXY_PORT        = 8080                                                        # mitmproxy-ext (human browser, Mode 1)
VAULT_PORT            = 443                                                         # vault-app front door (Mode 2 / UX)
ACME_PORT             = 80                                                          # cert-init http-01 (letsencrypt-ip only)


class Content_Proxy__Service(Spec__Service__Base):
    aws_client        : Optional[Content_Proxy__AWS__Client]      = None
    mapper            : Optional[Content_Proxy__Stack__Mapper]    = None
    ip_detector       : Optional[Caller__IP__Detector]           = None
    name_gen          : Optional[Stack__Name__Generator]         = None
    user_data_builder : Optional[Content_Proxy__User_Data__Builder] = None
    probe_scheme      : str = 'http'                                                # set by health() per the stack's tls

    def setup(self) -> 'Content_Proxy__Service':
        self.aws_client        = Content_Proxy__AWS__Client().setup()
        self.mapper            = Content_Proxy__Stack__Mapper()
        self.ip_detector       = Caller__IP__Detector()
        self.name_gen          = Stack__Name__Generator()
        self.user_data_builder = Content_Proxy__User_Data__Builder()
        return self

    def cli_spec(self) -> Schema__Spec__CLI__Spec:
        return Schema__Spec__CLI__Spec(
            spec_id               = 'content_proxy'                          ,
            display_name          = 'Content-Transformation Proxy'           ,
            default_instance_type = DEFAULT_INSTANCE_TYPE                     ,
            create_request_cls    = Schema__Content_Proxy__Create__Request   ,
            service_factory       = lambda: Content_Proxy__Service().setup() ,
            health_path           = '/'                                      ,   # vault-app front door responds <500 → healthy
            health_port           = VAULT_PORT                               ,
            health_scheme         = self.probe_scheme                        )   # http for NONE; https for TLS stacks (set by health())

    def health(self, region: str, name: str, timeout_sec: int = 0, poll_sec: int = 10):
        info = self.get_stack_info(region, name)                                    # pick scheme from the stack's tls tag
        self.probe_scheme = 'https' if (info is not None and info.tls != Enum__Content_Proxy__Tls.NONE) else 'http'
        return super().health(region, name, timeout_sec=timeout_sec, poll_sec=poll_sec)

    def create_stack(self, request: Schema__Content_Proxy__Create__Request,
                           creator: str = '') -> Schema__Content_Proxy__Create__Response:
        t0         = time.monotonic()
        stack_name = str(request.stack_name)    or self.name_gen.generate()
        region     = str(request.region)        or DEFAULT_REGION
        caller_ip  = str(request.caller_ip)     or self.ip_detector.detect()
        ami_id     = str(request.from_ami)      or self.aws_client.ami.latest_al2023_ami(region)
        itype      = str(request.instance_type) or DEFAULT_INSTANCE_TYPE
        request.stack_name = stack_name                                             # so user-data / tags see the resolved name

        inbound = [EXT_PROXY_PORT, VAULT_PORT]
        if request.tls == Enum__Content_Proxy__Tls.LETSENCRYPT:
            inbound.append(ACME_PORT)                                               # cert-init http-01 challenge needs :80
        sg_id = self.aws_client.sg.ensure_security_group(region, stack_name, caller_ip,
                                                         inbound_ports=inbound)
        tags  = self.aws_client.tags.build(stack_name, caller_ip, creator,
                                           extra_tags={TAG_MODE: request.mode.value,
                                                       TAG_TLS : request.tls.value })
        # app secrets: reuse what a supplied --env-file already defines; generate only if absent
        env_map        = _parse_env(str(request.env_inline))
        fastapi_key    = env_map.get('FASTAPI_API_KEY_VALUE')  or secrets.token_urlsafe(24)
        playwright_key = env_map.get('SG_PLAYWRIGHT__API_KEY') or secrets.token_urlsafe(24)
        keys_from_env  = bool(env_map.get('FASTAPI_API_KEY_VALUE') or env_map.get('SG_PLAYWRIGHT__API_KEY'))
        aws_creds = {}
        if bool(request.forward_aws_creds):                                          # parity path — bake operator creds; else instance role
            for k in ('AWS_ACCOUNT_ID', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY'):
                v = os.environ.get(k, '')
                if v:
                    aws_creds[k] = v
        user_data = self.user_data_builder.render(request,
                                                  fastapi_api_key    = fastapi_key        ,
                                                  playwright_api_key = playwright_key     ,
                                                  region             = region             ,
                                                  aws_creds          = aws_creds          ,
                                                  env_override       = str(request.env_inline))
        iid = self.aws_client.launch.run_instance(region                = region            ,
                                                  ami_id                = ami_id            ,
                                                  sg_id                 = sg_id             ,
                                                  user_data             = user_data         ,
                                                  tags                  = tags              ,
                                                  instance_type         = itype             ,
                                                  instance_profile_name = PROFILE_NAME      ,
                                                  max_hours             = int(math.ceil(request.max_hours)),  # >0 → on-demand terminate-on-shutdown flag
                                                  disk_size_gb          = int(request.disk_size_gb),
                                                  use_spot              = bool(request.use_spot))
        info = self.mapper.to_info({'InstanceId'    : iid                          ,
                                    'InstanceType'  : itype                        ,
                                    'ImageId'       : ami_id                       ,
                                    'State'         : {'Name': 'pending'}          ,
                                    'SecurityGroups': [{'GroupId': sg_id}]         ,
                                    'Tags'          : tags                         }, region)
        env_src    = 'env-file' if str(request.env_inline) else ('baked AWS creds' if aws_creds else 'instance role')
        creds_path = env_src
        return Schema__Content_Proxy__Create__Response(
            stack_info         = info                                        ,
            fastapi_api_key    = fastapi_key                                 ,
            playwright_api_key = playwright_key                              ,
            secrets_from_env   = keys_from_env                              ,
            message    = f'Instance {iid} launching ({STACK_TYPE}, {request.proxy_tool.value}, S3 via {creds_path})',
            elapsed_ms = int((time.monotonic() - t0) * 1000)                 )

    def list_stacks(self, region: str = '') -> Schema__Content_Proxy__List:
        region = region or DEFAULT_REGION
        raw    = self.aws_client.instance.list_by_stack_type(region, STACK_TYPE)
        stacks = [self.mapper.to_info(d, region) for d in raw.values()]
        return Schema__Content_Proxy__List(region=region, stacks=stacks, total=len(stacks))

    def get_stack_info(self, region: str, stack_name: str) -> Optional[Schema__Content_Proxy__Stack__Info]:
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        return self.mapper.to_info(details, region) if details else None

    def delete_stack(self, region: str, stack_name: str) -> Schema__Content_Proxy__Delete__Response:
        t0      = time.monotonic()
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        if not details:
            return Schema__Content_Proxy__Delete__Response(stack_name=stack_name, deleted=False,
                                                          message='stack not found',
                                                          elapsed_ms=int((time.monotonic() - t0) * 1000))
        iid   = details.get('InstanceId', '')
        sg_id = (details.get('SecurityGroups') or [{}])[0].get('GroupId', '')
        ok    = self.aws_client.instance.terminate(region, iid)
        if ok and sg_id:
            self.aws_client.sg.delete_security_group(region, sg_id)
        return Schema__Content_Proxy__Delete__Response(stack_name=stack_name, deleted=bool(ok),
                                                      message=f'terminated {iid}' if ok else 'terminate failed',
                                                      elapsed_ms=int((time.monotonic() - t0) * 1000))
