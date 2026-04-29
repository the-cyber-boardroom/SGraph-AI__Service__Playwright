# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Neko__Service
# Tier-1 pure-logic orchestrator for sp neko (Neko WebRTC browser experiment).
# Mirrors VNC__Service shape. Plugin manifest ships enabled=True for the
# structured experiment (v0.22.19 brief, doc 04).
#
# Operations:
#   create_stack(request)  → Schema__Neko__Stack__Create__Response
#   list_stacks(region)    → Schema__Neko__Stack__List
#   get_stack_info(region, stack_name) → Optional[Schema__Neko__Stack__Info]
#   delete_stack(region, stack_name)   → Schema__Neko__Stack__Delete__Response
# ═══════════════════════════════════════════════════════════════════════════════

import secrets
import time

from typing                                                                         import Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.core.event_bus.Event__Bus                    import event_bus
from sgraph_ai_service_playwright__cli.core.event_bus.schemas.Schema__Stack__Event  import Schema__Stack__Event
from sgraph_ai_service_playwright__cli.neko.collections.List__Schema__Neko__Stack__Info import List__Schema__Neko__Stack__Info
from sgraph_ai_service_playwright__cli.neko.enums.Enum__Neko__Stack__State          import Enum__Neko__Stack__State
from sgraph_ai_service_playwright__cli.neko.schemas.Schema__Neko__Stack__Create__Request  import Schema__Neko__Stack__Create__Request
from sgraph_ai_service_playwright__cli.neko.schemas.Schema__Neko__Stack__Create__Response import Schema__Neko__Stack__Create__Response
from sgraph_ai_service_playwright__cli.neko.schemas.Schema__Neko__Stack__Delete__Response import Schema__Neko__Stack__Delete__Response
from sgraph_ai_service_playwright__cli.neko.schemas.Schema__Neko__Stack__Info       import Schema__Neko__Stack__Info
from sgraph_ai_service_playwright__cli.neko.schemas.Schema__Neko__Stack__List       import Schema__Neko__Stack__List
from sgraph_ai_service_playwright__cli.neko.service.Neko__AWS__Client               import NEKO_NAMING


DEFAULT_REGION        = 'eu-west-2'
DEFAULT_INSTANCE_TYPE = 't3.large'
PROFILE_NAME          = 'playwright-ec2'                                            # IAM instance profile with AmazonSSMManagedInstanceCore
PASSWORD_BYTES        = 16                                                          # secrets.token_urlsafe(16) → ~22 URL-safe chars


class Neko__Service(Type_Safe):
    aws_client        : object = None                                               # Neko__AWS__Client     (lazy via setup())
    mapper            : object = None                                               # Neko__Stack__Mapper   (lazy via setup())
    ip_detector       : object = None                                               # Caller__IP__Detector  (lazy via setup())
    name_gen          : object = None                                               # Random__Stack__Name__Generator (lazy via setup())
    user_data_builder : object = None                                               # Neko__User_Data__Builder (lazy via setup())

    def setup(self) -> 'Neko__Service':
        from sgraph_ai_service_playwright__cli.neko.service.Caller__IP__Detector        import Caller__IP__Detector
        from sgraph_ai_service_playwright__cli.neko.service.Neko__AWS__Client           import Neko__AWS__Client
        from sgraph_ai_service_playwright__cli.neko.service.Neko__Stack__Mapper         import Neko__Stack__Mapper
        from sgraph_ai_service_playwright__cli.neko.service.Neko__User_Data__Builder    import Neko__User_Data__Builder
        from sgraph_ai_service_playwright__cli.neko.service.Random__Stack__Name__Generator import Random__Stack__Name__Generator
        self.aws_client        = Neko__AWS__Client()  .setup()
        self.mapper            = Neko__Stack__Mapper()
        self.ip_detector       = Caller__IP__Detector()
        self.name_gen          = Random__Stack__Name__Generator()
        self.user_data_builder = Neko__User_Data__Builder()
        return self

    def create_stack(self, request: Schema__Neko__Stack__Create__Request, creator: str = '') -> Schema__Neko__Stack__Create__Response:
        t0             = time.monotonic()
        stack_name     = str(request.stack_name)    or f'neko-{self.name_gen.generate()}'
        region         = str(request.region)        or DEFAULT_REGION
        caller_ip      = str(request.caller_ip)     or str(self.ip_detector.detect())
        ami_id         = str(request.from_ami)      or self.aws_client.ami.latest_al2023_ami_id(region)
        itype          = str(request.instance_type) or DEFAULT_INSTANCE_TYPE
        admin_password = str(request.admin_password)  or secrets.token_urlsafe(PASSWORD_BYTES)
        member_password= str(request.member_password) or secrets.token_urlsafe(PASSWORD_BYTES)

        sg_id     = self.aws_client.sg.ensure_security_group(region, stack_name, caller_ip)
        tags      = self.aws_client.tags.build(stack_name, caller_ip, creator)
        user_data = self.user_data_builder.render(stack_name     = stack_name     ,
                                                    region         = region         ,
                                                    admin_password = admin_password ,
                                                    member_password= member_password)
        iid       = self.aws_client.launch.run_instance(region, ami_id, sg_id, user_data, tags,
                                                        instance_type         = itype       ,
                                                        instance_profile_name = PROFILE_NAME)
        event_bus.emit('neko:stack.created', Schema__Stack__Event(
            type_id     = Enum__Stack__Type.NEKO,
            stack_name  = stack_name            ,
            region      = region                ,
            instance_id = str(iid)              ))
        return Schema__Neko__Stack__Create__Response(
            stack_name        = stack_name                                    ,
            aws_name_tag      = NEKO_NAMING.aws_name_for_stack(stack_name)   ,
            instance_id       = iid                                           ,
            region            = region                                        ,
            ami_id            = ami_id                                        ,
            instance_type     = itype                                         ,
            security_group_id = sg_id                                         ,
            caller_ip         = caller_ip                                     ,
            admin_password    = admin_password                                ,
            member_password   = member_password                               ,
            state             = Enum__Neko__Stack__State.PENDING              ,
            elapsed_ms        = int((time.monotonic() - t0) * 1000)          )

    def list_stacks(self, region: str = '') -> Schema__Neko__Stack__List:
        region = region or DEFAULT_REGION
        raw    = self.aws_client.instance.list_stacks(region)
        stacks = List__Schema__Neko__Stack__Info()
        for details in raw.values():
            stacks.append(self.mapper.to_info(details, region))
        return Schema__Neko__Stack__List(region=region, stacks=stacks, total=len(stacks))

    def get_stack_info(self, region: str, stack_name: str) -> Optional[Schema__Neko__Stack__Info]:
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        return self.mapper.to_info(details, region) if details else None

    def delete_stack(self, region: str, stack_name: str) -> Schema__Neko__Stack__Delete__Response:
        t0      = time.monotonic()
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        if not details:
            return Schema__Neko__Stack__Delete__Response(
                stack_name = stack_name                        ,
                message    = 'stack not found'                 ,
                elapsed_ms = int((time.monotonic() - t0) * 1000))
        iid = details.get('InstanceId', '')
        ok  = self.aws_client.instance.terminate_instance(region, iid)
        if ok:
            event_bus.emit('neko:stack.deleted', Schema__Stack__Event(
                type_id     = Enum__Stack__Type.NEKO,
                stack_name  = stack_name            ,
                region      = region                ,
                instance_id = iid                   ))
        return Schema__Neko__Stack__Delete__Response(
            stack_name = stack_name                                        ,
            target     = iid                                               ,
            deleted    = ok                                                ,
            message    = f'terminated {iid}' if ok else 'terminate failed',
            elapsed_ms = int((time.monotonic() - t0) * 1000)              )
