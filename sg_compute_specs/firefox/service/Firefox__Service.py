# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Firefox: Firefox__Service
# Orchestrator for Firefox stack lifecycle: create / list / info / delete / health.
# ═══════════════════════════════════════════════════════════════════════════════

import secrets
import time
from typing                                                                         import Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.firefox.collections.List__Schema__Firefox__Stack__Info        import List__Schema__Firefox__Stack__Info
from sg_compute_specs.firefox.enums.Enum__Firefox__Stack__State                     import Enum__Firefox__Stack__State
from sg_compute_specs.firefox.schemas.Schema__Firefox__Health__Response             import Schema__Firefox__Health__Response
from sg_compute_specs.firefox.schemas.Schema__Firefox__Stack__Create__Request       import Schema__Firefox__Stack__Create__Request
from sg_compute_specs.firefox.schemas.Schema__Firefox__Stack__Create__Response      import Schema__Firefox__Stack__Create__Response
from sg_compute_specs.firefox.schemas.Schema__Firefox__Stack__Delete__Response      import Schema__Firefox__Stack__Delete__Response
from sg_compute_specs.firefox.schemas.Schema__Firefox__Stack__Info                  import Schema__Firefox__Stack__Info
from sg_compute_specs.firefox.schemas.Schema__Firefox__Stack__List                  import Schema__Firefox__Stack__List
from sg_compute_specs.firefox.service.Firefox__AWS__Client                          import FIREFOX_NAMING


DEFAULT_REGION        = 'eu-west-2'
DEFAULT_INSTANCE_TYPE = 't3.medium'
PASSWORD_BYTES        = 16


class Firefox__Service(Type_Safe):
    aws_client           : object = None
    mapper               : object = None
    user_data_builder    : object = None
    interceptor_resolver : object = None
    probe                : object = None

    def setup(self) -> 'Firefox__Service':
        from sg_compute_specs.firefox.service.Firefox__AWS__Client           import Firefox__AWS__Client
        from sg_compute_specs.firefox.service.Firefox__Stack__Mapper         import Firefox__Stack__Mapper
        from sg_compute_specs.firefox.service.Firefox__User_Data__Builder    import Firefox__User_Data__Builder
        from sg_compute_specs.firefox.service.Firefox__Interceptor__Resolver import Firefox__Interceptor__Resolver
        from sg_compute_specs.firefox.service.Firefox__HTTP__Probe           import Firefox__HTTP__Probe
        self.aws_client           = Firefox__AWS__Client()  .setup()
        self.mapper               = Firefox__Stack__Mapper()
        self.user_data_builder    = Firefox__User_Data__Builder()
        self.interceptor_resolver = Firefox__Interceptor__Resolver()
        self.probe                = Firefox__HTTP__Probe()
        return self

    def create_stack(self, request: Schema__Firefox__Stack__Create__Request,
                           creator: str = '') -> Schema__Firefox__Stack__Create__Response:
        t0         = time.monotonic()
        stack_name = str(request.stack_name)    or f'firefox-stack'
        region     = str(request.region)        or DEFAULT_REGION
        caller_ip  = str(request.caller_ip)     or '0.0.0.0'
        itype      = str(request.instance_type) or DEFAULT_INSTANCE_TYPE
        password   = str(request.password)      or secrets.token_urlsafe(PASSWORD_BYTES)

        interceptor_source, interceptor_label = self.interceptor_resolver.resolve(request.interceptor)
        interceptor_kind = str(request.interceptor.kind) if request.interceptor else 'none'
        cidr             = str(request.allowed_cidr) or f'{caller_ip}/32'
        max_hours        = int(request.max_hours)
        env_source       = str(request.env_source)

        profile   = self.aws_client.iam.ensure(region)
        sg_id     = self.aws_client.sg.ensure_security_group(region, stack_name, cidr)
        tags      = self.aws_client.tags.build(stack_name, caller_ip, creator)
        user_data = self.user_data_builder.render(stack_name         = stack_name        ,
                                                   region             = region            ,
                                                   password           = password          ,
                                                   interceptor_source = interceptor_source,
                                                   interceptor_kind   = interceptor_kind  ,
                                                   env_source         = env_source        ,
                                                   max_hours          = max_hours         )
        iid = self.aws_client.launch.run_instance(region, str(request.from_ami) or '',
                                                   sg_id, user_data, tags,
                                                   instance_type         = itype   ,
                                                   instance_profile_name = profile ,
                                                   max_hours             = max_hours)
        return Schema__Firefox__Stack__Create__Response(
            stack_name        = stack_name                                       ,
            aws_name_tag      = FIREFOX_NAMING.aws_name_for_stack(stack_name)   ,
            instance_id       = iid                                              ,
            region            = region                                           ,
            ami_id            = str(request.from_ami)                            ,
            instance_type     = itype                                            ,
            security_group_id = sg_id                                            ,
            caller_ip         = caller_ip                                        ,
            password          = password                                         ,
            interceptor_label = interceptor_label or 'none'                      ,
            mitmweb_url       = ''                                               ,
            state             = Enum__Firefox__Stack__State.PENDING              ,
            elapsed_ms        = int((time.monotonic() - t0) * 1000)             )

    def list_stacks(self, region: str = '') -> Schema__Firefox__Stack__List:
        region = region or DEFAULT_REGION
        raw    = self.aws_client.instance.list_stacks(region)
        stacks = List__Schema__Firefox__Stack__Info()
        for details in raw.values():
            stacks.append(self.mapper.to_info(details, region))
        return Schema__Firefox__Stack__List(region=region, stacks=stacks, total=len(stacks))

    def get_stack_info(self, region: str, stack_name: str) -> Optional[Schema__Firefox__Stack__Info]:
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        return self.mapper.to_info(details, region) if details else None

    def health(self, region: str, stack_name: str,
               timeout_sec: int = 0) -> Schema__Firefox__Health__Response:
        t0   = time.monotonic()
        info = self.get_stack_info(region, stack_name)
        if info is None:
            return Schema__Firefox__Health__Response(
                stack_name = stack_name                           ,
                state      = Enum__Firefox__Stack__State.UNKNOWN  ,
                message    = 'stack not found'                    ,
                elapsed_ms = int((time.monotonic() - t0) * 1000) )
        state = info.state
        if state in (Enum__Firefox__Stack__State.TERMINATED, Enum__Firefox__Stack__State.TERMINATING):
            return Schema__Firefox__Health__Response(
                stack_name = stack_name                           ,
                state      = state                                ,
                message    = 'instance terminated'                ,
                elapsed_ms = int((time.monotonic() - t0) * 1000) )
        public_ip  = str(info.public_ip)
        firefox_ok = mitmweb_ok = False
        if state in (Enum__Firefox__Stack__State.RUNNING, Enum__Firefox__Stack__State.READY) and public_ip:
            firefox_ok = self.probe.firefox_ready(public_ip)
            mitmweb_ok = self.probe.mitmweb_ready(public_ip)
        healthy = firefox_ok and mitmweb_ok
        return Schema__Firefox__Health__Response(
            stack_name = stack_name                                              ,
            state      = Enum__Firefox__Stack__State.READY if healthy else state ,
            healthy    = healthy                                                  ,
            firefox_ok = firefox_ok                                              ,
            mitmweb_ok = mitmweb_ok                                              ,
            message    = 'firefox + mitmweb reachable' if healthy else f'state={state.value}',
            elapsed_ms = int((time.monotonic() - t0) * 1000)                    )

    def delete_stack(self, region: str, stack_name: str) -> Schema__Firefox__Stack__Delete__Response:
        t0      = time.monotonic()
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        if not details:
            return Schema__Firefox__Stack__Delete__Response(
                stack_name = stack_name                        ,
                message    = 'stack not found'                 ,
                elapsed_ms = int((time.monotonic() - t0) * 1000))
        iid = details.get('InstanceId', '')
        ok  = self.aws_client.instance.terminate_instance(region, iid)
        return Schema__Firefox__Stack__Delete__Response(
            stack_name = stack_name                                        ,
            target     = iid                                               ,
            deleted    = ok                                                ,
            message    = f'terminated {iid}' if ok else 'terminate failed',
            elapsed_ms = int((time.monotonic() - t0) * 1000)              )
