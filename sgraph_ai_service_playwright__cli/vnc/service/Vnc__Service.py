# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Vnc__Service
# Tier-1 pure-logic orchestrator for sp vnc. Composes the per-concern helpers
# and exposes the operations consumed by both the typer CLI (Tier 2A) and the
# FastAPI routes (Tier 2B).
#
# Operations:
#   - list_stacks(region)
#   - get_stack_info(region, stack_name)
#   - delete_stack(region, stack_name)
#   - health(region, stack_name)
#   - flows(region, stack_name)                                                  ← peek mitmweb flows (per N4, no auto-export)
#   - create_stack(request, creator='')                                          (wired in step 7f)
# ═══════════════════════════════════════════════════════════════════════════════

import secrets

from typing                                                                         import Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.ec2.collections.List__Instance__Id           import List__Instance__Id
from sgraph_ai_service_playwright__cli.vnc.collections.List__Schema__Vnc__Mitm__Flow__Summary import List__Schema__Vnc__Mitm__Flow__Summary
from sgraph_ai_service_playwright__cli.vnc.collections.List__Schema__Vnc__Stack__Info import List__Schema__Vnc__Stack__Info
from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Interceptor__Kind       import Enum__Vnc__Interceptor__Kind
from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Stack__State            import Enum__Vnc__Stack__State
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Health              import Schema__Vnc__Health
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Mitm__Flow__Summary import Schema__Vnc__Mitm__Flow__Summary
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Create__Request  import Schema__Vnc__Stack__Create__Request
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Create__Response import Schema__Vnc__Stack__Create__Response
from sgraph_ai_service_playwright__cli.vnc.service.Vnc__AWS__Client                 import VNC_NAMING
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Delete__Response import Schema__Vnc__Stack__Delete__Response
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Info         import Schema__Vnc__Stack__Info
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__List         import Schema__Vnc__Stack__List


DEFAULT_REGION        = 'eu-west-2'
DEFAULT_INSTANCE_TYPE = 't3.large'                                                  # 2 vCPU / 8 GB — chromium needs RAM headroom for VNC + tabs (mirrors Vnc__Launch__Helper)
PASSWORD_BYTES        = 24                                                          # secrets.token_urlsafe(24) ⇒ 32-char URL-safe base64
PROFILE_NAME          = 'playwright-ec2'                                            # Reuses the existing IAM instance profile (has AmazonSSMManagedInstanceCore — required for `sp vnc connect`)


def _flow_summary_from_mitmweb(flow: dict) -> Schema__Vnc__Mitm__Flow__Summary:     # Pure mapper — mitmweb /api/flows shape → schema
    request  = flow.get('request' , {}) or {}
    response = flow.get('response', {}) or {}
    return Schema__Vnc__Mitm__Flow__Summary(flow_id        = str(flow.get('id', '') or '')                                       ,
                                              method         = str(request.get('method', '') or '')                                ,
                                              url            = str(request.get('pretty_url') or request.get('url', '') or '')     ,
                                              status_code    = int(response.get('status_code') or 0)                               ,
                                              intercepted_at = str(flow.get('timestamp_created', '') or ''))


class Vnc__Service(Type_Safe):
    aws_client           : object = None                                            # Vnc__AWS__Client              (lazy via setup())
    probe                : object = None                                            # Vnc__HTTP__Probe              (lazy via setup())
    mapper               : object = None                                            # Vnc__Stack__Mapper            (lazy via setup())
    ip_detector          : object = None                                            # Caller__IP__Detector          (lazy via setup())
    name_gen             : object = None                                            # Random__Stack__Name__Generator (lazy via setup())
    compose_template     : object = None                                            # Vnc__Compose__Template        (lazy via setup())
    user_data_builder    : object = None                                            # Vnc__User_Data__Builder       (lazy via setup())
    interceptor_resolver : object = None                                            # Vnc__Interceptor__Resolver    (lazy via setup())

    def setup(self) -> 'Vnc__Service':                                              # Lazy imports avoid circular module-load
        from sgraph_ai_service_playwright__cli.vnc.service.Caller__IP__Detector            import Caller__IP__Detector
        from sgraph_ai_service_playwright__cli.vnc.service.Random__Stack__Name__Generator  import Random__Stack__Name__Generator
        from sgraph_ai_service_playwright__cli.vnc.service.Vnc__AWS__Client                import Vnc__AWS__Client
        from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Compose__Template          import Vnc__Compose__Template
        from sgraph_ai_service_playwright__cli.vnc.service.Vnc__HTTP__Base                 import Vnc__HTTP__Base
        from sgraph_ai_service_playwright__cli.vnc.service.Vnc__HTTP__Probe                import Vnc__HTTP__Probe
        from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Interceptor__Resolver      import Vnc__Interceptor__Resolver
        from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Stack__Mapper              import Vnc__Stack__Mapper
        from sgraph_ai_service_playwright__cli.vnc.service.Vnc__User_Data__Builder         import Vnc__User_Data__Builder
        self.aws_client           = Vnc__AWS__Client()       .setup()
        self.probe                = Vnc__HTTP__Probe(http=Vnc__HTTP__Base())
        self.mapper               = Vnc__Stack__Mapper()
        self.ip_detector          = Caller__IP__Detector()
        self.name_gen             = Random__Stack__Name__Generator()
        self.compose_template     = Vnc__Compose__Template()
        self.user_data_builder    = Vnc__User_Data__Builder()
        self.interceptor_resolver = Vnc__Interceptor__Resolver()
        return self

    def create_stack(self, request: Schema__Vnc__Stack__Create__Request, creator: str = '') -> Schema__Vnc__Stack__Create__Response:
        stack_name  = str(request.stack_name)         or f'vnc-{self.name_gen.generate()}'  # Empty → 'vnc-{adjective}-{scientist}'
        region      = str(request.region)             or DEFAULT_REGION
        caller_ip   = str(request.caller_ip)          or str(self.ip_detector.detect())
        password    = str(request.operator_password)  or secrets.token_urlsafe(PASSWORD_BYTES)
        ami_id      = str(request.from_ami)           or self.aws_client.ami.latest_al2023_ami_id(region)
        inst_type   = str(request.instance_type)      or DEFAULT_INSTANCE_TYPE

        source, label = self.interceptor_resolver.resolve(request.interceptor)              # N5: (source_to_bake, label)
        interceptor_kind_str = str(request.interceptor.kind)                                # 'none' / 'name' / 'inline'

        sg_id        = self.aws_client.sg.ensure_security_group(region, stack_name, caller_ip,
                                                                  public=bool(request.public_ingress))      # --open / public_ingress=True opens 443 to 0.0.0.0/0
        tags         = self.aws_client.tags.build(stack_name, caller_ip, creator, request.interceptor)
        compose_yaml = self.compose_template.render()
        user_data    = self.user_data_builder.render(stack_name         = stack_name        ,
                                                       region             = region            ,
                                                       compose_yaml       = compose_yaml      ,
                                                       interceptor_source = source            ,
                                                       operator_password  = password          ,
                                                       interceptor_kind   = interceptor_kind_str)
        instance_id  = self.aws_client.launch.run_instance(region, ami_id, sg_id, user_data, tags,
                                                              instance_type         = inst_type   ,
                                                              instance_profile_name = PROFILE_NAME)        # Without this, SSM agent has no creds to register — `sp vnc connect` fails with TargetNotConnected.

        return Schema__Vnc__Stack__Create__Response(
            stack_name        = stack_name                                              ,
            aws_name_tag      = VNC_NAMING.aws_name_for_stack(stack_name)               ,
            instance_id       = instance_id                                              ,
            region            = region                                                   ,
            ami_id            = ami_id                                                   ,
            instance_type     = inst_type                                                ,
            security_group_id = sg_id                                                    ,
            caller_ip         = caller_ip                                                ,
            operator_password = password                                                 ,
            interceptor_kind  = request.interceptor.kind                                 ,
            interceptor_name  = label                                                    ,
            state             = Enum__Vnc__Stack__State.PENDING                          )

    def list_stacks(self, region: str) -> Schema__Vnc__Stack__List:
        region = region or DEFAULT_REGION
        raw    = self.aws_client.instance.list_stacks(region)
        stacks = List__Schema__Vnc__Stack__Info()
        for details in raw.values():
            stacks.append(self.mapper.to_info(details, region))
        return Schema__Vnc__Stack__List(region=region, stacks=stacks)

    def get_stack_info(self, region: str, stack_name: str) -> Optional[Schema__Vnc__Stack__Info]:
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        return self.mapper.to_info(details, region) if details else None

    def delete_stack(self, region: str, stack_name: str) -> Schema__Vnc__Stack__Delete__Response:
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        if not details:
            return Schema__Vnc__Stack__Delete__Response()                           # Empty fields ⇒ route returns 404
        instance_id = details.get('InstanceId', '')
        ok          = self.aws_client.instance.terminate_instance(region, instance_id)
        terminated  = List__Instance__Id()
        if ok and instance_id:
            terminated.append(instance_id)
        return Schema__Vnc__Stack__Delete__Response(target=instance_id, stack_name=stack_name, terminated_instance_ids=terminated)

    def health(self, region: str, stack_name: str, username: str = '', password: str = '') -> Schema__Vnc__Health:
        info = self.get_stack_info(region, stack_name)
        if info is None or not str(info.public_ip):
            return Schema__Vnc__Health(stack_name=stack_name, error='instance not running or no public IP')
        viewer_url     = str(info.viewer_url )
        mitmweb_url    = str(info.mitmweb_url)
        nginx_ok       = self.probe.nginx_ready  (viewer_url , username, password)
        mitmweb_ok     = self.probe.mitmweb_ready(mitmweb_url, username, password)
        if mitmweb_ok:
            flow_count = len(self.probe.flows_listing(mitmweb_url, username, password))
        else:
            flow_count = -1                                                         # Sentinel: probe couldn't list
        state = Enum__Vnc__Stack__State.READY if (nginx_ok and mitmweb_ok) else info.state
        return Schema__Vnc__Health(stack_name = stack_name ,
                                     state      = state      ,
                                     nginx_ok   = nginx_ok   ,
                                     mitmweb_ok = mitmweb_ok ,
                                     flow_count = flow_count )

    def flows(self, region: str, stack_name: str, username: str = '', password: str = '') -> List__Schema__Vnc__Mitm__Flow__Summary:
        info = self.get_stack_info(region, stack_name)
        out  = List__Schema__Vnc__Mitm__Flow__Summary()
        if info is None or not str(info.public_ip):
            return out
        for flow in self.probe.flows_listing(str(info.mitmweb_url), username, password):
            out.append(_flow_summary_from_mitmweb(flow))
        return out
