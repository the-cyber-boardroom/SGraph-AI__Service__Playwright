# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Ec2__Service
# Pure-logic entry point for EC2 instance operations. Same service is called
# from the typer CLI (future wrapper) and from Routes__Ec2 FastAPI routes.
#
# Current form: thin adapter over scripts.provision_ec2 functions. The
# underlying CLI module stays untouched and keeps carrying the imperative
# provisioning logic. When the full port of provision_ec2.py lands, this
# class's method bodies are the only thing that needs to change.
#
# Side-effect isolation
# ─────────────────────
# scripts.provision_ec2.preflight_check() can call sys.exit(1) on credential
# failure — fatal for a FastAPI route. This service replicates the pure-data
# half of preflight (account/region/registry/image/api-key resolution)
# without touching the print-or-exit helpers, so route handlers can catch
# failures as exceptions rather than process exits.
# ═══════════════════════════════════════════════════════════════════════════════

import secrets

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.type_safe_core.decorators.type_safe                      import type_safe
from osbot_utils.utils.Env                                                          import get_env

from sgraph_ai_service_playwright__cli.ec2.collections.List__Instance__Id              import List__Instance__Id
from sgraph_ai_service_playwright__cli.ec2.enums.Enum__Instance__State                 import Enum__Instance__State
from sgraph_ai_service_playwright__cli.ec2.schemas.Schema__Ec2__Create__Request        import Schema__Ec2__Create__Request
from sgraph_ai_service_playwright__cli.ec2.schemas.Schema__Ec2__Create__Response       import Schema__Ec2__Create__Response
from sgraph_ai_service_playwright__cli.ec2.schemas.Schema__Ec2__Delete__Response       import Schema__Ec2__Delete__Response
from sgraph_ai_service_playwright__cli.ec2.schemas.Schema__Ec2__Instance__Info         import Schema__Ec2__Instance__Info
from sgraph_ai_service_playwright__cli.ec2.schemas.Schema__Ec2__Preflight              import Schema__Ec2__Preflight


DEFAULT_API_KEY_NAME = 'X-API-Key'


class Ec2__Service(Type_Safe):                                                      # EC2 orchestration boundary

    @type_safe
    def create(self, request: Schema__Ec2__Create__Request) -> Schema__Ec2__Create__Response:
        from scripts.provision_ec2                                                  import (
            aws_account_id        ,
            aws_region            ,
            ecr_registry_host     ,
            default_playwright_image_uri,
            default_sidecar_image_uri   ,
            provision             ,
            EC2__INSTANCE_TYPE    )

        api_key_name  = get_env('FAST_API__AUTH__API_KEY__NAME' ) or DEFAULT_API_KEY_NAME
        api_key_value = get_env('FAST_API__AUTH__API_KEY__VALUE')
        api_key_generated = False
        if not api_key_value:
            api_key_value     = secrets.token_urlsafe(32)                           # Mirror preflight_check's random-key path
            api_key_generated = True

        playwright_uri = str(request.playwright_image_uri) or default_playwright_image_uri()
        sidecar_uri    = str(request.sidecar_image_uri   ) or default_sidecar_image_uri   ()
        instance_type  = str(request.instance_type       ) or EC2__INSTANCE_TYPE

        preflight = Schema__Ec2__Preflight(aws_account          = aws_account_id  () or '' ,
                                           aws_region           = aws_region      () or '' ,
                                           registry             = ecr_registry_host()      ,
                                           playwright_image_uri = playwright_uri            ,
                                           sidecar_image_uri    = sidecar_uri               ,
                                           api_key_name         = api_key_name              ,
                                           api_key_generated    = api_key_generated         )

        result = provision(stage                = str(request.stage         ) or 'dev'  ,
                           playwright_image_uri = playwright_uri                         ,
                           sidecar_image_uri    = sidecar_uri                            ,
                           deploy_name          = str(request.deploy_name   )            ,
                           from_ami             = str(request.from_ami      ) or None    ,
                           instance_type        = instance_type                          ,
                           max_hours            = int(request.max_hours     )            ,
                           terminate            = False                                   ,
                           upstream_url         = str(request.upstream_url  )            ,
                           upstream_user        = str(request.upstream_user )            ,
                           upstream_pass        = str(request.upstream_pass )            ,
                           http2                = str(request.http2         )            )

        return Schema__Ec2__Create__Response(instance_id          = result.get('instance_id'         , '') ,
                                             deploy_name          = result.get('deploy_name'         , '') ,
                                             stage                = result.get('stage'               , '') ,
                                             creator              = result.get('creator'             , '') ,
                                             ami_id               = result.get('ami_id'              , '') ,
                                             public_ip            = result.get('public_ip'           , '') or '',
                                             playwright_url       = result.get('playwright_url'      , '') or '',
                                             sidecar_admin_url    = result.get('sidecar_admin_url'   , '') or '',
                                             browser_url          = result.get('browser_url'         , '') or '',
                                             playwright_image_uri = result.get('playwright_image_uri', '') ,
                                             sidecar_image_uri    = result.get('sidecar_image_uri'   , '') ,
                                             api_key_name         = api_key_name                           ,
                                             api_key_value        = result.get('api_key_value'       , '') ,
                                             max_hours            = int(result.get('max_hours', 1))        ,
                                             preflight            = preflight                             )

    @type_safe
    def get_instance_info(self, target: str) -> Schema__Ec2__Instance__Info:
        from scripts.provision_ec2 import (find_instances               ,
                                           _instance_tag                ,
                                           _instance_deploy_name        ,
                                           TAG__STAGE_KEY                ,
                                           TAG__CREATOR_KEY              ,
                                           TAG__API_KEY_NAME_KEY         ,
                                           TAG__API_KEY_VALUE_KEY        ,
                                           EC2__PLAYWRIGHT_PORT          ,
                                           EC2__SIDECAR_ADMIN_PORT       ,
                                           EC2__BROWSER_INTERNAL_PORT    )
        from osbot_aws.aws.ec2.EC2                                   import EC2

        ec2             = EC2()
        instance_id, d  = self.resolve_target(ec2, target, find_instances)
        if instance_id is None:
            return None                                                             # Caller maps to 404

        state_raw = d.get('state', {})
        state_str = state_raw.get('Name', '') if isinstance(state_raw, dict) else str(state_raw)
        ip        = d.get('public_ip', '') or ''

        return Schema__Ec2__Instance__Info(instance_id          = instance_id                              ,
                                           deploy_name          = _instance_deploy_name(d) or ''           ,
                                           stage                = _instance_tag(d, TAG__STAGE_KEY)         ,
                                           creator              = _instance_tag(d, TAG__CREATOR_KEY)       ,
                                           ami_id               = d.get('image_id', '')                    ,
                                           public_ip            = ip                                       ,
                                           playwright_url       = f'http://{ip}:{EC2__PLAYWRIGHT_PORT}'         if ip else '',
                                           sidecar_admin_url    = f'http://{ip}:{EC2__SIDECAR_ADMIN_PORT}'    if ip else '',
                                           browser_url          = f'https://{ip}:{EC2__BROWSER_INTERNAL_PORT}' if ip else '',
                                           api_key_name         = _instance_tag(d, TAG__API_KEY_NAME_KEY )    ,
                                           api_key_value        = _instance_tag(d, TAG__API_KEY_VALUE_KEY)    ,
                                           playwright_image_uri = '(stored in compose file on instance)'      ,
                                           sidecar_image_uri    = '(stored in compose file on instance)'      ,
                                           state                = self.parse_state(state_str)                 )

    @type_safe
    def delete_instance(self, target: str) -> Schema__Ec2__Delete__Response:
        from scripts.provision_ec2 import find_instances, _instance_deploy_name
        from osbot_aws.aws.ec2.EC2 import EC2

        ec2                  = EC2()
        instance_id, details = self.resolve_target(ec2, target, find_instances)
        if instance_id is None:
            return Schema__Ec2__Delete__Response()                                  # All fields empty — caller maps to 404

        deploy_name = _instance_deploy_name(details) or ''
        ec2.instance_terminate(instance_id)

        terminated = List__Instance__Id()
        terminated.append(instance_id)
        return Schema__Ec2__Delete__Response(target                  = instance_id ,
                                             deploy_name             = deploy_name  ,
                                             terminated_instance_ids = terminated   )

    def resolve_target(self, ec2, target, find_instances_fn):                       # target = deploy-name or instance-id; no prompts, no exits
        instances = find_instances_fn(ec2)
        if not instances:
            return None, None
        if target.startswith('i-') and target in instances:
            return target, instances[target]
        from scripts.provision_ec2 import _instance_deploy_name
        for iid, details in instances.items():
            if _instance_deploy_name(details) == target:
                return iid, details
        return None, None

    def parse_state(self, state_str: str) -> Enum__Instance__State:                 # AWS returns the canonical value; fall through to UNKNOWN for anything we don't model
        for member in Enum__Instance__State:
            if member.value == state_str:
                return member
        return Enum__Instance__State.UNKNOWN
