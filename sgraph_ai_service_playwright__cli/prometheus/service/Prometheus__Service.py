# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Prometheus__Service
# Tier-1 pure-logic orchestrator for sp prom. Composes the per-concern helpers
# and exposes the operations consumed by both the typer CLI (Tier 2A) and the
# FastAPI routes (Tier 2B). No print(), no Console — ergonomic concerns live
# in the wrappers.
#
# Read paths (this slice — 6e):
#   - list_stacks(region)
#   - get_stack_info(region, stack_name)
#   - delete_stack(region, stack_name)
#   - health(region, stack_name)
#
# create_stack lands in step 6f.4b.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.ec2.collections.List__Instance__Id           import List__Instance__Id
from sgraph_ai_service_playwright__cli.prometheus.collections.List__Schema__Prom__Stack__Info import List__Schema__Prom__Stack__Info
from sgraph_ai_service_playwright__cli.prometheus.enums.Enum__Prom__Stack__State    import Enum__Prom__Stack__State
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Health      import Schema__Prom__Health
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__Delete__Response import Schema__Prom__Stack__Delete__Response
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__Info import Schema__Prom__Stack__Info
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__List import Schema__Prom__Stack__List


DEFAULT_REGION = 'eu-west-2'


def _count_targets(targets_body: dict) -> tuple:                                    # (total, up) derived from data.activeTargets
    active = (targets_body.get('data') or {}).get('activeTargets') or []
    total  = len(active)
    up     = sum(1 for t in active if (t.get('health') or '').lower() == 'up')
    return total, up


class Prometheus__Service(Type_Safe):
    aws_client  : object = None                                                     # Prometheus__AWS__Client       (lazy via setup())
    probe       : object = None                                                     # Prometheus__HTTP__Probe       (lazy via setup())
    mapper      : object = None                                                     # Prometheus__Stack__Mapper     (lazy via setup())
    ip_detector : object = None                                                     # Caller__IP__Detector          (lazy via setup())
    name_gen    : object = None                                                     # Random__Stack__Name__Generator (lazy via setup())

    def setup(self) -> 'Prometheus__Service':                                       # Lazy imports avoid circular module-load
        from sgraph_ai_service_playwright__cli.prometheus.service.Caller__IP__Detector            import Caller__IP__Detector
        from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__AWS__Client         import Prometheus__AWS__Client
        from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__HTTP__Base          import Prometheus__HTTP__Base
        from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__HTTP__Probe         import Prometheus__HTTP__Probe
        from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__Stack__Mapper       import Prometheus__Stack__Mapper
        from sgraph_ai_service_playwright__cli.prometheus.service.Random__Stack__Name__Generator  import Random__Stack__Name__Generator
        self.aws_client  = Prometheus__AWS__Client()       .setup()
        self.probe       = Prometheus__HTTP__Probe(http=Prometheus__HTTP__Base())
        self.mapper      = Prometheus__Stack__Mapper()
        self.ip_detector = Caller__IP__Detector()
        self.name_gen    = Random__Stack__Name__Generator()
        return self

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
