# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Neko__AWS__Client
# Composition shell for the per-concern AWS helpers (SG / AMI / Instance /
# Tags / Launch). Owns the tag-key constants and NEKO_NAMING binding.
#
# Tag convention (mirrors VNC):
#   sg:purpose    : neko
#   sg:stack-name : {stack_name}
#   sg:allowed-ip : {caller_ip}
#   sg:creator    : git email or $USER
#   sg:section    : neko
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.aws.Stack__Naming                            import Stack__Naming


TAG_PURPOSE_KEY   = 'sg:purpose'
TAG_PURPOSE_VALUE = 'neko'
TAG_STACK_NAME_KEY= 'sg:stack-name'
TAG_ALLOWED_IP_KEY= 'sg:allowed-ip'
TAG_CREATOR_KEY   = 'sg:creator'
TAG_SECTION_KEY   = 'sg:section'
TAG_SECTION_VALUE = 'neko'

NEKO_NAMING = Stack__Naming(section_prefix='neko')


class Neko__AWS__Client(Type_Safe):
    sg       : object = None                                                        # Neko__SG__Helper
    ami      : object = None                                                        # Neko__AMI__Helper
    instance : object = None                                                        # Neko__Instance__Helper
    tags     : object = None                                                        # Neko__Tags__Builder
    launch   : object = None                                                        # Neko__Launch__Helper

    def setup(self) -> 'Neko__AWS__Client':
        from sgraph_ai_service_playwright__cli.neko.service.Neko__SG__Helper       import Neko__SG__Helper
        from sgraph_ai_service_playwright__cli.neko.service.Neko__AMI__Helper      import Neko__AMI__Helper
        from sgraph_ai_service_playwright__cli.neko.service.Neko__Instance__Helper import Neko__Instance__Helper
        from sgraph_ai_service_playwright__cli.neko.service.Neko__Launch__Helper   import Neko__Launch__Helper
        from sgraph_ai_service_playwright__cli.neko.service.Neko__Tags__Builder    import Neko__Tags__Builder
        self.sg       = Neko__SG__Helper      ()
        self.ami      = Neko__AMI__Helper     ()
        self.instance = Neko__Instance__Helper()
        self.tags     = Neko__Tags__Builder   ()
        self.launch   = Neko__Launch__Helper  ()
        return self
