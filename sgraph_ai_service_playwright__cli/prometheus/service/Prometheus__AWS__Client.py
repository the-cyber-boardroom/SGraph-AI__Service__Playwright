# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Prometheus__AWS__Client
# Composition shell for the per-concern AWS helpers (SG / AMI / Instance /
# Tags). Mirrors the OpenSearch__AWS__Client + Elastic__AWS__Client +
# Ec2__AWS__Client patterns. Owns the tag-key constants and the PROM_NAMING
# binding so the section's AWS surface is in one shared header.
#
# Tag convention (mirrors elastic + os + ec2):
#   sg:purpose      : prometheus
#   sg:stack-name   : {stack_name}                 ← logical name lookup
#   sg:allowed-ip   : {caller_ip}                  ← records what /32 was set
#   sg:creator      : git email or $USER
#   sg:section      : prom
#
# Launch__Helper joined the setup() chain in step 6f.4a.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.aws.Stack__Naming                            import Stack__Naming


TAG_PURPOSE_KEY     = 'sg:purpose'
TAG_PURPOSE_VALUE   = 'prometheus'
TAG_STACK_NAME_KEY  = 'sg:stack-name'
TAG_ALLOWED_IP_KEY  = 'sg:allowed-ip'
TAG_CREATOR_KEY     = 'sg:creator'
TAG_SECTION_KEY     = 'sg:section'
TAG_SECTION_VALUE   = 'prom'


PROM_NAMING = Stack__Naming(section_prefix='prometheus')                            # AWS Name tag carries 'prometheus-' prefix; never doubled


class Prometheus__AWS__Client(Type_Safe):                                           # Composes the per-concern helpers — kept small on purpose
    sg       : object = None                                                        # Prometheus__SG__Helper       (lazy via setup())
    ami      : object = None                                                        # Prometheus__AMI__Helper      (lazy via setup())
    instance : object = None                                                        # Prometheus__Instance__Helper (lazy via setup())
    tags     : object = None                                                        # Prometheus__Tags__Builder    (lazy via setup())
    launch   : object = None                                                        # Prometheus__Launch__Helper   (lazy via setup())

    def setup(self) -> 'Prometheus__AWS__Client':                                   # Lazy import — avoids circular module-load when callers import the client first
        from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__SG__Helper       import Prometheus__SG__Helper
        from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__AMI__Helper      import Prometheus__AMI__Helper
        from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__Instance__Helper import Prometheus__Instance__Helper
        from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__Launch__Helper   import Prometheus__Launch__Helper
        from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__Tags__Builder    import Prometheus__Tags__Builder
        self.sg       = Prometheus__SG__Helper      ()
        self.ami      = Prometheus__AMI__Helper     ()
        self.instance = Prometheus__Instance__Helper()
        self.tags     = Prometheus__Tags__Builder   ()
        self.launch   = Prometheus__Launch__Helper  ()
        return self
