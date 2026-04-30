# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Firefox__Service
# Tier-1 pure-logic orchestrator for sp firefox (jlesage/firefox experiment).
# Mirrors Neko__Service shape.
#
# Operations:
#   create_stack(request)  → Schema__Firefox__Stack__Create__Response
#   list_stacks(region)    → Schema__Firefox__Stack__List
#   get_stack_info(region, stack_name) → Optional[Schema__Firefox__Stack__Info]
#   delete_stack(region, stack_name)   → Schema__Firefox__Stack__Delete__Response
#   health(region, stack_name, ...)    → Schema__Firefox__Health__Response
# ═══════════════════════════════════════════════════════════════════════════════

import secrets
import time

from typing                                                                         import Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.core.event_bus.Event__Bus                    import event_bus
from sgraph_ai_service_playwright__cli.core.event_bus.schemas.Schema__Stack__Event  import Schema__Stack__Event
from sgraph_ai_service_playwright__cli.firefox.collections.List__Schema__Firefox__Stack__Info import List__Schema__Firefox__Stack__Info
from sgraph_ai_service_playwright__cli.firefox.enums.Enum__Firefox__Stack__State    import Enum__Firefox__Stack__State
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Health__Response      import Schema__Firefox__Health__Response
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Stack__Create__Request  import Schema__Firefox__Stack__Create__Request
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Stack__Create__Response import Schema__Firefox__Stack__Create__Response
from sgraph_ai_service_playwright__cli.firefox.collections.List__Schema__Firefox__AMI__Info        import List__Schema__Firefox__AMI__Info
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__AMI__Create__Response      import Schema__Firefox__AMI__Create__Response
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__AMI__Info                  import Schema__Firefox__AMI__Info
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Set__Interceptor__Response import Schema__Firefox__Set__Interceptor__Response
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Stack__Delete__Response import Schema__Firefox__Stack__Delete__Response
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Stack__Info import Schema__Firefox__Stack__Info
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Stack__List import Schema__Firefox__Stack__List
from sgraph_ai_service_playwright__cli.firefox.service.Firefox__AWS__Client         import FIREFOX_NAMING
from sgraph_ai_service_playwright__cli.firefox.service.Firefox__Interceptor__Resolver import Firefox__Interceptor__Resolver


DEFAULT_REGION        = 'eu-west-2'
DEFAULT_INSTANCE_TYPE = 't3.medium'
PROFILE_NAME          = 'playwright-ec2'                                            # IAM instance profile with AmazonSSMManagedInstanceCore
PASSWORD_BYTES        = 16                                                          # secrets.token_urlsafe(16) → ~22 URL-safe chars


class Firefox__Service(Type_Safe):
    aws_client        : object = None                                               # Firefox__AWS__Client    (lazy via setup())
    mapper            : object = None                                               # Firefox__Stack__Mapper  (lazy via setup())
    ip_detector       : object = None                                               # Caller__IP__Detector    (lazy via setup())
    name_gen          : object = None                                               # Random__Stack__Name__Generator (lazy via setup())
    user_data_builder : object = None                                               # Firefox__User_Data__Builder (lazy via setup())
    interceptor_resolver: object = None                                             # Firefox__Interceptor__Resolver (lazy via setup())

    def setup(self) -> 'Firefox__Service':
        from sgraph_ai_service_playwright__cli.firefox.service.Caller__IP__Detector         import Caller__IP__Detector
        from sgraph_ai_service_playwright__cli.firefox.service.Firefox__AWS__Client         import Firefox__AWS__Client
        from sgraph_ai_service_playwright__cli.firefox.service.Firefox__Stack__Mapper       import Firefox__Stack__Mapper
        from sgraph_ai_service_playwright__cli.firefox.service.Firefox__User_Data__Builder  import Firefox__User_Data__Builder
        from sgraph_ai_service_playwright__cli.firefox.service.Random__Stack__Name__Generator import Random__Stack__Name__Generator
        self.aws_client          = Firefox__AWS__Client()  .setup()
        self.mapper              = Firefox__Stack__Mapper()
        self.ip_detector         = Caller__IP__Detector()
        self.name_gen            = Random__Stack__Name__Generator()
        self.user_data_builder   = Firefox__User_Data__Builder()
        self.interceptor_resolver= Firefox__Interceptor__Resolver()
        return self

    def create_stack(self, request: Schema__Firefox__Stack__Create__Request, creator: str = '') -> Schema__Firefox__Stack__Create__Response:
        t0         = time.monotonic()
        stack_name = str(request.stack_name)    or f'firefox-{self.name_gen.generate()}'
        region     = str(request.region)        or DEFAULT_REGION
        caller_ip  = str(request.caller_ip)     or str(self.ip_detector.detect())
        ami_id     = str(request.from_ami)      or self.aws_client.ami.latest_al2023_ami_id(region)
        itype      = str(request.instance_type) or DEFAULT_INSTANCE_TYPE
        password   = str(request.password)      or secrets.token_urlsafe(PASSWORD_BYTES)

        interceptor_source, interceptor_label = self.interceptor_resolver.resolve(request.interceptor)
        interceptor_kind = str(request.interceptor.kind) if request.interceptor else 'none'

        sg_id     = self.aws_client.sg.ensure_security_group(region, stack_name, caller_ip)
        tags      = self.aws_client.tags.build(stack_name, caller_ip, creator)
        user_data = self.user_data_builder.render(stack_name         = stack_name        ,
                                                   region             = region            ,
                                                   password           = password          ,
                                                   interceptor_source = interceptor_source,
                                                   interceptor_kind   = interceptor_kind  )
        iid       = self.aws_client.launch.run_instance(region, ami_id, sg_id, user_data, tags,
                                                        instance_type         = itype       ,
                                                        instance_profile_name = PROFILE_NAME)
        event_bus.emit('firefox:stack.created', Schema__Stack__Event(
            type_id     = Enum__Stack__Type.FIREFOX,
            stack_name  = stack_name               ,
            region      = region                   ,
            instance_id = str(iid)                 ))
        return Schema__Firefox__Stack__Create__Response(
            stack_name        = stack_name                                       ,
            aws_name_tag      = FIREFOX_NAMING.aws_name_for_stack(stack_name)   ,
            instance_id       = iid                                              ,
            region            = region                                           ,
            ami_id            = ami_id                                           ,
            instance_type     = itype                                            ,
            security_group_id = sg_id                                            ,
            caller_ip         = caller_ip                                        ,
            password          = password                                         ,
            interceptor_label = interceptor_label or 'none'                      ,
            mitmweb_url       = ''                                               ,   # unknown until instance boots
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
               timeout_sec: int = 300, poll_sec: int = 10) -> Schema__Firefox__Health__Response:
        t0       = time.monotonic()
        deadline = t0 + timeout_sec
        while True:
            info = self.get_stack_info(region, stack_name)
            if info is None:
                return Schema__Firefox__Health__Response(
                    stack_name = stack_name                           ,
                    state      = Enum__Firefox__Stack__State.UNKNOWN  ,
                    message    = 'stack not found'                    ,
                    elapsed_ms = int((time.monotonic() - t0) * 1000) )
            state = info.state
            if state in (Enum__Firefox__Stack__State.RUNNING, Enum__Firefox__Stack__State.READY):
                return Schema__Firefox__Health__Response(
                    stack_name = stack_name                           ,
                    state      = state                                ,
                    healthy    = True                                 ,
                    message    = 'instance running'                   ,
                    elapsed_ms = int((time.monotonic() - t0) * 1000) )
            if state in (Enum__Firefox__Stack__State.TERMINATED, Enum__Firefox__Stack__State.TERMINATING):
                return Schema__Firefox__Health__Response(
                    stack_name = stack_name                           ,
                    state      = state                                ,
                    message    = 'instance terminated'                ,
                    elapsed_ms = int((time.monotonic() - t0) * 1000) )
            if time.monotonic() >= deadline:
                return Schema__Firefox__Health__Response(
                    stack_name = stack_name                           ,
                    state      = state                                ,
                    message    = f'timed out after {timeout_sec}s'   ,
                    elapsed_ms = int((time.monotonic() - t0) * 1000) )
            time.sleep(poll_sec)

    def create_ami(self, region: str, stack_name: str,
                   ami_name: str = '', no_reboot: bool = True) -> Schema__Firefox__AMI__Create__Response:
        import time as _time
        t0      = _time.monotonic()
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        if not details:
            raise ValueError(f'no Firefox stack found: {stack_name!r}')
        iid      = details.get('InstanceId', '')
        name     = ami_name or f'firefox-{stack_name}-{int(_time.time())}'
        ami_id   = self.aws_client.ami.create_image(region, iid, stack_name, name, no_reboot)
        return Schema__Firefox__AMI__Create__Response(
            ami_id      = ami_id                                        ,
            ami_name    = name                                          ,
            stack_name  = stack_name                                    ,
            instance_id = iid                                           ,
            region      = region                                        ,
            state       = 'pending'                                     ,
            elapsed_ms  = int((_time.monotonic() - t0) * 1000)         )

    def wait_for_ami(self, region: str, ami_id: str,
                     timeout_sec: int = 1200, poll_sec: int = 15,
                     on_progress=None) -> str:                                      # Returns final state string
        import time as _time
        t0       = _time.monotonic()
        deadline = t0 + timeout_sec
        attempt  = 0
        while _time.monotonic() < deadline:
            state   = self.aws_client.ami.describe_ami_state(region, ami_id)
            attempt += 1
            if on_progress:
                on_progress({'state': state, 'attempt': attempt,
                             'elapsed_ms': int((_time.monotonic() - t0) * 1000)})
            if state and state != 'pending':
                return state
            _time.sleep(poll_sec)
        return self.aws_client.ami.describe_ami_state(region, ami_id) or 'unknown'

    def list_amis(self, region: str = '') -> List__Schema__Firefox__AMI__Info:
        region = region or DEFAULT_REGION
        raw    = self.aws_client.ami.list_firefox_amis(region)
        result = List__Schema__Firefox__AMI__Info()
        for item in raw:
            result.append(Schema__Firefox__AMI__Info(
                ami_id        = item.get('ami_id'       , ''),
                name          = item.get('name'         , ''),
                creation_date = item.get('creation_date', ''),
                state         = item.get('state'        , ''),
                source_stack  = item.get('source_stack' , ''),
                source_id     = item.get('source_id'    , '')))
        return result

    def delete_ami(self, region: str, ami_id: str) -> dict:                        # {'deleted': bool, 'snapshots': int}
        ok, snaps = self.aws_client.ami.deregister_ami(region, ami_id)
        return {'deleted': ok, 'snapshots': snaps}

    def create_from_ami(self, request: Schema__Firefox__Stack__Create__Request,
                        creator: str = '') -> Schema__Firefox__Stack__Create__Response:
        t0         = time.monotonic()
        stack_name = str(request.stack_name)    or f'firefox-{self.name_gen.generate()}'
        region     = str(request.region)        or DEFAULT_REGION
        caller_ip  = str(request.caller_ip)     or str(self.ip_detector.detect())
        ami_id     = str(request.from_ami)
        itype      = str(request.instance_type) or DEFAULT_INSTANCE_TYPE
        password   = str(request.password)      or secrets.token_urlsafe(PASSWORD_BYTES)

        interceptor_source, interceptor_label = self.interceptor_resolver.resolve(request.interceptor)
        interceptor_kind = str(request.interceptor.kind) if request.interceptor else 'none'

        sg_id     = self.aws_client.sg.ensure_security_group(region, stack_name, caller_ip)
        tags      = self.aws_client.tags.build(stack_name, caller_ip, creator)
        user_data = self.user_data_builder.render_fast(
            stack_name         = stack_name        ,
            region             = region            ,
            password           = password          ,
            interceptor_source = interceptor_source,
            interceptor_kind   = interceptor_kind  )
        iid       = self.aws_client.launch.run_instance(region, ami_id, sg_id, user_data, tags,
                                                        instance_type         = itype       ,
                                                        instance_profile_name = PROFILE_NAME)
        event_bus.emit('firefox:stack.created', Schema__Stack__Event(
            type_id     = Enum__Stack__Type.FIREFOX,
            stack_name  = stack_name               ,
            region      = region                   ,
            instance_id = str(iid)                 ))
        return Schema__Firefox__Stack__Create__Response(
            stack_name        = stack_name                                       ,
            aws_name_tag      = FIREFOX_NAMING.aws_name_for_stack(stack_name)   ,
            instance_id       = iid                                              ,
            region            = region                                           ,
            ami_id            = ami_id                                           ,
            instance_type     = itype                                            ,
            security_group_id = sg_id                                            ,
            caller_ip         = caller_ip                                        ,
            password          = password                                         ,
            interceptor_label = interceptor_label or 'none'                      ,
            mitmweb_url       = ''                                               ,
            state             = Enum__Firefox__Stack__State.PENDING              ,
            elapsed_ms        = int((time.monotonic() - t0) * 1000)             )

    def set_interceptor(self, region: str, stack_name: str,
                        choice: 'Schema__Firefox__Interceptor__Choice' = None) -> Schema__Firefox__Set__Interceptor__Response:
        from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Interceptor__Choice import Schema__Firefox__Interceptor__Choice
        t0      = time.monotonic()
        choice  = choice or Schema__Firefox__Interceptor__Choice()
        source, label = self.interceptor_resolver.resolve(choice)
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        if not details:
            return Schema__Firefox__Set__Interceptor__Response(
                stack_name        = stack_name                          ,
                interceptor_label = label or 'none'                    ,
                message           = 'stack not found'                  ,
                elapsed_ms        = int((time.monotonic() - t0) * 1000))
        iid             = details.get('InstanceId', '')
        ok, message     = self.aws_client.ssm.push_interceptor(region, iid, source)
        return Schema__Firefox__Set__Interceptor__Response(
            stack_name        = stack_name                          ,
            instance_id       = iid                                ,
            interceptor_label = label or 'none'                    ,
            success           = ok                                 ,
            message           = message                            ,
            elapsed_ms        = int((time.monotonic() - t0) * 1000))

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
        if ok:
            event_bus.emit('firefox:stack.deleted', Schema__Stack__Event(
                type_id     = Enum__Stack__Type.FIREFOX,
                stack_name  = stack_name               ,
                region      = region                   ,
                instance_id = iid                      ))
        return Schema__Firefox__Stack__Delete__Response(
            stack_name = stack_name                                        ,
            target     = iid                                               ,
            deleted    = ok                                                ,
            message    = f'terminated {iid}' if ok else 'terminate failed',
            elapsed_ms = int((time.monotonic() - t0) * 1000)              )
