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
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Stack__Delete__Response import Schema__Firefox__Stack__Delete__Response
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Stack__Info import Schema__Firefox__Stack__Info
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Stack__List import Schema__Firefox__Stack__List
from sgraph_ai_service_playwright__cli.firefox.service.Firefox__AWS__Client         import FIREFOX_NAMING


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

    def setup(self) -> 'Firefox__Service':
        from sgraph_ai_service_playwright__cli.firefox.service.Caller__IP__Detector         import Caller__IP__Detector
        from sgraph_ai_service_playwright__cli.firefox.service.Firefox__AWS__Client         import Firefox__AWS__Client
        from sgraph_ai_service_playwright__cli.firefox.service.Firefox__Stack__Mapper       import Firefox__Stack__Mapper
        from sgraph_ai_service_playwright__cli.firefox.service.Firefox__User_Data__Builder  import Firefox__User_Data__Builder
        from sgraph_ai_service_playwright__cli.firefox.service.Random__Stack__Name__Generator import Random__Stack__Name__Generator
        self.aws_client        = Firefox__AWS__Client()  .setup()
        self.mapper            = Firefox__Stack__Mapper()
        self.ip_detector       = Caller__IP__Detector()
        self.name_gen          = Random__Stack__Name__Generator()
        self.user_data_builder = Firefox__User_Data__Builder()
        return self

    def create_stack(self, request: Schema__Firefox__Stack__Create__Request, creator: str = '') -> Schema__Firefox__Stack__Create__Response:
        t0         = time.monotonic()
        stack_name = str(request.stack_name)    or f'firefox-{self.name_gen.generate()}'
        region     = str(request.region)        or DEFAULT_REGION
        caller_ip  = str(request.caller_ip)     or str(self.ip_detector.detect())
        ami_id     = str(request.from_ami)      or self.aws_client.ami.latest_al2023_ami_id(region)
        itype      = str(request.instance_type) or DEFAULT_INSTANCE_TYPE
        password   = str(request.password)      or secrets.token_urlsafe(PASSWORD_BYTES)

        sg_id     = self.aws_client.sg.ensure_security_group(region, stack_name, caller_ip)
        tags      = self.aws_client.tags.build(stack_name, caller_ip, creator)
        user_data = self.user_data_builder.render(stack_name = stack_name                    ,
                                                   region     = region                      ,
                                                   password   = password                    ,
                                                   proxy_host = str(request.proxy_host) or '',
                                                   proxy_port = request.proxy_port or 0     ,
                                                   proxy_user = str(request.proxy_user) or '',
                                                   proxy_pass = str(request.proxy_pass) or '')
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
            proxy_host        = str(request.proxy_host) or ''                   ,
            proxy_port        = request.proxy_port or 0                          ,
            proxy_user        = str(request.proxy_user) or ''                   ,
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
