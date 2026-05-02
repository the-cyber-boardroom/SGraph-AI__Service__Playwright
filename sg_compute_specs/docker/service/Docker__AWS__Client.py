# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Docker: Docker__AWS__Client
# Composition shell for per-concern AWS helpers.
#
# Tag convention:
#   sg:purpose    : docker
#   sg:stack-name : {stack_name}
#   sg:allowed-ip : {caller_ip}
#   sg:creator    : git email or $USER
#   sg:section    : docker
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.aws.Stack__Naming                            import Stack__Naming


TAG_PURPOSE_KEY     = 'sg:purpose'
TAG_PURPOSE_VALUE   = 'docker'
TAG_STACK_NAME_KEY  = 'sg:stack-name'
TAG_ALLOWED_IP_KEY  = 'sg:allowed-ip'
TAG_CREATOR_KEY     = 'sg:creator'
TAG_SECTION_KEY     = 'sg:section'
TAG_SECTION_VALUE   = 'docker'


DOCKER_NAMING = Stack__Naming(section_prefix='docker')


class Docker__AWS__Client(Type_Safe):
    sg       : object = None
    ami      : object = None
    instance : object = None
    tags     : object = None
    launch   : object = None

    def setup(self) -> 'Docker__AWS__Client':
        from sg_compute_specs.docker.service.Docker__SG__Helper       import Docker__SG__Helper
        from sg_compute_specs.docker.service.Docker__AMI__Helper      import Docker__AMI__Helper
        from sg_compute_specs.docker.service.Docker__Instance__Helper import Docker__Instance__Helper
        from sg_compute_specs.docker.service.Docker__Launch__Helper   import Docker__Launch__Helper
        from sg_compute_specs.docker.service.Docker__Tags__Builder    import Docker__Tags__Builder
        self.sg       = Docker__SG__Helper      ()
        self.ami      = Docker__AMI__Helper     ()
        self.instance = Docker__Instance__Helper()
        self.tags     = Docker__Tags__Builder   ()
        self.launch   = Docker__Launch__Helper  ()
        return self
