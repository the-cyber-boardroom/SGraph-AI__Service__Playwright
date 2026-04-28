# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Linux__AWS__Client
# Composition shell for the per-concern AWS helpers (SG / AMI / Instance /
# Tags / Launch). Mirrors OpenSearch__AWS__Client. Owns the tag-key constants
# and the LINUX_NAMING binding.
#
# Tag convention (mirrors opensearch + elastic):
#   sg:purpose      : linux
#   sg:stack-name   : {stack_name}
#   sg:allowed-ip   : {caller_ip}
#   sg:creator      : git email or $USER
#   sg:section      : linux
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.aws.Stack__Naming                            import Stack__Naming


TAG_PURPOSE_KEY     = 'sg:purpose'
TAG_PURPOSE_VALUE   = 'linux'
TAG_STACK_NAME_KEY  = 'sg:stack-name'
TAG_ALLOWED_IP_KEY  = 'sg:allowed-ip'
TAG_CREATOR_KEY     = 'sg:creator'
TAG_SECTION_KEY     = 'sg:section'
TAG_SECTION_VALUE   = 'linux'


LINUX_NAMING = Stack__Naming(section_prefix='linux')                                # AWS Name tag carries 'linux-' prefix; never doubled


class Linux__AWS__Client(Type_Safe):
    sg       : object = None                                                        # Linux__SG__Helper       (lazy via setup())
    ami      : object = None                                                        # Linux__AMI__Helper      (lazy via setup())
    instance : object = None                                                        # Linux__Instance__Helper (lazy via setup())
    tags     : object = None                                                        # Linux__Tags__Builder    (lazy via setup())
    launch   : object = None                                                        # Linux__Launch__Helper   (lazy via setup())

    def setup(self) -> 'Linux__AWS__Client':
        from sgraph_ai_service_playwright__cli.linux.service.Linux__SG__Helper       import Linux__SG__Helper
        from sgraph_ai_service_playwright__cli.linux.service.Linux__AMI__Helper      import Linux__AMI__Helper
        from sgraph_ai_service_playwright__cli.linux.service.Linux__Instance__Helper import Linux__Instance__Helper
        from sgraph_ai_service_playwright__cli.linux.service.Linux__Launch__Helper   import Linux__Launch__Helper
        from sgraph_ai_service_playwright__cli.linux.service.Linux__Tags__Builder    import Linux__Tags__Builder
        self.sg       = Linux__SG__Helper      ()
        self.ami      = Linux__AMI__Helper     ()
        self.instance = Linux__Instance__Helper()
        self.tags     = Linux__Tags__Builder   ()
        self.launch   = Linux__Launch__Helper  ()
        return self
