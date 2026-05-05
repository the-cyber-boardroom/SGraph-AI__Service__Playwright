# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — VNC: Vnc__Service
# ═══════════════════════════════════════════════════════════════════════════════

import secrets

from typing                                                                         import Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sg_compute.core.event_bus.Event__Bus                    import event_bus
from sg_compute.core.event_bus.schemas.Schema__Stack__Event  import Schema__Stack__Event
from sg_compute.platforms.ec2.collections.List__Instance__Id           import List__Instance__Id
from sg_compute.primitives.Safe_Str__AWS__Region             import Safe_Str__AWS__Region
from sg_compute.primitives.Safe_Str__Message                 import Safe_Str__Message
from sg_compute.primitives.Safe_Str__SSM__Path               import Safe_Str__SSM__Path
from sg_compute.primitives.Safe_Str__Stack__Name             import Safe_Str__Stack__Name

from sg_compute_specs.vnc.collections.List__Schema__Vnc__Mitm__Flow__Summary        import List__Schema__Vnc__Mitm__Flow__Summary
from sg_compute_specs.vnc.collections.List__Schema__Vnc__Stack__Info                import List__Schema__Vnc__Stack__Info
from sg_compute_specs.vnc.enums.Enum__Vnc__Stack__State                             import Enum__Vnc__Stack__State
from sg_compute_specs.vnc.schemas.Schema__Vnc__Health                               import Schema__Vnc__Health
from sg_compute_specs.vnc.schemas.Schema__Vnc__Mitm__Flow__Summary                  import Schema__Vnc__Mitm__Flow__Summary
from sg_compute_specs.vnc.schemas.Schema__Vnc__Stack__Create__Request               import Schema__Vnc__Stack__Create__Request
from sg_compute_specs.vnc.schemas.Schema__Vnc__Stack__Create__Response              import Schema__Vnc__Stack__Create__Response
from sg_compute_specs.vnc.schemas.Schema__Vnc__Stack__Delete__Response              import Schema__Vnc__Stack__Delete__Response
from sg_compute_specs.vnc.schemas.Schema__Vnc__Stack__Info                          import Schema__Vnc__Stack__Info
from sg_compute_specs.vnc.schemas.Schema__Vnc__Stack__List                          import Schema__Vnc__Stack__List
from typing import Optional

from sg_compute_specs.vnc.service.Caller__IP__Detector           import Caller__IP__Detector
from sg_compute_specs.vnc.service.Random__Stack__Name__Generator import Random__Stack__Name__Generator
from sg_compute_specs.vnc.service.Vnc__AWS__Client               import Vnc__AWS__Client
from sg_compute_specs.vnc.service.Vnc__Tags                                  import VNC_NAMING
from sg_compute_specs.vnc.service.Vnc__Compose__Template         import Vnc__Compose__Template
from sg_compute_specs.vnc.service.Vnc__HTTP__Base                import Vnc__HTTP__Base
from sg_compute_specs.vnc.service.Vnc__HTTP__Probe               import Vnc__HTTP__Probe
from sg_compute_specs.vnc.service.Vnc__Interceptor__Resolver     import Vnc__Interceptor__Resolver
from sg_compute_specs.vnc.service.Vnc__Stack__Mapper             import Vnc__Stack__Mapper
from sg_compute_specs.vnc.service.Vnc__User_Data__Builder        import Vnc__User_Data__Builder


DEFAULT_REGION        = 'eu-west-2'
DEFAULT_INSTANCE_TYPE = 't3.large'
PASSWORD_BYTES        = 24                                                          # secrets.token_urlsafe(24) ⇒ 32-char URL-safe base64
PROFILE_NAME          = 'playwright-ec2'                                            # IAM instance profile with AmazonSSMManagedInstanceCore


def _flow_summary_from_mitmweb(flow: dict) -> Schema__Vnc__Mitm__Flow__Summary:
    request  = flow.get('request' , {}) or {}
    response = flow.get('response', {}) or {}
    return Schema__Vnc__Mitm__Flow__Summary(flow_id        = str(flow.get('id', '') or '')                                   ,
                                             method         = str(request.get('method', '') or '')                            ,
                                             url            = str(request.get('pretty_url') or request.get('url', '') or '') ,
                                             status_code    = int(response.get('status_code') or 0)                           ,
                                             intercepted_at = str(flow.get('timestamp_created', '') or ''))


class Vnc__Service(Type_Safe):
    aws_client           : Optional[Vnc__AWS__Client]           = None
    probe                : Optional[Vnc__HTTP__Probe]           = None
    mapper               : Optional[Vnc__Stack__Mapper]         = None
    ip_detector          : Optional[Caller__IP__Detector]       = None
    name_gen             : Optional[Random__Stack__Name__Generator] = None
    compose_template     : Optional[Vnc__Compose__Template]     = None
    user_data_builder    : Optional[Vnc__User_Data__Builder]    = None
    interceptor_resolver : Optional[Vnc__Interceptor__Resolver] = None

    def setup(self) -> 'Vnc__Service':
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
        stack_name = str(request.stack_name)        or f'vnc-{self.name_gen.generate()}'
        region     = str(request.region)            or DEFAULT_REGION
        caller_ip  = str(request.caller_ip)         or str(self.ip_detector.detect())
        password   = str(request.operator_password) or secrets.token_urlsafe(PASSWORD_BYTES)
        ami_id     = str(request.from_ami)          or self.aws_client.ami.latest_al2023_ami_id(region)
        inst_type  = str(request.instance_type)     or DEFAULT_INSTANCE_TYPE

        source, label        = self.interceptor_resolver.resolve(request.interceptor)
        interceptor_kind_str = str(request.interceptor.kind)

        sg_id        = self.aws_client.sg.ensure_security_group(region, stack_name, caller_ip,
                                                                  public=bool(request.public_ingress))
        tags         = self.aws_client.tags.build(stack_name, caller_ip, creator, request.interceptor)
        compose_yaml = self.compose_template.render()
        user_data    = self.user_data_builder.render(stack_name         = stack_name               ,
                                                       region             = region                 ,
                                                       compose_yaml       = compose_yaml           ,
                                                       interceptor_source = source                 ,
                                                       operator_password  = password               ,
                                                       interceptor_kind   = interceptor_kind_str   ,
                                                       registry           = request.registry       ,
                                                       api_key_ssm_path   = request.api_key_ssm_path)
        instance_id  = self.aws_client.launch.run_instance(region, ami_id, sg_id, user_data, tags,
                                                              instance_type         = inst_type  ,
                                                              instance_profile_name = PROFILE_NAME)
        event_bus.emit('vnc:stack.created', Schema__Stack__Event(
            type_id     = Enum__Stack__Type.VNC,
            stack_name  = stack_name           ,
            region      = region               ,
            instance_id = str(instance_id)     ))
        return Schema__Vnc__Stack__Create__Response(
            stack_name        = stack_name                                ,
            aws_name_tag      = VNC_NAMING.aws_name_for_stack(stack_name) ,
            instance_id       = instance_id                               ,
            region            = region                                    ,
            ami_id            = ami_id                                    ,
            instance_type     = inst_type                                 ,
            security_group_id = sg_id                                     ,
            caller_ip         = caller_ip                                 ,
            operator_password = password                                  ,
            interceptor_kind  = request.interceptor.kind                  ,
            interceptor_name  = label                                     ,
            state             = Enum__Vnc__Stack__State.PENDING           )

    def create_node(self, base_request, api_key_ssm_path: Safe_Str__SSM__Path = Safe_Str__SSM__Path()) -> 'Schema__Node__Info':
        from sg_compute.core.node.schemas.Schema__Node__Info import Schema__Node__Info
        from sg_compute.primitives.enums.Enum__Node__State   import Enum__Node__State
        vnc_req = Schema__Vnc__Stack__Create__Request(
            stack_name       = base_request.node_name     ,
            region           = base_request.region        ,
            instance_type    = base_request.instance_type ,
            from_ami         = base_request.ami_id        ,
            caller_ip        = base_request.caller_ip     ,
            max_hours        = base_request.max_hours     ,
            api_key_ssm_path = api_key_ssm_path           ,
        )
        resp = self.create_stack(vnc_req)
        return Schema__Node__Info(
            node_id              = str(resp.stack_name)      ,
            spec_id              = 'vnc'                     ,
            region               = base_request.region       ,
            state                = Enum__Node__State.BOOTING ,
            public_ip            = str(resp.public_ip)       ,
            instance_id          = str(resp.instance_id)     ,
            instance_type        = str(resp.instance_type)   ,
            host_api_key_ssm_path= api_key_ssm_path          ,
        )

    def list_stacks(self, region: Safe_Str__AWS__Region) -> Schema__Vnc__Stack__List:
        region = region or DEFAULT_REGION
        raw    = self.aws_client.instance.list_stacks(region)
        stacks = List__Schema__Vnc__Stack__Info()
        for details in raw.values():
            stacks.append(self.mapper.to_info(details, region))
        return Schema__Vnc__Stack__List(region=region, stacks=stacks)

    def get_stack_info(self, region: Safe_Str__AWS__Region, stack_name: Safe_Str__Stack__Name) -> Optional[Schema__Vnc__Stack__Info]:
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        return self.mapper.to_info(details, region) if details else None

    def delete_stack(self, region: Safe_Str__AWS__Region, stack_name: Safe_Str__Stack__Name) -> Schema__Vnc__Stack__Delete__Response:
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        if not details:
            return Schema__Vnc__Stack__Delete__Response()
        instance_id = details.get('InstanceId', '')
        ok          = self.aws_client.instance.terminate_instance(region, instance_id)
        terminated  = List__Instance__Id()
        if ok and instance_id:
            terminated.append(instance_id)
            event_bus.emit('vnc:stack.deleted', Schema__Stack__Event(
                type_id     = Enum__Stack__Type.VNC,
                stack_name  = stack_name           ,
                region      = region               ,
                instance_id = instance_id          ))
        return Schema__Vnc__Stack__Delete__Response(target=instance_id, stack_name=stack_name,
                                                     terminated_instance_ids=terminated)

    def health(self, region: Safe_Str__AWS__Region, stack_name: Safe_Str__Stack__Name,
               username: Safe_Str__Message = Safe_Str__Message(), password: Safe_Str__Message = Safe_Str__Message()) -> Schema__Vnc__Health:
        info = self.get_stack_info(region, stack_name)
        if info is None or not str(info.public_ip):
            return Schema__Vnc__Health(stack_name=stack_name, error='instance not running or no public IP')
        viewer_url  = str(info.viewer_url )
        mitmweb_url = str(info.mitmweb_url)
        nginx_ok    = self.probe.nginx_ready  (viewer_url , username, password)
        mitmweb_ok  = self.probe.mitmweb_ready(mitmweb_url, username, password)
        flow_count  = len(self.probe.flows_listing(mitmweb_url, username, password)) if mitmweb_ok else -1
        state       = Enum__Vnc__Stack__State.READY if (nginx_ok and mitmweb_ok) else info.state
        return Schema__Vnc__Health(stack_name = stack_name ,
                                    state      = state      ,
                                    nginx_ok   = nginx_ok   ,
                                    mitmweb_ok = mitmweb_ok ,
                                    flow_count = flow_count )

    def flows(self, region: Safe_Str__AWS__Region, stack_name: Safe_Str__Stack__Name,
              username: Safe_Str__Message = Safe_Str__Message(), password: Safe_Str__Message = Safe_Str__Message()) -> List__Schema__Vnc__Mitm__Flow__Summary:
        info = self.get_stack_info(region, stack_name)
        out  = List__Schema__Vnc__Mitm__Flow__Summary()
        if info is None or not str(info.public_ip):
            return out
        for flow in self.probe.flows_listing(str(info.mitmweb_url), username, password):
            out.append(_flow_summary_from_mitmweb(flow))
        return out
