# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — OpenSearch__Service
# Tier-1 pure-logic orchestrator for sp os. Composes the per-concern helpers
# and exposes the operations consumed by both the typer CLI (Tier 2A) and
# the FastAPI routes (Tier 2B). No print(), no Console — ergonomic concerns
# live in the wrappers.
# ═══════════════════════════════════════════════════════════════════════════════

import secrets

from typing                                                                         import Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.ec2.collections.List__Instance__Id           import List__Instance__Id
from sgraph_ai_service_playwright__cli.opensearch.collections.List__Schema__OS__Stack__Info import List__Schema__OS__Stack__Info
from sgraph_ai_service_playwright__cli.opensearch.enums.Enum__OS__Stack__State      import Enum__OS__Stack__State
from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Health        import Schema__OS__Health
from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Stack__Create__Request  import Schema__OS__Stack__Create__Request
from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Stack__Create__Response import Schema__OS__Stack__Create__Response
from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Stack__Delete__Response import Schema__OS__Stack__Delete__Response
from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Stack__Info   import Schema__OS__Stack__Info
from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Stack__List   import Schema__OS__Stack__List
from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__AWS__Client   import OS_NAMING


DEFAULT_REGION = 'eu-west-2'
PASSWORD_BYTES = 24                                                                 # secrets.token_urlsafe(24) ⇒ 32-char URL-safe base64; fits Safe_Str__OS__Password regex (16-64)
PROFILE_NAME   = 'playwright-ec2'                                                   # Reuses the existing IAM instance profile (has AmazonSSMManagedInstanceCore — required for `sp os connect` once it lands)


class OpenSearch__Service(Type_Safe):
    aws_client        : object = None                                               # OpenSearch__AWS__Client       (lazy via setup())
    probe             : object = None                                               # OpenSearch__HTTP__Probe       (lazy via setup())
    mapper            : object = None                                               # OpenSearch__Stack__Mapper     (lazy via setup())
    ip_detector       : object = None                                               # Caller__IP__Detector          (lazy via setup())
    name_gen          : object = None                                               # Random__Stack__Name__Generator (lazy via setup())
    compose_template  : object = None                                               # OpenSearch__Compose__Template (lazy via setup())
    user_data_builder : object = None                                               # OpenSearch__User_Data__Builder (lazy via setup())

    def setup(self) -> 'OpenSearch__Service':                                       # Lazy imports avoid circular module-load
        from sgraph_ai_service_playwright__cli.opensearch.service.Caller__IP__Detector            import Caller__IP__Detector
        from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__AWS__Client         import OpenSearch__AWS__Client
        from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__Compose__Template   import OpenSearch__Compose__Template
        from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__HTTP__Base          import OpenSearch__HTTP__Base
        from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__HTTP__Probe         import OpenSearch__HTTP__Probe
        from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__Stack__Mapper       import OpenSearch__Stack__Mapper
        from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__User_Data__Builder  import OpenSearch__User_Data__Builder
        from sgraph_ai_service_playwright__cli.opensearch.service.Random__Stack__Name__Generator  import Random__Stack__Name__Generator
        self.aws_client        = OpenSearch__AWS__Client()       .setup()
        self.probe             = OpenSearch__HTTP__Probe(http=OpenSearch__HTTP__Base())
        self.mapper            = OpenSearch__Stack__Mapper()
        self.ip_detector       = Caller__IP__Detector()
        self.name_gen          = Random__Stack__Name__Generator()
        self.compose_template  = OpenSearch__Compose__Template()
        self.user_data_builder = OpenSearch__User_Data__Builder()
        return self

    def create_stack(self, request: Schema__OS__Stack__Create__Request, creator: str = '') -> Schema__OS__Stack__Create__Response:
        stack_name = str(request.stack_name)     or f'os-{self.name_gen.generate()}'    # Empty → 'os-{adjective}-{scientist}'
        region     = str(request.region    )     or DEFAULT_REGION
        caller_ip  = str(request.caller_ip )     or str(self.ip_detector.detect())
        password   = str(request.admin_password) or secrets.token_urlsafe(PASSWORD_BYTES)
        ami_id     = str(request.from_ami  )     or self.aws_client.ami.latest_al2023_ami_id(region)

        sg_id        = self.aws_client.sg.ensure_security_group(region, stack_name, caller_ip)
        tags         = self.aws_client.tags.build(stack_name, caller_ip, creator)
        compose_yaml = self.compose_template.render(admin_password=password)
        user_data    = self.user_data_builder.render(stack_name, region, compose_yaml)
        instance_id  = self.aws_client.launch.run_instance(region, ami_id, sg_id, user_data, tags,
                                                            instance_type         = str(request.instance_type) or 't3.large',
                                                            instance_profile_name = PROFILE_NAME                            )    # Required for SSM agent registration (TargetNotConnected without it).

        return Schema__OS__Stack__Create__Response(
            stack_name        = stack_name                                              ,
            aws_name_tag      = OS_NAMING.aws_name_for_stack(stack_name)                ,
            instance_id       = instance_id                                              ,
            region            = region                                                    ,
            ami_id            = ami_id                                                    ,
            instance_type     = str(request.instance_type) or 't3.large'                  ,
            security_group_id = sg_id                                                     ,
            caller_ip         = caller_ip                                                 ,
            admin_password    = password                                                  ,
            state             = Enum__OS__Stack__State.PENDING                            )

    def list_stacks(self, region: str) -> Schema__OS__Stack__List:
        raw      = self.aws_client.instance.list_stacks(region)
        stacks   = List__Schema__OS__Stack__Info()
        for details in raw.values():
            stacks.append(self.mapper.to_info(details, region))
        return Schema__OS__Stack__List(region=region, stacks=stacks)

    def get_stack_info(self, region: str, stack_name: str) -> Optional[Schema__OS__Stack__Info]:
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        return self.mapper.to_info(details, region) if details else None

    def delete_stack(self, region: str, stack_name: str) -> Schema__OS__Stack__Delete__Response:
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        if not details:
            return Schema__OS__Stack__Delete__Response()                            # Empty fields ⇒ route returns 404
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
            stack_name     = stack_name                                       ,
            state          = Enum__OS__Stack__State.READY if (cluster and dashboards_ok) else info.state,
            cluster_status = str(cluster.get('status', ''))                   ,
            node_count     = int(cluster.get('number_of_nodes' , -1))         ,
            active_shards  = int(cluster.get('active_shards'   , -1))         ,
            doc_count      = -1                                                ,    # Doc count probe lands when Index helper exists
            dashboards_ok  = dashboards_ok                                    ,
            os_endpoint_ok = bool(cluster)                                    )
