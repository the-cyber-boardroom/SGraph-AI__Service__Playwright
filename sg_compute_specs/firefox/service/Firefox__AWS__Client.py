# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Firefox: Firefox__AWS__Client
# Composition shell: tag constants, FIREFOX_NAMING, and helper slots.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.aws.Stack__Naming                            import Stack__Naming


TAG_PURPOSE_KEY    = 'sg:purpose'
TAG_PURPOSE_VALUE  = 'firefox'
TAG_STACK_NAME_KEY = 'sg:stack-name'
TAG_ALLOWED_IP_KEY = 'sg:allowed-ip'
TAG_CREATOR_KEY    = 'sg:creator'
TAG_SECTION_KEY    = 'sg:section'
TAG_SECTION_VALUE  = 'firefox'

FIREFOX_NAMING = Stack__Naming(section_prefix='firefox')


class Firefox__AWS__Client(Type_Safe):
    sg       : object = None
    instance : object = None
    tags     : object = None
    launch   : object = None
    iam      : object = None

    def setup(self) -> 'Firefox__AWS__Client':
        from sg_compute_specs.firefox.service.Firefox__SG__Helper       import Firefox__SG__Helper
        from sg_compute_specs.firefox.service.Firefox__Instance__Helper  import Firefox__Instance__Helper
        from sg_compute_specs.firefox.service.Firefox__Launch__Helper    import Firefox__Launch__Helper
        from sg_compute_specs.firefox.service.Firefox__Tags__Builder     import Firefox__Tags__Builder
        from sg_compute_specs.firefox.service.Firefox__IAM__Helper       import Firefox__IAM__Helper
        self.sg       = Firefox__SG__Helper      ()
        self.instance = Firefox__Instance__Helper()
        self.launch   = Firefox__Launch__Helper  ()
        self.tags     = Firefox__Tags__Builder   ()
        self.iam      = Firefox__IAM__Helper     ()
        return self
