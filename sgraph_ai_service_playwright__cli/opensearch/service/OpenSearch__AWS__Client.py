# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — OpenSearch__AWS__Client
# Composition shell for the per-concern AWS helpers (SG / AMI / Instance /
# Tags). Mirrors the Elastic__AWS__Client + Ec2__AWS__Client patterns but
# splits each responsibility into its own small file (one class per file
# per CLAUDE.md rule #21). Owns the tag-key constants and the OS_NAMING
# binding to keep the section's AWS surface in one shared header.
#
# Tag convention (mirrors elastic + ec2):
#   sg:purpose      : opensearch
#   sg:stack-name   : {stack_name}                 ← logical name lookup
#   sg:allowed-ip   : {caller_ip}                  ← records what /32 was set
#   sg:creator      : git email or $USER
#   sg:section      : os
#
# Plan reference:
#   team/comms/plans/v0.1.96__playwright-stack-split__04__sp-os__opensearch.md
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.aws.Stack__Naming                            import Stack__Naming


TAG_PURPOSE_KEY     = 'sg:purpose'
TAG_PURPOSE_VALUE   = 'opensearch'
TAG_STACK_NAME_KEY  = 'sg:stack-name'
TAG_ALLOWED_IP_KEY  = 'sg:allowed-ip'
TAG_CREATOR_KEY     = 'sg:creator'
TAG_SECTION_KEY     = 'sg:section'
TAG_SECTION_VALUE   = 'os'


OS_NAMING = Stack__Naming(section_prefix='opensearch')                              # AWS Name tag carries 'opensearch-' prefix; never doubled


class OpenSearch__AWS__Client(Type_Safe):                                           # Composes the per-concern helpers — kept small on purpose
    sg       : object = None                                                        # OpenSearch__SG__Helper       (lazy via setup())
    ami      : object = None                                                        # OpenSearch__AMI__Helper      (lazy via setup())
    instance : object = None                                                        # OpenSearch__Instance__Helper (lazy via setup())
    tags     : object = None                                                        # OpenSearch__Tags__Builder    (lazy via setup())
    launch   : object = None                                                        # OpenSearch__Launch__Helper   (lazy via setup())

    def setup(self) -> 'OpenSearch__AWS__Client':                                   # Lazy import — avoids circular module-load when callers import the client first
        from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__SG__Helper       import OpenSearch__SG__Helper
        from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__AMI__Helper      import OpenSearch__AMI__Helper
        from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__Instance__Helper import OpenSearch__Instance__Helper
        from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__Launch__Helper   import OpenSearch__Launch__Helper
        from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__Tags__Builder    import OpenSearch__Tags__Builder
        self.sg       = OpenSearch__SG__Helper      ()
        self.ami      = OpenSearch__AMI__Helper     ()
        self.instance = OpenSearch__Instance__Helper()
        self.tags     = OpenSearch__Tags__Builder   ()
        self.launch   = OpenSearch__Launch__Helper  ()
        return self
