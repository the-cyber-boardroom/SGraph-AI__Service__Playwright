# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Elastic: Elastic__Service
# ═══════════════════════════════════════════════════════════════════════════════

import os
import secrets

from typing                                                                         import Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute.platforms.ec2.collections.List__Instance__Id           import List__Instance__Id
from sg_compute_specs.elastic.collections.List__Schema__Elastic__Health__Check      import List__Schema__Elastic__Health__Check
from sg_compute_specs.elastic.collections.List__Schema__Elastic__Info               import List__Schema__Elastic__Info
from sg_compute_specs.elastic.enums.Enum__Elastic__State                            import Enum__Elastic__State
from sg_compute_specs.elastic.enums.Enum__Health__Status                            import Enum__Health__Status
from sg_compute_specs.elastic.primitives.Safe_Str__Elastic__Password                import Safe_Str__Elastic__Password
from sg_compute_specs.elastic.primitives.Safe_Str__Elastic__Stack__Name             import Safe_Str__Elastic__Stack__Name
from sg_compute_specs.elastic.schemas.Schema__Elastic__Create__Request              import Schema__Elastic__Create__Request
from sg_compute_specs.elastic.schemas.Schema__Elastic__Create__Response             import Schema__Elastic__Create__Response
from sg_compute_specs.elastic.schemas.Schema__Elastic__Delete__Response             import Schema__Elastic__Delete__Response
from sg_compute_specs.elastic.schemas.Schema__Elastic__Health__Check                import Schema__Elastic__Health__Check
from sg_compute_specs.elastic.schemas.Schema__Elastic__Health__Response             import Schema__Elastic__Health__Response
from sg_compute_specs.elastic.schemas.Schema__Elastic__Info                         import Schema__Elastic__Info
from sg_compute_specs.elastic.schemas.Schema__Elastic__List                         import Schema__Elastic__List
from sg_compute_specs.elastic.service.Elastic__AWS__Client                          import ELASTIC_NAMING


DEFAULT_REGION        = 'eu-west-2'
DEFAULT_INSTANCE_TYPE = 'm6i.xlarge'
PASSWORD_BYTES        = 24

ADJECTIVES = ['bold','bright','calm','clever','cool','daring','deep','eager',
              'fast','fierce','fresh','grand','happy','keen','light','lucky',
              'mellow','neat','quick','quiet','sharp','sleek','smart','swift','witty']
SCIENTISTS = ['bohr','curie','darwin','dirac','einstein','euler','faraday',
              'fermi','feynman','galileo','gauss','hopper','hubble','lovelace',
              'maxwell','newton','noether','pascal','planck','turing','tesla',
              'volta','watt','wien','zeno']


class Elastic__Service(Type_Safe):
    aws_client        : object = None
    http_client       : object = None
    ip_detector       : object = None
    user_data_builder : object = None

    def setup(self) -> 'Elastic__Service':
        from sg_compute_specs.elastic.service.Caller__IP__Detector       import Caller__IP__Detector
        from sg_compute_specs.elastic.service.Elastic__AWS__Client        import Elastic__AWS__Client
        from sg_compute_specs.elastic.service.Elastic__HTTP__Client       import Elastic__HTTP__Client
        from sg_compute_specs.elastic.service.Elastic__User_Data__Builder import Elastic__User_Data__Builder
        self.aws_client        = Elastic__AWS__Client       ()
        self.http_client       = Elastic__HTTP__Client      ()
        self.ip_detector       = Caller__IP__Detector       ()
        self.user_data_builder = Elastic__User_Data__Builder()
        return self

    def create(self, request: Schema__Elastic__Create__Request) -> Schema__Elastic__Create__Response:
        region        = str(request.region       ) or DEFAULT_REGION
        stack_name    = str(request.stack_name   ) or self._random_stack_name()
        caller_ip     = str(request.caller_ip    ) or str(self.ip_detector.detect())
        instance_type = str(request.instance_type) or DEFAULT_INSTANCE_TYPE
        ami_id        = str(request.from_ami     ) or self.aws_client.resolve_latest_al2023_ami(region)
        creator       = self._resolve_creator()
        password      = (str(request.elastic_password)
                         or secrets.token_urlsafe(PASSWORD_BYTES))
        password_prim = Safe_Str__Elastic__Password(password)

        sg_id        = self.aws_client.ensure_security_group(region, stack_name, caller_ip, creator)
        profile_name = self.aws_client.ensure_instance_profile(region)
        max_hours    = max(int(request.max_hours), 0)
        user_data    = self.user_data_builder.render(stack_name       = Safe_Str__Elastic__Stack__Name(stack_name),
                                                     elastic_password = password_prim                              ,
                                                     max_hours        = max_hours                                  )
        instance_id  = self.aws_client.launch_instance(region                = region                          ,
                                                        stack_name            = stack_name                       ,
                                                        ami_id                = ami_id                           ,
                                                        instance_type         = instance_type                    ,
                                                        security_group_id     = sg_id                           ,
                                                        user_data             = user_data                       ,
                                                        caller_ip             = caller_ip                       ,
                                                        instance_profile_name = profile_name                    ,
                                                        creator               = creator                         ,
                                                        max_hours             = max_hours                       )
        return Schema__Elastic__Create__Response(
            stack_name        = stack_name                              ,
            aws_name_tag      = ELASTIC_NAMING.aws_name_for_stack(stack_name),
            instance_id       = instance_id                            ,
            region            = region                                 ,
            ami_id            = ami_id                                 ,
            instance_type     = instance_type                          ,
            security_group_id = sg_id                                  ,
            caller_ip         = caller_ip                              ,
            public_ip         = ''                                     ,
            kibana_url        = ''                                     ,
            elastic_password  = password_prim                          ,
            state             = Enum__Elastic__State.PENDING           )

    def list_stacks(self, region: str) -> Schema__Elastic__List:
        details_by = self.aws_client.list_elastic_instances(region)
        stacks     = List__Schema__Elastic__Info()
        for instance_id in sorted(details_by.keys()):
            details = details_by[instance_id]
            details['__region'] = region
            stacks.append(self.aws_client.build_instance_info(details))
        return Schema__Elastic__List(region=region, stacks=stacks)

    def get_stack_info(self, stack_name: str, region: str) -> Optional[Schema__Elastic__Info]:
        details = self.aws_client.find_by_stack_name(region, stack_name)
        if details is None:
            return None
        details['__region'] = region
        return self.aws_client.build_instance_info(details)

    def delete_stack(self, stack_name: str, region: str) -> Schema__Elastic__Delete__Response:
        details = self.aws_client.find_by_stack_name(region, stack_name)
        if details is None:
            return Schema__Elastic__Delete__Response(stack_name=stack_name)
        instance_id = str(details.get('InstanceId', ''))
        sg_list     = details.get('SecurityGroups', [])
        sg_id       = str(sg_list[0].get('GroupId', '')) if sg_list else ''
        terminated  = self.aws_client.terminate_instance(region, instance_id)
        sg_deleted  = False
        if terminated and sg_id:
            sg_deleted = self.aws_client.delete_security_group(region, sg_id)
        ids = List__Instance__Id()
        if terminated and instance_id:
            ids.append(instance_id)
        return Schema__Elastic__Delete__Response(stack_name             = stack_name ,
                                                  target                  = instance_id,
                                                  terminated_instance_ids = ids        ,
                                                  security_group_deleted  = sg_deleted )

    def health(self, stack_name: str, region: str = '', password: str = '') -> Schema__Elastic__Health__Response:
        region   = region or DEFAULT_REGION
        password = password or os.environ.get('SG_ELASTIC_PASSWORD', '')
        checks   = List__Schema__Elastic__Health__Check()
        info     = self.get_stack_info(stack_name, region)

        if info is None:
            checks.append(Schema__Elastic__Health__Check(name='ec2-state', status=Enum__Health__Status.FAIL,
                                                          detail='no instance found for stack'))
            return Schema__Elastic__Health__Response(stack_name=stack_name, all_ok=False, checks=checks)

        state_str  = str(info.state)
        ec2_status = Enum__Health__Status.OK if state_str == 'running' else Enum__Health__Status.FAIL
        checks.append(Schema__Elastic__Health__Check(name='ec2-state', status=ec2_status,
                                                      detail=f'state={state_str}'))

        public_ip = str(info.public_ip)
        if public_ip:
            checks.append(Schema__Elastic__Health__Check(name='public-ip', status=Enum__Health__Status.OK,
                                                          detail=public_ip))
        else:
            checks.append(Schema__Elastic__Health__Check(name='public-ip', status=Enum__Health__Status.WARN,
                                                          detail='no public ip yet'))

        url = str(info.kibana_url)
        if url:
            es_probe = self.http_client.elastic_probe(url, 'elastic', password)
            if es_probe.is_ready():
                checks.append(Schema__Elastic__Health__Check(name='elastic',
                                                              status=Enum__Health__Status.OK   if str(es_probe) == 'green' else Enum__Health__Status.WARN,
                                                              detail=f'/_cluster/health = {es_probe}'))
            else:
                checks.append(Schema__Elastic__Health__Check(name='elastic', status=Enum__Health__Status.FAIL,
                                                              detail=f'/_cluster/health = {es_probe}'))
            kb_probe = self.http_client.kibana_probe(url)
            kb_status = Enum__Health__Status.OK if str(kb_probe) == 'ready' else Enum__Health__Status.FAIL
            checks.append(Schema__Elastic__Health__Check(name='kibana', status=kb_status,
                                                          detail=f'/api/status probe = {kb_probe}'))
        else:
            checks.append(Schema__Elastic__Health__Check(name='elastic', status=Enum__Health__Status.SKIP, detail='no URL'))
            checks.append(Schema__Elastic__Health__Check(name='kibana' , status=Enum__Health__Status.SKIP, detail='no URL'))

        all_ok = not any(c.status == Enum__Health__Status.FAIL for c in checks)
        return Schema__Elastic__Health__Response(stack_name=stack_name, all_ok=all_ok, checks=checks)

    def _random_stack_name(self) -> str:
        return f'elastic-{secrets.choice(ADJECTIVES)}-{secrets.choice(SCIENTISTS)}'

    def _resolve_creator(self) -> str:
        return os.environ.get('USER', '') or os.environ.get('LOGNAME', '') or 'sg-elastic'
