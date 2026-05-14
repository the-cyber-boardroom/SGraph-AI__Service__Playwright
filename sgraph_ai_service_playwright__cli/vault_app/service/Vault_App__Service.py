# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Vault_App__Service
# Tier-1 pure-logic orchestrator for sp vault-app. Composes the per-concern
# helpers and exposes the operations consumed by both the typer CLI (Tier 2A)
# and the FastAPI routes (Tier 2B). No print(), no Console.
#
# Operations:
#   - list_stacks(region)
#   - get_stack_info(region, stack_name)
#   - create_stack(request, creator='')
#   - delete_stack(region, stack_name)
#   - health(region, stack_name)
#   - seed_vault(region, stack_name, keys_csv)
# ═══════════════════════════════════════════════════════════════════════════════

import secrets

from typing                                                                         import Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.core.event_bus.Event__Bus                    import event_bus
from sgraph_ai_service_playwright__cli.core.event_bus.schemas.Schema__Stack__Event  import Schema__Stack__Event
from sgraph_ai_service_playwright__cli.vault_app.collections.List__Schema__Vault_App__Stack__Info import List__Schema__Vault_App__Stack__Info
from sgraph_ai_service_playwright__cli.vault_app.enums.Enum__Vault_App__Stack__State  import Enum__Vault_App__Stack__State
from sgraph_ai_service_playwright__cli.vault_app.schemas.Schema__Vault_App__Health                import Schema__Vault_App__Health
from sgraph_ai_service_playwright__cli.vault_app.schemas.Schema__Vault_App__Stack__Create__Request  import Schema__Vault_App__Stack__Create__Request
from sgraph_ai_service_playwright__cli.vault_app.schemas.Schema__Vault_App__Stack__Create__Response import Schema__Vault_App__Stack__Create__Response
from sgraph_ai_service_playwright__cli.vault_app.schemas.Schema__Vault_App__Stack__Delete__Response import Schema__Vault_App__Stack__Delete__Response
from sgraph_ai_service_playwright__cli.vault_app.schemas.Schema__Vault_App__Stack__Info import Schema__Vault_App__Stack__Info
from sgraph_ai_service_playwright__cli.vault_app.schemas.Schema__Vault_App__Stack__List import Schema__Vault_App__Stack__List
from sgraph_ai_service_playwright__cli.vault_app.service.Vault_App__AWS__Client     import VAULT_APP_NAMING


DEFAULT_REGION        = 'eu-west-2'
DEFAULT_INSTANCE_TYPE = 't3.medium'
PROFILE_NAME          = 'playwright-ec2'                                            # IAM instance profile (has AmazonSSMManagedInstanceCore)
TOKEN_BYTES           = 24                                                          # secrets.token_urlsafe(24) → 32-char URL-safe base64


class Vault_App__Service(Type_Safe):
    aws_client        : object = None                                               # Vault_App__AWS__Client        (lazy via setup())
    probe             : object = None                                               # Vault_App__HTTP__Probe        (lazy via setup())
    mapper            : object = None                                               # Vault_App__Stack__Mapper      (lazy via setup())
    ip_detector       : object = None                                               # Caller__IP__Detector          (lazy via setup())
    name_gen          : object = None                                               # Random__Stack__Name__Generator (lazy via setup())
    compose_template  : object = None                                               # Vault_App__Compose__Template  (lazy via setup())
    user_data_builder : object = None                                               # Vault_App__User_Data__Builder (lazy via setup())

    def setup(self) -> 'Vault_App__Service':
        from sgraph_ai_service_playwright__cli.vault_app.service.Vault_App__AWS__Client         import Vault_App__AWS__Client
        from sgraph_ai_service_playwright__cli.vault_app.service.Vault_App__Compose__Template   import Vault_App__Compose__Template
        from sgraph_ai_service_playwright__cli.vault_app.service.Vault_App__HTTP__Probe         import Vault_App__HTTP__Probe
        from sgraph_ai_service_playwright__cli.vault_app.service.Vault_App__Stack__Mapper       import Vault_App__Stack__Mapper
        from sgraph_ai_service_playwright__cli.vault_app.service.Vault_App__User_Data__Builder  import Vault_App__User_Data__Builder
        from sgraph_ai_service_playwright__cli.vnc.service.Caller__IP__Detector                 import Caller__IP__Detector
        from sgraph_ai_service_playwright__cli.vnc.service.Random__Stack__Name__Generator       import Random__Stack__Name__Generator
        self.aws_client        = Vault_App__AWS__Client()     .setup()
        self.probe             = Vault_App__HTTP__Probe()
        self.mapper            = Vault_App__Stack__Mapper()
        self.ip_detector       = Caller__IP__Detector()
        self.name_gen          = Random__Stack__Name__Generator()
        self.compose_template  = Vault_App__Compose__Template()
        self.user_data_builder = Vault_App__User_Data__Builder()
        return self

    def list_stacks(self, region: str = DEFAULT_REGION) -> Schema__Vault_App__Stack__List:
        instances = self.aws_client.instance_helper.list_by_purpose(TAG_PURPOSE=VAULT_APP_NAMING.purpose,
                                                                     region=region)
        stacks = List__Schema__Vault_App__Stack__Info()
        for inst in instances:
            info = self.mapper.instance_to_info(inst)
            if info:
                stacks.append(info)
        return Schema__Vault_App__Stack__List(region=region, stacks=stacks)

    def get_stack_info(self, region: str, stack_name: str) -> Optional[Schema__Vault_App__Stack__Info]:
        instance = self.aws_client.instance_helper.find_by_stack_name(stack_name, region)
        if not instance:
            return None
        return self.mapper.instance_to_info(instance)

    def create_stack(self, request: Schema__Vault_App__Stack__Create__Request,
                     creator: str = '') -> Schema__Vault_App__Stack__Create__Response:
        region        = str(request.region)        or DEFAULT_REGION
        instance_type = str(request.instance_type) or DEFAULT_INSTANCE_TYPE
        stack_name    = str(request.stack_name)    or self.name_gen.generate(prefix='va')
        access_token  = str(request.access_token)  or secrets.token_urlsafe(TOKEN_BYTES)
        caller_ip     = self.ip_detector.detect()

        ami_id        = (str(request.from_ami)
                         or self.aws_client.instance_helper.latest_al2023_ami(region))

        compose_yaml  = self.compose_template.render(
            access_token    = access_token           ,
            seed_vault_keys = str(request.seed_vault_keys) ,
        )
        user_data     = self.user_data_builder.build(compose_yaml=compose_yaml,
                                                     stack_name  =stack_name  )

        tags          = self.aws_client.tags_builder.build(stack_name=stack_name,
                                                           creator   =creator   )
        sg_id         = self.aws_client.sg_helper.get_or_create(stack_name=stack_name,
                                                                 caller_ip =caller_ip ,
                                                                 region    =region    )
        launch_result = self.aws_client.launch_helper.launch(
            ami_id        = ami_id        ,
            instance_type = instance_type ,
            region        = region        ,
            sg_id         = sg_id         ,
            tags          = tags          ,
            user_data     = user_data     ,
            use_spot      = request.use_spot,
            profile_name  = PROFILE_NAME  ,
        )

        response = Schema__Vault_App__Stack__Create__Response(
            stack_name        = stack_name               ,
            aws_name_tag      = f'vault-app-{stack_name}',
            instance_id       = launch_result.instance_id,
            region            = region                   ,
            ami_id            = ami_id                   ,
            instance_type     = instance_type            ,
            security_group_id = sg_id                    ,
            public_ip         = ''                       ,
            vault_url         = ''                       ,
            access_token      = access_token             ,
            state             = Enum__Vault_App__Stack__State.PENDING ,
        )
        event_bus.emit(Schema__Stack__Event(
            stack_type  = Enum__Stack__Type.VAULT_APP ,
            stack_name  = stack_name                  ,
            event_name  = 'vault_app:stack.created'   ,
            instance_id = launch_result.instance_id   ,
            region      = region                      ,
        ))
        return response

    def delete_stack(self, region: str, stack_name: str) -> Schema__Vault_App__Stack__Delete__Response:
        instance = self.aws_client.instance_helper.find_by_stack_name(stack_name, region)
        if not instance:
            return Schema__Vault_App__Stack__Delete__Response()
        instance_id = instance.get('InstanceId', '')
        self.aws_client.instance_helper.terminate(instance_id, region)
        self.aws_client.sg_helper.delete_for_stack(stack_name, region)
        event_bus.emit(Schema__Stack__Event(
            stack_type  = Enum__Stack__Type.VAULT_APP ,
            stack_name  = stack_name                  ,
            event_name  = 'vault_app:stack.deleted'   ,
            instance_id = instance_id                 ,
            region      = region                      ,
        ))
        ids = List__Schema__Vault_App__Stack__Info()                               # re-use ec2 id list via import below
        from sgraph_ai_service_playwright__cli.ec2.collections.List__Instance__Id  import List__Instance__Id
        terminated = List__Instance__Id()
        terminated.append(instance_id)
        return Schema__Vault_App__Stack__Delete__Response(
            target                  = instance_id ,
            stack_name              = stack_name  ,
            terminated_instance_ids = terminated  ,
        )

    def health(self, region: str, stack_name: str) -> Schema__Vault_App__Health:
        info = self.get_stack_info(region, stack_name)
        if not info:
            return Schema__Vault_App__Health(stack_name=stack_name,
                                             error='stack not found')
        return self.probe.check(info)

    def seed_vault(self, region: str, stack_name: str, keys_csv: str) -> dict:
        from sgraph_ai_service_playwright__cli.vault_app.service.Vault__Seeder      import Vault__Seeder
        info = self.get_stack_info(region, stack_name)
        if not info:
            return {'error': 'stack not found'}
        seeder = Vault__Seeder(
            vault_endpoint   = str(info.vault_url) ,
            vault_token      = ''                  ,                               # operator supplies token out-of-band
            host_plane_url   = f'http://{info.public_ip}:8000',
            host_plane_token = ''                  ,
        )
        return seeder.seed_all(keys_csv)
