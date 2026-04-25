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
from typing                                                                         import Callable

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.type_safe_core.decorators.type_safe                      import type_safe

from osbot_aws.AWS_Config                                                           import AWS_Config

from sgraph_ai_service_playwright__cli.ec2.collections.List__Instance__Id           import List__Instance__Id
from sgraph_ai_service_playwright__cli.elastic.collections.List__Schema__Elastic__Health__Check import List__Schema__Elastic__Health__Check
from sgraph_ai_service_playwright__cli.elastic.collections.List__Schema__Elastic__Info  import List__Schema__Elastic__Info
from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Elastic__Probe__Status   import Enum__Elastic__Probe__Status
from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Elastic__State           import Enum__Elastic__State
from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Health__Status           import Enum__Health__Status
from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Kibana__Probe__Status    import Enum__Kibana__Probe__Status
from sgraph_ai_service_playwright__cli.elastic.enums.Enum__Saved_Object__Type       import Enum__Saved_Object__Type
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Password    import Safe_Str__Elastic__Password
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__IP__Address     import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Create__Request  import Schema__Elastic__Create__Request
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Create__Response import Schema__Elastic__Create__Response
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Delete__Response import Schema__Elastic__Delete__Response
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Info        import Schema__Elastic__Info
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__List        import Schema__Elastic__List
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Health__Check import Schema__Elastic__Health__Check
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Health__Response import Schema__Elastic__Health__Response
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Seed__Request    import Schema__Elastic__Seed__Request
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Seed__Response   import Schema__Elastic__Seed__Response
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Exec__Result         import Schema__Exec__Result
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Kibana__Export__Result import Schema__Kibana__Export__Result
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Kibana__Find__Response import Schema__Kibana__Find__Response
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Kibana__Import__Result import Schema__Kibana__Import__Result
from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Wait__Tick           import Schema__Wait__Tick
from sgraph_ai_service_playwright__cli.elastic.service.Caller__IP__Detector         import Caller__IP__Detector
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__AWS__Client         import Elastic__AWS__Client, aws_name_for_stack
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__HTTP__Client        import Elastic__HTTP__Client
from sgraph_ai_service_playwright__cli.elastic.service.Elastic__User__Data__Builder import Elastic__User__Data__Builder
from sgraph_ai_service_playwright__cli.elastic.service.Kibana__Saved_Objects__Client import Kibana__Saved_Objects__Client
from sgraph_ai_service_playwright__cli.elastic.service.Synthetic__Data__Generator   import Synthetic__Data__Generator
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region    import Safe_Str__AWS__Region


PROBE_MESSAGES = {                                                                  # Human-friendly text the CLI renders per tick
    Enum__Kibana__Probe__Status.UNREACHABLE  : 'nothing answering on :443 yet (instance or nginx still starting).',
    Enum__Kibana__Probe__Status.UPSTREAM_DOWN: 'nginx is up but Kibana container is still booting (502/503).',
    Enum__Kibana__Probe__Status.BOOTING      : 'Kibana answered but not 200 yet.',
    Enum__Kibana__Probe__Status.READY        : 'Kibana is ready.',
    Enum__Kibana__Probe__Status.UNKNOWN      : 'Kibana probe returned an unexpected status.',
}


DEFAULT_REGION        = 'eu-west-2'
DEFAULT_INSTANCE_TYPE = 'm6i.xlarge'                                                # 4 vCPU / 16 GB — matches sp create. t3.medium (4 GB) was tight for ES+Kibana+nginx; Kibana would stall under memory pressure during boot.

ADJECTIVES = ['bold','bright','calm','clever','cool','daring','deep','eager',       # Matches scripts.provision_ec2._random_deploy_name vocabulary
              'fast','fierce','fresh','grand','happy','keen','light','lucky',
              'mellow','neat','quick','quiet','sharp','sleek','smart','swift','witty']
SCIENTISTS = ['bohr','curie','darwin','dirac','einstein','euler','faraday',
              'fermi','feynman','galileo','gauss','hopper','hubble','lovelace',
              'maxwell','newton','noether','pascal','planck','turing','tesla',
              'volta','watt','wien','zeno']


class Elastic__Service(Type_Safe):                                                  # Pure-logic orchestrator
    aws_client            : Elastic__AWS__Client
    http_client           : Elastic__HTTP__Client
    saved_objects_client  : Kibana__Saved_Objects__Client
    ip_detector           : Caller__IP__Detector
    user_data_builder     : Elastic__User__Data__Builder
    data_generator        : Synthetic__Data__Generator

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
        profile_name  = self.aws_client.ensure_instance_profile(str(region))                  # IAM role + profile with AmazonSSMManagedInstanceCore — required for `sp elastic connect/exec`
        max_hours     = max(int(request.max_hours), 0)                                        # Negative collapses to 0 (= no auto-terminate)
        user_data     = self.user_data_builder.render(stack_name       = stack_name  ,
                                                      elastic_password = password    ,
                                                      max_hours        = max_hours   )
        instance_id   = self.aws_client.launch_instance(region                = str(region)    ,
                                                        stack_name            = stack_name     ,
                                                        ami_id                = ami_id          ,
                                                        instance_type         = instance_type   ,
                                                        security_group_id     = sg_id           ,
                                                        user_data             = user_data       ,
                                                        caller_ip             = caller_ip       ,
                                                        instance_profile_name = profile_name    ,
                                                        creator               = creator         ,
                                                        max_hours             = max_hours       )
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

    def wait_until_ready(self, stack_name      : Safe_Str__Elastic__Stack__Name      ,
                               region          : Safe_Str__AWS__Region    = None     ,
                               timeout         : int                      = 600      ,
                               poll_seconds    : int                      = 10       ,
                               elastic_password: str                      = ''       ,  # Optional — when supplied, ES probe runs authenticated and can distinguish AUTH_REQUIRED from UNREACHABLE
                               on_progress     : Callable                 = None     ,  # Invoked with Schema__Wait__Tick each poll; CLI drives the Rich spinner
                               sleep_fn        : Callable                 = time.sleep   # Injectable so tests drive the loop without real sleeps
                          ) -> Schema__Elastic__Info:
        resolved   = self.resolve_region(region)
        password   = elastic_password or os.environ.get('SG_ELASTIC_PASSWORD', '')
        start      = time.monotonic()
        deadline   = start + max(timeout, 1)
        poll_sec   = max(poll_seconds, 1)
        attempt    = 0
        info       = self.get_stack_info(stack_name = stack_name, region = resolved)
        while time.monotonic() < deadline:
            attempt += 1
            info     = self.get_stack_info(stack_name = stack_name, region = resolved)
            probe    = Enum__Kibana__Probe__Status.UNREACHABLE
            es_probe = Enum__Elastic__Probe__Status.UNREACHABLE
            message  = f'instance state = {info.state}'
            if info.state == Enum__Elastic__State.RUNNING and str(info.kibana_url):
                es_probe = self.http_client.elastic_probe(str(info.kibana_url), 'elastic', password)  # ES is up first; probe it on every tick to surface "ES ready" before Kibana
                probe    = self.http_client.kibana_probe(str(info.kibana_url))
                message  = PROBE_MESSAGES.get(probe, PROBE_MESSAGES[Enum__Kibana__Probe__Status.UNKNOWN])
                if probe == Enum__Kibana__Probe__Status.READY:
                    info.state = Enum__Elastic__State.READY

            tick = Schema__Wait__Tick(attempt       = attempt                            ,
                                      info          = info                               ,
                                      probe         = probe                              ,
                                      elastic_probe = es_probe                           ,
                                      message       = message                            ,
                                      elapsed_ms    = int((time.monotonic() - start) * 1000))
            if on_progress is not None:
                on_progress(tick)

            if info.state == Enum__Elastic__State.READY:
                return info
            if info.state in (Enum__Elastic__State.TERMINATING, Enum__Elastic__State.TERMINATED):
                return info
            sleep_fn(poll_sec)
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
        last_status  = 0
        last_err_msg = ''
        batch_size = max(int(request.batch_size), 1)
        for offset in range(0, len(docs), batch_size):
            chunk = type(docs)()                                                    # Fresh List__Schema__Log__Document for the slice
            for d in docs[offset:offset + batch_size]:
                chunk.append(d)
            batch_posted, batch_failed, http_status, err = self.http_client.bulk_post(
                base_url = str(info.kibana_url) ,
                username = 'elastic'             ,
                password = password              ,
                index    = str(request.index)    ,
                docs     = chunk                  )
            posted      += batch_posted
            failed      += batch_failed
            batches     += 1
            last_status  = http_status
            if err and not last_err_msg:                                            # First error sticks so the user sees the root cause, not the tail
                last_err_msg = err
        elapsed_ms = max(int(time.monotonic() * 1000) - start_ms, 1)
        rate       = int(posted * 1000 / elapsed_ms)

        # Ensure a Kibana data view exists for the seeded index — bypasses the "Now create a data view" wall in Discover.
        # Only attempted when the bulk-post landed at least one doc; nothing to look at otherwise.
        dv_id      = ''
        dv_created = False
        dv_error   = ''
        if request.create_data_view and posted > 0:
            dv = self.saved_objects_client.ensure_data_view(base_url        = str(info.kibana_url)         ,
                                                             username        = 'elastic'                    ,
                                                             password        = password                     ,
                                                             title           = str(request.index)           ,
                                                             time_field_name = str(request.time_field_name) )
            dv_id      = str(dv.id)
            dv_created = bool(dv.created)
            dv_error   = str(dv.error)

        # Import the default 4-panel "Synthetic Logs Overview" dashboard. Needs the data view id, so chained after.
        db_id      = ''
        db_title   = ''
        db_objects = 0
        db_error   = ''
        if request.create_dashboard and posted > 0 and dv_id and not dv_error:
            db = self.saved_objects_client.ensure_default_dashboard(base_url     = str(info.kibana_url)         ,
                                                                     username     = 'elastic'                    ,
                                                                     password     = password                     ,
                                                                     index        = str(request.index)           ,
                                                                     data_view_id = dv_id                         ,
                                                                     time_field   = str(request.time_field_name) )
            db_id      = str(db.id)
            db_title   = str(db.title)
            db_objects = int(db.object_count)
            db_error   = str(db.error)

        return Schema__Elastic__Seed__Response(stack_name         = request.stack_name ,
                                               index              = request.index      ,
                                               documents_posted   = posted              ,
                                               documents_failed   = failed              ,
                                               batches            = batches             ,
                                               duration_ms        = elapsed_ms          ,
                                               docs_per_second    = rate                ,
                                               last_http_status   = last_status         ,
                                               last_error_message = last_err_msg        ,
                                               data_view_id       = dv_id               ,
                                               data_view_created  = dv_created          ,
                                               data_view_error    = dv_error            ,
                                               dashboard_id       = db_id               ,
                                               dashboard_title    = db_title            ,
                                               dashboard_objects  = db_objects          ,
                                               dashboard_error    = db_error            )

    @type_safe
    def harden_kibana(self, stack_name : Safe_Str__Elastic__Stack__Name ,           # Disable Observability / Security / Fleet / ML side-nav groups in the default Kibana space
                            password   : str                            = ''
                       ) -> dict:                                                   # {'ok': bool, 'http_status': int, 'error': str}
        info = self.get_stack_info(stack_name = stack_name)
        if not str(info.kibana_url):
            return {'ok': False, 'http_status': 0, 'error': 'no kibana url for stack'}
        pwd = password or os.environ.get('SG_ELASTIC_PASSWORD', '')
        ok, status, err = self.saved_objects_client.disable_space_features(base_url=str(info.kibana_url), username='elastic', password=pwd)
        return {'ok': ok, 'http_status': status, 'error': err}

    @type_safe
    def wipe_seed(self, stack_name : Safe_Str__Elastic__Stack__Name ,               # Delete the ES index + Kibana data view + auto-generated dashboard saved objects. Idempotent.
                        index      : str                            = 'sg-synthetic',
                        password   : str                            = ''
                   ) -> dict:                                                       # {'index_deleted', 'data_view_deleted', 'dashboard_objects_deleted', plus per-side http_status / error}
        info = self.get_stack_info(stack_name = stack_name)
        if not str(info.kibana_url):
            return {'index_deleted': False, 'index_status': 0, 'index_error': 'no kibana url for stack',
                    'data_view_deleted': False, 'data_view_status': 0, 'data_view_error': 'no kibana url for stack',
                    'dashboard_objects_deleted': 0}
        pwd = password or os.environ.get('SG_ELASTIC_PASSWORD', '')
        idx_deleted, idx_status, idx_err = self.http_client.delete_index(base_url=str(info.kibana_url), username='elastic', password=pwd, index=index)
        dv_deleted , dv_status , dv_err  = self.saved_objects_client.delete_data_view_by_title(base_url=str(info.kibana_url), username='elastic', password=pwd, title=index)
        # Also clean any saved objects from the auto-generated dashboard, including stale lens objects from earlier attempts that otherwise crash savedobjects-service migration on re-import.
        dash_deleted = self.saved_objects_client.delete_default_dashboard_objects(base_url=str(info.kibana_url), username='elastic', password=pwd)
        return {'index_deleted'             : idx_deleted ,
                'index_status'              : idx_status  ,
                'index_error'               : idx_err     ,
                'data_view_deleted'         : dv_deleted  ,
                'data_view_status'          : dv_status   ,
                'data_view_error'           : dv_err      ,
                'dashboard_objects_deleted' : dash_deleted}

    @type_safe
    def health(self, stack_name : Safe_Str__Elastic__Stack__Name ,
                     password   : str                            = '',
                     check_ssm  : bool                           = True
                ) -> Schema__Elastic__Health__Response:
        checks   = List__Schema__Elastic__Health__Check()
        info     = self.get_stack_info(stack_name = stack_name)
        password = password or os.environ.get('SG_ELASTIC_PASSWORD', '')

        # 1) EC2 state                                                              # If the instance isn't running there's nothing more to check from the network side
        state_str  = str(info.state)
        ec2_status = Enum__Health__Status.OK if state_str == 'running' else Enum__Health__Status.FAIL
        ec2_detail = f'state={state_str}' if state_str else 'no instance found for stack'
        checks.append(Schema__Elastic__Health__Check(name='ec2-state', status=ec2_status, detail=ec2_detail))
        if not str(info.instance_id):                                               # No instance — bail; everything else would be pointless skips
            return Schema__Elastic__Health__Response(stack_name=stack_name, all_ok=False, checks=checks)

        # 2) Public IP                                                              # Without a public IP the SG/TCP/HTTP checks all skip
        public_ip = str(info.public_ip)
        if public_ip:
            checks.append(Schema__Elastic__Health__Check(name='public-ip', status=Enum__Health__Status.OK, detail=public_ip))
        else:
            checks.append(Schema__Elastic__Health__Check(name='public-ip', status=Enum__Health__Status.WARN, detail='no public ip yet - instance may still be initialising'))

        # 3) SG ingress vs current caller IP                                        # Most common failure mode: home/office IP rotated since `sp el create`
        current_ip = str(self.ip_detector.detect())
        sg_id      = str(info.security_group_id)
        if not sg_id:
            checks.append(Schema__Elastic__Health__Check(name='sg-ingress', status=Enum__Health__Status.SKIP, detail='no security group on instance'))
        else:
            ingress = self.aws_client.describe_security_group_ingress(str(info.region), sg_id)
            allowed = [r for r in ingress if int(r.get('port') or 0) == 443]
            if not allowed:
                checks.append(Schema__Elastic__Health__Check(name='sg-ingress', status=Enum__Health__Status.FAIL,
                                                              detail=f'no :443 ingress on {sg_id} - recreate the stack'))
            else:
                cidrs    = [r['cidr'] for r in allowed]
                if any(c == f'{current_ip}/32' for c in cidrs):
                    checks.append(Schema__Elastic__Health__Check(name='sg-ingress', status=Enum__Health__Status.OK,
                                                                  detail=f'{current_ip}/32 allowed on :443'))
                else:
                    checks.append(Schema__Elastic__Health__Check(name='sg-ingress', status=Enum__Health__Status.FAIL,
                                                                  detail=f'current IP {current_ip} not in allowed CIDRs {cidrs} - your IP rotated since create'))

        # 4) TCP :443                                                               # The network-level check — catches "ConnectTimeout" before any HTTPS handshake
        if public_ip:
            import socket
            try:
                with socket.create_connection((public_ip, 443), timeout=5):
                    checks.append(Schema__Elastic__Health__Check(name='tcp-443', status=Enum__Health__Status.OK,
                                                                  detail=f'reachable in <5s'))
            except Exception as exc:
                checks.append(Schema__Elastic__Health__Check(name='tcp-443', status=Enum__Health__Status.FAIL,
                                                              detail=f'cannot connect to {public_ip}:443 - {type(exc).__name__}'))
        else:
            checks.append(Schema__Elastic__Health__Check(name='tcp-443', status=Enum__Health__Status.SKIP, detail='no public IP'))

        # 5/6) Elastic + Kibana probes                                              # Skipped if we don't even have a URL; they internally handle UNREACHABLE
        url = str(info.kibana_url)
        if url:
            es_probe = self.http_client.elastic_probe(url, 'elastic', password)
            if es_probe.is_ready():
                checks.append(Schema__Elastic__Health__Check(name='elastic',
                                                              status=Enum__Health__Status.OK   if es_probe == Enum__Elastic__Probe__Status.GREEN else Enum__Health__Status.WARN,
                                                              detail=f'/_cluster/health = {es_probe} (yellow is normal on single-node)'))
            elif es_probe == Enum__Elastic__Probe__Status.AUTH_REQUIRED:
                checks.append(Schema__Elastic__Health__Check(name='elastic', status=Enum__Health__Status.FAIL,
                                                              detail='/_cluster/health returned 401/403 - SG_ELASTIC_PASSWORD does not match'))
            else:
                checks.append(Schema__Elastic__Health__Check(name='elastic', status=Enum__Health__Status.FAIL,
                                                              detail=f'/_cluster/health = {es_probe}'))

            kb_probe = self.http_client.kibana_probe(url)
            kb_status = Enum__Health__Status.OK if kb_probe == Enum__Kibana__Probe__Status.READY else Enum__Health__Status.FAIL
            checks.append(Schema__Elastic__Health__Check(name='kibana', status=kb_status,
                                                          detail=f'/api/status probe = {kb_probe}'))
        else:
            checks.append(Schema__Elastic__Health__Check(name='elastic', status=Enum__Health__Status.SKIP, detail='no URL'))
            checks.append(Schema__Elastic__Health__Check(name='kibana',  status=Enum__Health__Status.SKIP, detail='no URL'))

        # 7/8) SSM-side checks                                                      # Run via the existing SSM seam — works even when :443 is unreachable from the caller
        if check_ssm:
            ssm_calls = [('ssm-boot-status', 'cat /var/log/sg-elastic-boot-status 2>/dev/null || echo MISSING'),
                          ('ssm-docker'     , 'docker ps --format "{{.Names}}: {{.Status}}" 2>/dev/null | head -10')]
            for name, command in ssm_calls:
                stdout, stderr, code, status = self.aws_client.ssm_send_command(region      = str(info.region)  ,
                                                                                instance_id = str(info.instance_id),
                                                                                commands    = [command]            ,
                                                                                timeout     = 30                   )
                if status == 'Success' or code == 0:                                # AWS reports both — treat either as OK so a non-zero-but-Success edge case still surfaces output
                    text = (str(stdout) or '').strip().splitlines()[0:6]            # Snip to fit the diagnostic line
                    checks.append(Schema__Elastic__Health__Check(name=name, status=Enum__Health__Status.OK,
                                                                  detail=' | '.join(text) or '(no output)'))
                else:
                    checks.append(Schema__Elastic__Health__Check(name=name, status=Enum__Health__Status.FAIL,
                                                                  detail=f'SSM exit={code} status={status}'))
        else:
            checks.append(Schema__Elastic__Health__Check(name='ssm-boot-status', status=Enum__Health__Status.SKIP, detail='--no-ssm'))
            checks.append(Schema__Elastic__Health__Check(name='ssm-docker'     , status=Enum__Health__Status.SKIP, detail='--no-ssm'))

        # Rollup: WARN does NOT fail the rollup (it means "expected non-OK", e.g. yellow on single-node ES is normal). Only FAIL flips all_ok false.
        all_ok = not any(c.status == Enum__Health__Status.FAIL for c in checks)
        return Schema__Elastic__Health__Response(stack_name=stack_name, all_ok=all_ok, checks=checks)

    @type_safe
    def run_on_instance(self, stack_name : Safe_Str__Elastic__Stack__Name ,
                              command    : str                            ,
                              region     : Safe_Str__AWS__Region          = None ,
                              timeout    : int                            = 60
                         ) -> Schema__Exec__Result:
        resolved = self.resolve_region(region)
        info     = self.get_stack_info(stack_name = stack_name, region = resolved)
        result   = Schema__Exec__Result(stack_name  = stack_name                 ,
                                        instance_id = info.instance_id           ,
                                        command     = command                    ,
                                        exit_code   = -1                         ,
                                        status      = ''                         )
        if not str(info.instance_id):
            result.stderr = f'No such stack: {stack_name}'
            result.status = 'NotFound'
            return result
        start = time.monotonic()
        stdout, stderr, code, status = self.aws_client.ssm_send_command(region      = str(resolved)      ,
                                                                        instance_id = str(info.instance_id),
                                                                        commands    = [command]            ,
                                                                        timeout     = max(timeout, 1)      )
        result.stdout      = stdout
        result.stderr      = stderr
        result.exit_code   = code
        result.status      = status
        result.duration_ms = int((time.monotonic() - start) * 1000)
        return result

    @type_safe
    def saved_objects_find(self, stack_name : Safe_Str__Elastic__Stack__Name ,
                                  object_type: Enum__Saved_Object__Type      ,
                                  password   : str                            = '',
                                  page_size  : int                            = 100
                            ) -> Schema__Kibana__Find__Response:
        info     = self.get_stack_info(stack_name = stack_name)
        if not str(info.kibana_url):
            return Schema__Kibana__Find__Response()                                 # No public IP yet — empty result, http_status stays 0
        pwd      = password or os.environ.get('SG_ELASTIC_PASSWORD', '')
        return self.saved_objects_client.find(base_url    = str(info.kibana_url),
                                              username    = 'elastic'           ,
                                              password    = pwd                  ,
                                              object_type = object_type          ,
                                              page_size   = page_size            )

    @type_safe
    def saved_objects_export(self, stack_name : Safe_Str__Elastic__Stack__Name ,
                                    object_type: Enum__Saved_Object__Type      ,
                                    output_path: str                            ,
                                    password   : str                            = '',
                                    include_references_deep: bool               = True
                              ) -> Schema__Kibana__Export__Result:
        info     = self.get_stack_info(stack_name = stack_name)
        if not str(info.kibana_url):
            return Schema__Kibana__Export__Result(error = 'no kibana url for stack — is the EC2 instance running?')
        pwd      = password or os.environ.get('SG_ELASTIC_PASSWORD', '')
        ndjson, status, err = self.saved_objects_client.export(base_url               = str(info.kibana_url) ,
                                                                username               = 'elastic'            ,
                                                                password               = pwd                  ,
                                                                object_type            = object_type          ,
                                                                include_references_deep= include_references_deep)
        if err:
            return Schema__Kibana__Export__Result(http_status = status, error = err)
        with open(output_path, 'wb') as f:                                          # Verbatim ndjson — written as bytes so re-import round-trips byte-identical
            f.write(ndjson)
        line_count = sum(1 for line in ndjson.splitlines() if line.strip())
        return Schema__Kibana__Export__Result(object_count  = line_count   ,
                                              bytes_written = len(ndjson)  ,
                                              file_path     = output_path  ,
                                              http_status   = status       ,
                                              error         = ''            )

    @type_safe
    def saved_objects_import(self, stack_name : Safe_Str__Elastic__Stack__Name ,
                                    input_path : str                            ,
                                    password   : str                            = '',
                                    overwrite  : bool                           = True
                              ) -> Schema__Kibana__Import__Result:
        info     = self.get_stack_info(stack_name = stack_name)
        if not str(info.kibana_url):
            return Schema__Kibana__Import__Result(first_error = 'no kibana url for stack — is the EC2 instance running?')
        pwd      = password or os.environ.get('SG_ELASTIC_PASSWORD', '')
        with open(input_path, 'rb') as f:
            ndjson = f.read()
        return self.saved_objects_client.import_objects(base_url     = str(info.kibana_url),
                                                        username     = 'elastic'           ,
                                                        password     = pwd                  ,
                                                        ndjson_bytes = ndjson               ,
                                                        overwrite    = overwrite            )

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
