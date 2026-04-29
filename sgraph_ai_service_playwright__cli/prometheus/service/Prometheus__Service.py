# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Prometheus__Service
# Tier-1 pure-logic orchestrator for sp prom. Composes the per-concern helpers
# and exposes the operations consumed by both the typer CLI (Tier 2A) and the
# FastAPI routes (Tier 2B). No print(), no Console — ergonomic concerns live
# in the wrappers.
#
# Operations:
#   - list_stacks(region)
#   - get_stack_info(region, stack_name)
#   - delete_stack(region, stack_name)
#   - health(region, stack_name)
#   - create_stack(request, creator='')                                            (wired in step 6f.4b)
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.ec2.collections.List__Instance__Id           import List__Instance__Id
from sgraph_ai_service_playwright__cli.prometheus.collections.List__Schema__Prom__Stack__Info import List__Schema__Prom__Stack__Info
from sgraph_ai_service_playwright__cli.prometheus.enums.Enum__Prom__Stack__State    import Enum__Prom__Stack__State
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Health      import Schema__Prom__Health
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__Create__Request  import Schema__Prom__Stack__Create__Request
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__Create__Response import Schema__Prom__Stack__Create__Response
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__Delete__Response import Schema__Prom__Stack__Delete__Response
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__Info import Schema__Prom__Stack__Info
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__List import Schema__Prom__Stack__List
from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__AWS__Client   import PROM_NAMING


DEFAULT_REGION        = 'eu-west-2'
DEFAULT_INSTANCE_TYPE = 't3.medium'                                                 # Mirrors Prometheus__Launch__Helper.DEFAULT_INSTANCE_TYPE
PROFILE_NAME          = 'playwright-ec2'                                            # Reuses the existing IAM instance profile (has AmazonSSMManagedInstanceCore — required for `sp prom connect` once it lands)


def _count_targets(targets_body: dict) -> tuple:                                    # (total, up) derived from data.activeTargets
    active = (targets_body.get('data') or {}).get('activeTargets') or []
    total  = len(active)
    up     = sum(1 for t in active if (t.get('health') or '').lower() == 'up')
    return total, up


class Prometheus__Service(Type_Safe):
    aws_client        : object = None                                               # Prometheus__AWS__Client        (lazy via setup())
    probe             : object = None                                               # Prometheus__HTTP__Probe        (lazy via setup())
    mapper            : object = None                                               # Prometheus__Stack__Mapper      (lazy via setup())
    ip_detector       : object = None                                               # Caller__IP__Detector           (lazy via setup())
    name_gen          : object = None                                               # Random__Stack__Name__Generator (lazy via setup())
    compose_template  : object = None                                               # Prometheus__Compose__Template  (lazy via setup())
    config_generator  : object = None                                               # Prometheus__Config__Generator  (lazy via setup())
    user_data_builder : object = None                                               # Prometheus__User_Data__Builder (lazy via setup())

    def setup(self) -> 'Prometheus__Service':                                       # Lazy imports avoid circular module-load
        from sgraph_ai_service_playwright__cli.prometheus.service.Caller__IP__Detector            import Caller__IP__Detector
        from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__AWS__Client         import Prometheus__AWS__Client
        from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__Compose__Template   import Prometheus__Compose__Template
        from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__Config__Generator   import Prometheus__Config__Generator
        from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__HTTP__Base          import Prometheus__HTTP__Base
        from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__HTTP__Probe         import Prometheus__HTTP__Probe
        from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__Stack__Mapper       import Prometheus__Stack__Mapper
        from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__User_Data__Builder  import Prometheus__User_Data__Builder
        from sgraph_ai_service_playwright__cli.prometheus.service.Random__Stack__Name__Generator  import Random__Stack__Name__Generator
        self.aws_client        = Prometheus__AWS__Client()       .setup()
        self.probe             = Prometheus__HTTP__Probe(http=Prometheus__HTTP__Base())
        self.mapper            = Prometheus__Stack__Mapper()
        self.ip_detector       = Caller__IP__Detector()
        self.name_gen          = Random__Stack__Name__Generator()
        self.compose_template  = Prometheus__Compose__Template()
        self.config_generator  = Prometheus__Config__Generator()
        self.user_data_builder = Prometheus__User_Data__Builder()
        return self

    def create_stack(self, request: Schema__Prom__Stack__Create__Request, creator: str = '') -> Schema__Prom__Stack__Create__Response:
        stack_name = str(request.stack_name)    or f'prom-{self.name_gen.generate()}'  # Empty → 'prom-{adjective}-{scientist}'
        region     = str(request.region    )    or DEFAULT_REGION
        caller_ip  = str(request.caller_ip )    or str(self.ip_detector.detect())
        ami_id     = str(request.from_ami  )    or self.aws_client.ami.latest_al2023_ami_id(region)
        inst_type  = str(request.instance_type) or DEFAULT_INSTANCE_TYPE

        sg_id        = self.aws_client.sg.ensure_security_group(region, stack_name, caller_ip)
        tags         = self.aws_client.tags.build(stack_name, caller_ip, creator)
        compose_yaml = self.compose_template.render()
        config_yaml  = self.config_generator.render(request.scrape_targets)
        user_data    = self.user_data_builder.render(stack_name, region, compose_yaml, config_yaml)
        instance_id  = self.aws_client.launch.run_instance(region, ami_id, sg_id, user_data, tags,
                                                              instance_type         = inst_type   ,
                                                              instance_profile_name = PROFILE_NAME)        # Required for SSM agent registration (TargetNotConnected without it).

        return Schema__Prom__Stack__Create__Response(
            stack_name        = stack_name                                              ,
            aws_name_tag      = PROM_NAMING.aws_name_for_stack(stack_name)              ,
            instance_id       = instance_id                                              ,
            region            = region                                                    ,
            ami_id            = ami_id                                                    ,
            instance_type     = inst_type                                                ,
            security_group_id = sg_id                                                     ,
            caller_ip         = caller_ip                                                 ,
            targets_count     = len(request.scrape_targets)                              ,
            state             = Enum__Prom__Stack__State.PENDING                         )

    def list_stacks(self, region: str) -> Schema__Prom__Stack__List:
        raw    = self.aws_client.instance.list_stacks(region)
        stacks = List__Schema__Prom__Stack__Info()
        for details in raw.values():
            stacks.append(self.mapper.to_info(details, region))
        return Schema__Prom__Stack__List(region=region, stacks=stacks)

    def get_stack_info(self, region: str, stack_name: str) -> Optional[Schema__Prom__Stack__Info]:
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        return self.mapper.to_info(details, region) if details else None

    def delete_stack(self, region: str, stack_name: str) -> Schema__Prom__Stack__Delete__Response:
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        if not details:
            return Schema__Prom__Stack__Delete__Response()                          # Empty fields ⇒ route returns 404
        instance_id = details.get('InstanceId', '')
        ok          = self.aws_client.instance.terminate_instance(region, instance_id)
        terminated  = List__Instance__Id()
        if ok and instance_id:
            terminated.append(instance_id)
        return Schema__Prom__Stack__Delete__Response(target=instance_id, stack_name=stack_name, terminated_instance_ids=terminated)

    def health(self, region: str, stack_name: str, username: str = '', password: str = '') -> Schema__Prom__Health:
        info = self.get_stack_info(region, stack_name)
        if info is None or not str(info.public_ip):
            return Schema__Prom__Health(stack_name=stack_name, error='instance not running or no public IP')
        prom_url       = str(info.prometheus_url)
        prometheus_ok  = self.probe.prometheus_ready(prom_url, username, password)
        targets_body   = self.probe.targets_status (prom_url, username, password)
        total, up      = _count_targets(targets_body) if targets_body else (-1, -1)
        return Schema__Prom__Health(
            stack_name    = stack_name                                                   ,
            state         = Enum__Prom__Stack__State.READY if prometheus_ok else info.state,
            prometheus_ok = prometheus_ok                                                ,
            targets_total = total                                                         ,
            targets_up    = up                                                            )
