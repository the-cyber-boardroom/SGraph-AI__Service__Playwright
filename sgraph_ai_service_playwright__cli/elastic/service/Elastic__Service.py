# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Elastic__Service
# Pure-logic entry point for `sp elastic` lifecycle commands. Callable from the
# typer CLI (scripts/elastic.py) and, later, from FastAPI routes (out of scope
# for this slice). No boto3, no HTTP, no Typer imports here — every side-effect
# is delegated to an injected client.
#
# Dependencies are constructor-injected so tests swap each for an in-memory
# subclass (see tests/.../service/Elastic__{AWS,HTTP}__Client__In_Memory.py).
# No mocks, no patches — per CLAUDE.md.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import secrets
import time

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.type_safe_core.decorators.type_safe                      import type_safe

from osbot_aws.AWS_Config                                                           import AWS_Config

from sgraph_ai_service_playwright__cli.ec2.collections.List__Instance__Id           import List__Instance__Id
from sgraph_ai_service_playwright__cli.elastic.collections.List__Schema__Elastic__Info  import List__Schema__Elastic__Info
from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Elastic__State           import Enum__Elastic__State
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Password    import Safe_Str__Elastic__Password
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__IP__Address     import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Create__Request  import Schema__Elastic__Create__Request
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Create__Response import Schema__Elastic__Create__Response
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Delete__Response import Schema__Elastic__Delete__Response
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Info        import Schema__Elastic__Info
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__List        import Schema__Elastic__List
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Seed__Request    import Schema__Elastic__Seed__Request
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Seed__Response   import Schema__Elastic__Seed__Response
from sgraph_ai_service_playwright__cli.elastic.service.Caller__IP__Detector         import Caller__IP__Detector
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__AWS__Client         import Elastic__AWS__Client, aws_name_for_stack
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__HTTP__Client        import Elastic__HTTP__Client
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__User__Data__Builder import Elastic__User__Data__Builder
from sgraph_ai_service_playwright__cli.elastic.service.Synthetic__Data__Generator   import Synthetic__Data__Generator
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region    import Safe_Str__AWS__Region


DEFAULT_REGION        = 'eu-west-2'
DEFAULT_INSTANCE_TYPE = 't3.medium'                                                 # 4 GB RAM — comfortable for single-node ES + Kibana + nginx

ADJECTIVES = ['bold','bright','calm','clever','cool','daring','deep','eager',       # Matches scripts.provision_ec2._random_deploy_name vocabulary
              'fast','fierce','fresh','grand','happy','keen','light','lucky',
              'mellow','neat','quick','quiet','sharp','sleek','smart','swift','witty']
SCIENTISTS = ['bohr','curie','darwin','dirac','einstein','euler','faraday',
              'fermi','feynman','galileo','gauss','hopper','hubble','lovelace',
              'maxwell','newton','noether','pascal','planck','turing','tesla',
              'volta','watt','wien','zeno']


class Elastic__Service(Type_Safe):                                                  # Pure-logic orchestrator
    aws_client       : Elastic__AWS__Client
    http_client      : Elastic__HTTP__Client
    ip_detector      : Caller__IP__Detector
    user_data_builder: Elastic__User__Data__Builder
    data_generator   : Synthetic__Data__Generator

    @type_safe
    def create(self, request: Schema__Elastic__Create__Request) -> Schema__Elastic__Create__Response:
        region        = self.resolve_region(request.region)
        stack_name    = request.stack_name if str(request.stack_name) else Safe_Str__Elastic__Stack__Name(self.random_stack_name())
        caller_ip     = request.caller_ip  if str(request.caller_ip)  else self.ip_detector.detect()
        instance_type = str(request.instance_type) or DEFAULT_INSTANCE_TYPE
        ami_id        = str(request.from_ami)      or self.aws_client.resolve_latest_al2023_ami(str(region))
        creator       = self.resolve_creator()
        password      = Safe_Str__Elastic__Password(secrets.token_urlsafe(24))

        sg_id         = self.aws_client.ensure_security_group(region     = str(region)      ,
                                                              stack_name = stack_name        ,
                                                              caller_ip  = caller_ip         ,
                                                              creator    = creator           )
        user_data     = self.user_data_builder.render(stack_name       = stack_name  ,
                                                      elastic_password = password    )
        instance_id   = self.aws_client.launch_instance(region           = str(region)     ,
                                                        stack_name       = stack_name      ,
                                                        ami_id           = ami_id           ,
                                                        instance_type    = instance_type    ,
                                                        security_group_id= sg_id            ,
                                                        user_data        = user_data        ,
                                                        caller_ip        = caller_ip        ,
                                                        creator          = creator          )
        return Schema__Elastic__Create__Response(stack_name        = stack_name                                  ,
                                                 aws_name_tag      = aws_name_for_stack(stack_name)              ,  # "elastic-..." marker, no doubles
                                                 instance_id       = instance_id                                  ,
                                                 region            = region                                       ,
                                                 ami_id            = ami_id                                       ,
                                                 instance_type     = instance_type                                ,
                                                 security_group_id = sg_id                                        ,
                                                 caller_ip         = caller_ip                                    ,
                                                 public_ip         = ''                                           ,  # AWS assigns async — read via info()
                                                 kibana_url        = ''                                           ,  # Filled by info() once public_ip is known
                                                 elastic_password  = password                                     ,
                                                 state             = Enum__Elastic__State.PENDING                 )

    @type_safe
    def list_stacks(self, region: Safe_Str__AWS__Region = None) -> Schema__Elastic__List:
        resolved   = self.resolve_region(region)
        details_by = self.aws_client.list_elastic_instances(str(resolved))
        stacks     = List__Schema__Elastic__Info()
        for instance_id in sorted(details_by.keys()):
            details = details_by[instance_id]
            details['__region'] = str(resolved)                                     # Mapper uses this — see Elastic__AWS__Client.build_instance_info
            stacks.append(self.aws_client.build_instance_info(details))
        return Schema__Elastic__List(region = resolved, stacks = stacks)

    @type_safe
    def get_stack_info(self, stack_name : Safe_Str__Elastic__Stack__Name ,
                             region     : Safe_Str__AWS__Region          = None
                        ) -> Schema__Elastic__Info:
        resolved = self.resolve_region(region)
        details  = self.aws_client.find_by_stack_name(str(resolved), stack_name)
        if details is None:
            return Schema__Elastic__Info(stack_name = stack_name,
                                         region     = resolved   ,
                                         state      = Enum__Elastic__State.UNKNOWN)
        details['__region'] = str(resolved)
        return self.aws_client.build_instance_info(details)

    @type_safe
    def wait_until_ready(self, stack_name : Safe_Str__Elastic__Stack__Name ,
                               region     : Safe_Str__AWS__Region          = None ,
                               timeout    : int                            = 600  ,
                               poll_seconds: int                           = 10
                          ) -> Schema__Elastic__Info:                               # Polls describe + Kibana /api/status; returns the latest Info
        resolved = self.resolve_region(region)
        deadline = time.time() + max(timeout, 1)
        info     = self.get_stack_info(stack_name = stack_name, region = resolved)
        while time.time() < deadline:
            info = self.get_stack_info(stack_name = stack_name, region = resolved)
            if info.state == Enum__Elastic__State.RUNNING and str(info.kibana_url):
                if self.http_client.kibana_ready(str(info.kibana_url)):
                    info.state = Enum__Elastic__State.READY
                    return info
            if info.state in (Enum__Elastic__State.TERMINATING, Enum__Elastic__State.TERMINATED):
                return info
            time.sleep(max(poll_seconds, 1))
        return info

    @type_safe
    def delete_stack(self, stack_name : Safe_Str__Elastic__Stack__Name ,
                           region     : Safe_Str__AWS__Region          = None
                      ) -> Schema__Elastic__Delete__Response:
        resolved = self.resolve_region(region)
        details  = self.aws_client.find_by_stack_name(str(resolved), stack_name)
        if details is None:
            return Schema__Elastic__Delete__Response(stack_name = stack_name)       # All other fields empty — caller maps to "no such stack"

        instance_id = str(details.get('InstanceId', ''))
        sg_list     = details.get('SecurityGroups', [])
        sg_id       = str(sg_list[0].get('GroupId', '')) if sg_list else ''
        terminated  = self.aws_client.terminate_instance(str(resolved), instance_id)
        sg_deleted  = False
        if terminated and sg_id:                                                    # Best-effort SG cleanup; AWS often refuses while instance still terminating
            sg_deleted = self.aws_client.delete_security_group(str(resolved), sg_id)

        ids = List__Instance__Id()
        if terminated and instance_id:
            ids.append(instance_id)
        return Schema__Elastic__Delete__Response(stack_name              = stack_name  ,
                                                 target                  = instance_id ,
                                                 terminated_instance_ids = ids          ,
                                                 security_group_deleted  = sg_deleted   )

    @type_safe
    def seed_stack(self, request: Schema__Elastic__Seed__Request) -> Schema__Elastic__Seed__Response:
        info     = self.get_stack_info(stack_name = request.stack_name)
        if not str(info.kibana_url):                                                # No public IP yet — nothing to seed against
            return Schema__Elastic__Seed__Response(stack_name = request.stack_name,
                                                   index      = request.index    )

        password = str(request.elastic_password) or os.environ.get('SG_ELASTIC_PASSWORD', '')
        self.data_generator.window_days = max(int(request.window_days), 1)
        docs     = self.data_generator.generate(int(request.document_count))

        start_ms = int(time.monotonic() * 1000)
        posted   = 0
        failed   = 0
        batches  = 0
        batch_size = max(int(request.batch_size), 1)
        for offset in range(0, len(docs), batch_size):
            chunk = type(docs)()                                                    # Fresh List__Schema__Log__Document for the slice
            for d in docs[offset:offset + batch_size]:
                chunk.append(d)
            batch_posted, batch_failed = self.http_client.bulk_post(
                base_url = str(info.kibana_url) ,
                username = 'elastic'             ,
                password = password              ,
                index    = str(request.index)    ,
                docs     = chunk                  )
            posted  += batch_posted
            failed  += batch_failed
            batches += 1
        elapsed_ms = max(int(time.monotonic() * 1000) - start_ms, 1)
        rate       = int(posted * 1000 / elapsed_ms)

        return Schema__Elastic__Seed__Response(stack_name       = request.stack_name ,
                                               index            = request.index      ,
                                               documents_posted = posted              ,
                                               documents_failed = failed              ,
                                               batches          = batches             ,
                                               duration_ms      = elapsed_ms          ,
                                               docs_per_second  = rate                )

    def random_stack_name(self) -> str:
        return f'elastic-{secrets.choice(ADJECTIVES)}-{secrets.choice(SCIENTISTS)}'

    def resolve_creator(self) -> str:                                               # Best-effort — same idea as scripts.provision_ec2._get_creator
        return os.environ.get('USER', '') or os.environ.get('LOGNAME', '') or 'sg-elastic'

    def resolve_region(self, region: Safe_Str__AWS__Region = None) -> Safe_Str__AWS__Region:
        if region:                                                                  # Explicit argument wins
            return region
        try:
            from_config = AWS_Config().aws_session_region_name()
            if from_config:
                return Safe_Str__AWS__Region(from_config)
        except Exception:
            pass
        return Safe_Str__AWS__Region(DEFAULT_REGION)
