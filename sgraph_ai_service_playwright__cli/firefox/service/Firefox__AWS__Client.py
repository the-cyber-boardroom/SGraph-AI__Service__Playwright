# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Firefox__AWS__Client
# Composition shell for the per-concern AWS helpers (SG / AMI / Instance /
# Tags / Launch). Owns the tag-key constants and FIREFOX_NAMING binding.
#
# Tag convention:
#   sg:purpose    : firefox
#   sg:stack-name : {stack_name}
#   sg:allowed-ip : {caller_ip}
#   sg:creator    : git email or $USER
#   sg:section    : firefox
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.aws.Stack__Naming                            import Stack__Naming


TAG_PURPOSE_KEY   = 'sg:purpose'
TAG_PURPOSE_VALUE = 'firefox'
TAG_STACK_NAME_KEY= 'sg:stack-name'
TAG_ALLOWED_IP_KEY= 'sg:allowed-ip'
TAG_CREATOR_KEY   = 'sg:creator'
TAG_SECTION_KEY   = 'sg:section'
TAG_SECTION_VALUE = 'firefox'

FIREFOX_NAMING = Stack__Naming(section_prefix='firefox')


class Firefox__AWS__Client(Type_Safe):
    sg       : object = None                                                        # Firefox__SG__Helper
    ami      : object = None                                                        # Firefox__AMI__Helper
    instance : object = None                                                        # Firefox__Instance__Helper
    tags     : object = None                                                        # Firefox__Tags__Builder
    launch   : object = None                                                        # Firefox__Launch__Helper
    lt       : object = None                                                        # Firefox__Launch_Template__Helper
    ssm      : object = None                                                        # Firefox__SSM__Helper
    iam      : object = None                                                        # Firefox__IAM__Helper

    def setup(self) -> 'Firefox__AWS__Client':
        from sgraph_ai_service_playwright__cli.firefox.service.Firefox__SG__Helper              import Firefox__SG__Helper
        from sgraph_ai_service_playwright__cli.firefox.service.Firefox__AMI__Helper             import Firefox__AMI__Helper
        from sgraph_ai_service_playwright__cli.firefox.service.Firefox__Instance__Helper        import Firefox__Instance__Helper
        from sgraph_ai_service_playwright__cli.firefox.service.Firefox__Launch__Helper          import Firefox__Launch__Helper
        from sgraph_ai_service_playwright__cli.firefox.service.Firefox__Launch_Template__Helper import Firefox__Launch_Template__Helper
        from sgraph_ai_service_playwright__cli.firefox.service.Firefox__Tags__Builder           import Firefox__Tags__Builder
        from sgraph_ai_service_playwright__cli.firefox.service.Firefox__SSM__Helper             import Firefox__SSM__Helper
        from sgraph_ai_service_playwright__cli.firefox.service.Firefox__IAM__Helper             import Firefox__IAM__Helper
        self.sg       = Firefox__SG__Helper             ()
        self.ami      = Firefox__AMI__Helper            ()
        self.instance = Firefox__Instance__Helper       ()
        self.tags     = Firefox__Tags__Builder          ()
        self.launch   = Firefox__Launch__Helper         ()
        self.lt       = Firefox__Launch_Template__Helper()
        self.ssm      = Firefox__SSM__Helper            ()
        self.iam      = Firefox__IAM__Helper            ()
        return self
