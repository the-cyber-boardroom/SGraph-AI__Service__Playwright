# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Playwright__Stack__Service
# Tier-1 pure-logic orchestrator for `sp playwright`. Composes the per-concern
# EC2 helpers and exposes the operations consumed by both the typer CLI
# (Tier 2A) and the FastAPI routes (Tier 2B).
#
# EC2 model: each stack is one EC2 instance running 2-3 containers via
# docker-compose (host-control + sg-playwright + optional mitmproxy).
# CRUD is EC2-by-tag — no host-plane RPC.
#
# Operations:
#   - create_stack(request, creator='')
#   - list_stacks(region)
#   - get_stack_info(region, stack_name)
#   - delete_stack(region, stack_name)
#   - health(region, stack_name)
# ═══════════════════════════════════════════════════════════════════════════════

import secrets

from typing                                                                      import Optional

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type           import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.core.event_bus.Event__Bus                  import event_bus
from sgraph_ai_service_playwright__cli.core.event_bus.schemas.Schema__Stack__Event import Schema__Stack__Event
from sgraph_ai_service_playwright__cli.ec2.collections.List__Instance__Id         import List__Instance__Id
from sgraph_ai_service_playwright__cli.playwright.collections.List__Schema__Playwright__Stack__Info import List__Schema__Playwright__Stack__Info
from sgraph_ai_service_playwright__cli.playwright.enums.Enum__Playwright__Stack__State import Enum__Playwright__Stack__State
from sgraph_ai_service_playwright__cli.playwright.schemas.Schema__Playwright__Health  import Schema__Playwright__Health
from sgraph_ai_service_playwright__cli.playwright.schemas.Schema__Playwright__Stack__Create__Request  import Schema__Playwright__Stack__Create__Request
from sgraph_ai_service_playwright__cli.playwright.schemas.Schema__Playwright__Stack__Create__Response import Schema__Playwright__Stack__Create__Response
from sgraph_ai_service_playwright__cli.playwright.schemas.Schema__Playwright__Stack__Delete__Response import Schema__Playwright__Stack__Delete__Response
from sgraph_ai_service_playwright__cli.playwright.schemas.Schema__Playwright__Stack__Info import Schema__Playwright__Stack__Info
from sgraph_ai_service_playwright__cli.playwright.schemas.Schema__Playwright__Stack__List import Schema__Playwright__Stack__List
from sgraph_ai_service_playwright__cli.playwright.service.Playwright__AWS__Client import PLAYWRIGHT_NAMING
from sgraph_ai_service_playwright__cli.playwright.service.Random__Stack__Name__Generator import Random__Stack__Name__Generator


DEFAULT_REGION        = 'eu-west-2'
DEFAULT_INSTANCE_TYPE = 't3.medium'                                              # 2 vCPU / 4 GB — adequate for playwright + host-control
API_KEY_BYTES         = 24                                                       # secrets.token_urlsafe(24) → 32-char URL-safe base64
PROFILE_NAME          = 'playwright-ec2'                                         # Existing IAM instance profile (AmazonSSMManagedInstanceCore)


class Playwright__Stack__Service(Type_Safe):
    aws_client        : object = None                                            # Playwright__AWS__Client      (lazy via setup())
    probe             : object = None                                            # Playwright__HTTP__Probe      (lazy via setup())
    mapper            : object = None                                            # Playwright__Stack__Mapper    (lazy via setup())
    ip_detector       : object = None                                            # Caller__IP__Detector         (lazy via setup())
    name_gen          : object = None                                            # Random__Stack__Name__Generator (lazy via setup())
    compose_template  : object = None                                            # Playwright__Compose__Template (lazy via setup())
    user_data_builder : object = None                                            # Playwright__User_Data__Builder (lazy via setup())

    def setup(self) -> 'Playwright__Stack__Service':                             # Lazy imports avoid circular module-load
        from sgraph_ai_service_playwright__cli.playwright.service.Caller__IP__Detector         import Caller__IP__Detector
        from sgraph_ai_service_playwright__cli.playwright.service.Playwright__AWS__Client      import Playwright__AWS__Client
        from sgraph_ai_service_playwright__cli.playwright.service.Playwright__Compose__Template import Playwright__Compose__Template
        from sgraph_ai_service_playwright__cli.playwright.service.Playwright__HTTP__Probe      import Playwright__HTTP__Probe
        from sgraph_ai_service_playwright__cli.playwright.service.Playwright__Stack__Mapper    import Playwright__Stack__Mapper
        from sgraph_ai_service_playwright__cli.playwright.service.Playwright__User_Data__Builder import Playwright__User_Data__Builder
        self.aws_client        = Playwright__AWS__Client()     .setup()
        self.probe             = Playwright__HTTP__Probe()
        self.mapper            = Playwright__Stack__Mapper()
        self.ip_detector       = Caller__IP__Detector()
        self.name_gen          = Random__Stack__Name__Generator()
        self.compose_template  = Playwright__Compose__Template()
        self.user_data_builder = Playwright__User_Data__Builder()
        return self

    def create_stack(self, request: Schema__Playwright__Stack__Create__Request,
                           creator: str = '') -> Schema__Playwright__Stack__Create__Response:
        stack_name  = str(request.stack_name) or f'playwright-{self.name_gen.generate()}'
        region      = str(request.region)     or DEFAULT_REGION
        caller_ip   = str(request.caller_ip)  or str(self.ip_detector.detect())
        ami_id      = str(request.from_ami)   or self.aws_client.ami.latest_al2023_ami_id(region)
        inst_type   = str(request.instance_type) or DEFAULT_INSTANCE_TYPE
        api_key     = secrets.token_urlsafe(API_KEY_BYTES)                       # Generated here, returned ONCE, baked into compose env

        sg_id        = self.aws_client.sg.ensure_security_group(region, stack_name, caller_ip,
                                                                 public=bool(request.public_ingress))
        tags         = self.aws_client.tags.build(stack_name, caller_ip, creator,
                                                   with_mitmproxy=bool(request.with_mitmproxy))
        compose_yaml = self.compose_template.render(image_tag      = str(request.image_tag)      ,
                                                     api_key        = api_key                      ,
                                                     with_mitmproxy = bool(request.with_mitmproxy))
        user_data    = self.user_data_builder.render(stack_name       = stack_name                     ,
                                                      region           = region                         ,
                                                      compose_yaml     = compose_yaml                   ,
                                                      api_key          = api_key                        ,
                                                      with_mitmproxy   = bool(request.with_mitmproxy)   ,
                                                      intercept_script = str(request.intercept_script)  ,
                                                      registry         = str(request.registry)          ,
                                                      max_hours        = request.max_hours              )
        instance_id  = self.aws_client.launch.run_instance(region, ami_id, sg_id, user_data, tags,
                                                            instance_type         = inst_type    ,
                                                            instance_profile_name = PROFILE_NAME ,
                                                            max_hours             = request.max_hours)
        event_bus.emit('playwright:stack.created', Schema__Stack__Event(
            type_id     = Enum__Stack__Type.PLAYWRIGHT,
            stack_name  = stack_name                  ,
            region      = region                      ,
            instance_id = str(instance_id)            ))
        return Schema__Playwright__Stack__Create__Response(
            stack_name        = stack_name                                       ,
            aws_name_tag      = PLAYWRIGHT_NAMING.aws_name_for_stack(stack_name) ,
            instance_id       = instance_id                                      ,
            region            = region                                           ,
            ami_id            = ami_id                                           ,
            instance_type     = inst_type                                        ,
            security_group_id = sg_id                                            ,
            caller_ip         = caller_ip                                        ,
            public_ip         = ''                                               ,
            playwright_url    = ''                                               ,
            api_key           = api_key                                          ,
            with_mitmproxy    = bool(request.with_mitmproxy)                     ,
            state             = Enum__Playwright__Stack__State.PENDING           )

    def list_stacks(self, region: str) -> Schema__Playwright__Stack__List:
        region = region or DEFAULT_REGION
        raw    = self.aws_client.instance.list_stacks(region)
        stacks = List__Schema__Playwright__Stack__Info()
        for details in raw.values():
            stacks.append(self.mapper.to_info(details, region))
        return Schema__Playwright__Stack__List(region=region, stacks=stacks)

    def get_stack_info(self, region: str, stack_name: str) -> Optional[Schema__Playwright__Stack__Info]:
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        return self.mapper.to_info(details, region) if details else None

    def delete_stack(self, region: str, stack_name: str) -> Schema__Playwright__Stack__Delete__Response:
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        if not details:
            return Schema__Playwright__Stack__Delete__Response()                 # Empty fields ⇒ route returns 404
        instance_id = details.get('InstanceId', '')
        ok          = self.aws_client.instance.terminate_instance(region, instance_id)
        terminated  = List__Instance__Id()
        if ok and instance_id:
            terminated.append(instance_id)
            event_bus.emit('playwright:stack.deleted', Schema__Stack__Event(
                type_id     = Enum__Stack__Type.PLAYWRIGHT,
                stack_name  = stack_name                  ,
                region      = region                      ,
                instance_id = instance_id                 ))
        return Schema__Playwright__Stack__Delete__Response(target=instance_id, stack_name=stack_name,
                                                           terminated_instance_ids=terminated)

    def health(self, region: str, stack_name: str) -> Schema__Playwright__Health:
        info = self.get_stack_info(region, stack_name)
        if info is None or not str(info.public_ip):
            return Schema__Playwright__Health(stack_name=stack_name,
                                              error='instance not running or no public IP')
        playwright_ok = self.probe.playwright_ready(f'http://{str(info.public_ip)}:8000')
        state = Enum__Playwright__Stack__State.READY if playwright_ok else info.state
        return Schema__Playwright__Health(stack_name    = stack_name    ,
                                          state         = state         ,
                                          playwright_ok = playwright_ok )
