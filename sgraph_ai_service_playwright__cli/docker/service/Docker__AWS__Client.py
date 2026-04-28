# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Docker__AWS__Client
# Composition shell for the per-concern AWS helpers (SG / AMI / Instance /
# Tags / Launch). Mirrors Linux__AWS__Client.
#
# Tag convention:
#   sg:purpose      : docker
#   sg:stack-name   : {stack_name}
#   sg:allowed-ip   : {caller_ip}
#   sg:creator      : git email or $USER
#   sg:section      : docker
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


DOCKER_NAMING = Stack__Naming(section_prefix='docker')                              # AWS Name tag carries 'docker-' prefix; never doubled


class Docker__AWS__Client(Type_Safe):
    sg       : object = None                                                        # Docker__SG__Helper       (lazy via setup())
    ami      : object = None                                                        # Docker__AMI__Helper      (lazy via setup())
    instance : object = None                                                        # Docker__Instance__Helper (lazy via setup())
    tags     : object = None                                                        # Docker__Tags__Builder    (lazy via setup())
    launch   : object = None                                                        # Docker__Launch__Helper   (lazy via setup())

    def setup(self) -> 'Docker__AWS__Client':
        from sgraph_ai_service_playwright__cli.docker.service.Docker__SG__Helper       import Docker__SG__Helper
        from sgraph_ai_service_playwright__cli.docker.service.Docker__AMI__Helper      import Docker__AMI__Helper
        from sgraph_ai_service_playwright__cli.docker.service.Docker__Instance__Helper import Docker__Instance__Helper
        from sgraph_ai_service_playwright__cli.docker.service.Docker__Launch__Helper   import Docker__Launch__Helper
        from sgraph_ai_service_playwright__cli.docker.service.Docker__Tags__Builder    import Docker__Tags__Builder
        self.sg       = Docker__SG__Helper      ()
        self.ami      = Docker__AMI__Helper     ()
        self.instance = Docker__Instance__Helper()
        self.tags     = Docker__Tags__Builder   ()
        self.launch   = Docker__Launch__Helper  ()
        return self
