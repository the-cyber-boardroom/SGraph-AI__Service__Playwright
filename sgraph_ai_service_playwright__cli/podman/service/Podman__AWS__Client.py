# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Podman__AWS__Client
# Composition shell for the per-concern AWS helpers (SG / AMI / Instance /
# Tags / Launch). Mirrors Linux__AWS__Client.
#
# Tag convention:
#   sg:purpose      : podman
#   sg:stack-name   : {stack_name}
#   sg:allowed-ip   : {caller_ip}
#   sg:creator      : git email or $USER
#   sg:section      : podman
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.aws.Stack__Naming                            import Stack__Naming


TAG_PURPOSE_KEY     = 'sg:purpose'
TAG_PURPOSE_VALUE   = 'podman'
TAG_STACK_NAME_KEY  = 'sg:stack-name'
TAG_ALLOWED_IP_KEY  = 'sg:allowed-ip'
TAG_CREATOR_KEY     = 'sg:creator'
TAG_SECTION_KEY     = 'sg:section'
TAG_SECTION_VALUE   = 'podman'


PODMAN_NAMING = Stack__Naming(section_prefix='podman')                              # AWS Name tag carries 'podman-' prefix; never doubled


class Podman__AWS__Client(Type_Safe):
    sg       : object = None                                                        # Podman__SG__Helper       (lazy via setup())
    ami      : object = None                                                        # Podman__AMI__Helper      (lazy via setup())
    instance : object = None                                                        # Podman__Instance__Helper (lazy via setup())
    tags     : object = None                                                        # Podman__Tags__Builder    (lazy via setup())
    launch   : object = None                                                        # Podman__Launch__Helper   (lazy via setup())

    def setup(self) -> 'Podman__AWS__Client':
        from sgraph_ai_service_playwright__cli.podman.service.Podman__SG__Helper       import Podman__SG__Helper
        from sgraph_ai_service_playwright__cli.podman.service.Podman__AMI__Helper      import Podman__AMI__Helper
        from sgraph_ai_service_playwright__cli.podman.service.Podman__Instance__Helper import Podman__Instance__Helper
        from sgraph_ai_service_playwright__cli.podman.service.Podman__Launch__Helper   import Podman__Launch__Helper
        from sgraph_ai_service_playwright__cli.podman.service.Podman__Tags__Builder    import Podman__Tags__Builder
        self.sg       = Podman__SG__Helper      ()
        self.ami      = Podman__AMI__Helper     ()
        self.instance = Podman__Instance__Helper()
        self.tags     = Podman__Tags__Builder   ()
        self.launch   = Podman__Launch__Helper  ()
        return self
