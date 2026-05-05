# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Prometheus: Prometheus__AWS__Client
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute.platforms.ec2.helpers.Stack__Naming                            import Stack__Naming



TAG_PURPOSE_KEY    = 'sg:purpose'
TAG_PURPOSE_VALUE  = 'prometheus'
TAG_STACK_NAME_KEY = 'sg:stack-name'
TAG_ALLOWED_IP_KEY = 'sg:allowed-ip'
TAG_CREATOR_KEY    = 'sg:creator'
TAG_SECTION_KEY    = 'sg:section'
TAG_SECTION_VALUE  = 'prom'

PROM_NAMING = Stack__Naming(section_prefix='prometheus')                            # AWS Name tag carries 'prometheus-' prefix


class Prometheus__AWS__Client(Type_Safe):
    sg       : object = None
    ami      : object = None
    instance : object = None
    tags     : object = None
    launch   : object = None

    def setup(self) -> 'Prometheus__AWS__Client':
        from sg_compute_specs.prometheus.service.Prometheus__SG__Helper       import Prometheus__SG__Helper
        from sg_compute_specs.prometheus.service.Prometheus__AMI__Helper      import Prometheus__AMI__Helper
        from sg_compute_specs.prometheus.service.Prometheus__Instance__Helper import Prometheus__Instance__Helper
        from sg_compute_specs.prometheus.service.Prometheus__Launch__Helper   import Prometheus__Launch__Helper
        from sg_compute_specs.prometheus.service.Prometheus__Tags__Builder    import Prometheus__Tags__Builder
        self.sg       = Prometheus__SG__Helper      ()
        self.ami      = Prometheus__AMI__Helper     ()
        self.instance = Prometheus__Instance__Helper()
        self.tags     = Prometheus__Tags__Builder   ()
        self.launch   = Prometheus__Launch__Helper  ()
        return self
