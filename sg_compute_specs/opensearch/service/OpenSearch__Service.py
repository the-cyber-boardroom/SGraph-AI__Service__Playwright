# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — OpenSearch: OpenSearch__Service
# ═══════════════════════════════════════════════════════════════════════════════

import secrets

from typing                                                                         import Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute.platforms.ec2.collections.List__Instance__Id           import List__Instance__Id
from sg_compute_specs.opensearch.collections.List__Schema__OS__Stack__Info          import List__Schema__OS__Stack__Info
from sg_compute_specs.opensearch.enums.Enum__OS__Stack__State                       import Enum__OS__Stack__State
from sg_compute_specs.opensearch.schemas.Schema__OS__Health                         import Schema__OS__Health
from sg_compute_specs.opensearch.schemas.Schema__OS__Stack__Create__Request         import Schema__OS__Stack__Create__Request
from sg_compute_specs.opensearch.schemas.Schema__OS__Stack__Create__Response        import Schema__OS__Stack__Create__Response
from sg_compute_specs.opensearch.schemas.Schema__OS__Stack__Delete__Response        import Schema__OS__Stack__Delete__Response
from sg_compute_specs.opensearch.schemas.Schema__OS__Stack__Info                    import Schema__OS__Stack__Info
from sg_compute_specs.opensearch.schemas.Schema__OS__Stack__List                    import Schema__OS__Stack__List
from typing import Optional

from sg_compute_specs.opensearch.service.Caller__IP__Detector           import Caller__IP__Detector
from sg_compute_specs.opensearch.service.OpenSearch__AWS__Client        import OpenSearch__AWS__Client
from sg_compute_specs.opensearch.service.OpenSearch__Tags                    import OS_NAMING
from sg_compute_specs.opensearch.service.OpenSearch__Compose__Template  import OpenSearch__Compose__Template
from sg_compute_specs.opensearch.service.OpenSearch__HTTP__Base         import OpenSearch__HTTP__Base
from sg_compute_specs.opensearch.service.OpenSearch__HTTP__Probe        import OpenSearch__HTTP__Probe
from sg_compute_specs.opensearch.service.OpenSearch__Stack__Mapper      import OpenSearch__Stack__Mapper
from sg_compute_specs.opensearch.service.OpenSearch__User_Data__Builder import OpenSearch__User_Data__Builder
from sg_compute_specs.opensearch.service.Random__Stack__Name__Generator import Random__Stack__Name__Generator


DEFAULT_REGION = 'eu-west-2'
PASSWORD_BYTES = 24
PROFILE_NAME   = 'playwright-ec2'


class OpenSearch__Service(Type_Safe):
    aws_client        : Optional[OpenSearch__AWS__Client]        = None
    probe             : Optional[OpenSearch__HTTP__Probe]        = None
    mapper            : Optional[OpenSearch__Stack__Mapper]      = None
    ip_detector       : Optional[Caller__IP__Detector]           = None
    name_gen          : Optional[Random__Stack__Name__Generator] = None
    compose_template  : Optional[OpenSearch__Compose__Template]  = None
    user_data_builder : Optional[OpenSearch__User_Data__Builder] = None

    def setup(self) -> 'OpenSearch__Service':
        self.aws_client        = OpenSearch__AWS__Client()      .setup()
        self.probe             = OpenSearch__HTTP__Probe(http=OpenSearch__HTTP__Base())
        self.mapper            = OpenSearch__Stack__Mapper()
        self.ip_detector       = Caller__IP__Detector()
        self.name_gen          = Random__Stack__Name__Generator()
        self.compose_template  = OpenSearch__Compose__Template()
        self.user_data_builder = OpenSearch__User_Data__Builder()
        return self

    def create_stack(self, request: Schema__OS__Stack__Create__Request, creator: str = '') -> Schema__OS__Stack__Create__Response:
        stack_name = str(request.stack_name    ) or f'os-{self.name_gen.generate()}'
        region     = str(request.region        ) or DEFAULT_REGION
        caller_ip  = str(request.caller_ip     ) or str(self.ip_detector.detect())
        password   = str(request.admin_password) or secrets.token_urlsafe(PASSWORD_BYTES)
        ami_id     = str(request.from_ami      ) or self.aws_client.ami.latest_al2023_ami_id(region)

        sg_id        = self.aws_client.sg.ensure_security_group(region, stack_name, caller_ip)
        tags         = self.aws_client.tags.build(stack_name, caller_ip, creator)
        compose_yaml = self.compose_template.render(admin_password=password)
        user_data    = self.user_data_builder.render(stack_name, region, compose_yaml)
        instance_id  = self.aws_client.launch.run_instance(region, ami_id, sg_id, user_data, tags,
                                                            instance_type         = str(request.instance_type) or 't3.large',
                                                            instance_profile_name = PROFILE_NAME)

        return Schema__OS__Stack__Create__Response(
            stack_name        = stack_name                          ,
            aws_name_tag      = OS_NAMING.aws_name_for_stack(stack_name),
            instance_id       = instance_id                         ,
            region            = region                              ,
            ami_id            = ami_id                              ,
            instance_type     = str(request.instance_type) or 't3.large',
            security_group_id = sg_id                               ,
            caller_ip         = caller_ip                           ,
            admin_password    = password                            ,
            state             = Enum__OS__Stack__State.PENDING      )

    def list_stacks(self, region: str) -> Schema__OS__Stack__List:
        raw    = self.aws_client.instance.list_stacks(region)
        stacks = List__Schema__OS__Stack__Info()
        for details in raw.values():
            stacks.append(self.mapper.to_info(details, region))
        return Schema__OS__Stack__List(region=region, stacks=stacks)

    def get_stack_info(self, region: str, stack_name: str) -> Optional[Schema__OS__Stack__Info]:
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        return self.mapper.to_info(details, region) if details else None

    def delete_stack(self, region: str, stack_name: str) -> Schema__OS__Stack__Delete__Response:
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        if not details:
            return Schema__OS__Stack__Delete__Response()
        instance_id = details.get('InstanceId', '')
        ok          = self.aws_client.instance.terminate_instance(region, instance_id)
        terminated  = List__Instance__Id()
        if ok and instance_id:
            terminated.append(instance_id)
        return Schema__OS__Stack__Delete__Response(target=instance_id, stack_name=stack_name, terminated_instance_ids=terminated)

    def health(self, region: str, stack_name: str, username: str = '', password: str = '') -> Schema__OS__Health:
        info = self.get_stack_info(region, stack_name)
        if info is None or not str(info.public_ip):
            return Schema__OS__Health(stack_name=stack_name, error='instance not running or no public IP')
        os_url        = str(info.os_endpoint   )
        dash_url      = str(info.dashboards_url)
        cluster       = self.probe.cluster_health  (os_url  , username, password)
        dashboards_ok = self.probe.dashboards_ready(dash_url, username, password)
        return Schema__OS__Health(
            stack_name     = stack_name                                                                       ,
            state          = Enum__OS__Stack__State.READY if (cluster and dashboards_ok) else info.state      ,
            cluster_status = str(cluster.get('status', ''))                                                   ,
            node_count     = int(cluster.get('number_of_nodes', -1))                                          ,
            active_shards  = int(cluster.get('active_shards'  , -1))                                          ,
            doc_count      = -1                                                                               ,
            dashboards_ok  = dashboards_ok                                                                    ,
            os_endpoint_ok = bool(cluster)                                                                    )
