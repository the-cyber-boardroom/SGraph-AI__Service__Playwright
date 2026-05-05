# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — OpenSearch: OpenSearch__AWS__Client
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute.platforms.ec2.helpers.Stack__Naming                            import Stack__Naming


TAG_PURPOSE_KEY    = 'sg:purpose'
TAG_PURPOSE_VALUE  = 'opensearch'
TAG_STACK_NAME_KEY = 'sg:stack-name'
TAG_ALLOWED_IP_KEY = 'sg:allowed-ip'
TAG_CREATOR_KEY    = 'sg:creator'
TAG_SECTION_KEY    = 'sg:section'
TAG_SECTION_VALUE  = 'os'

OS_NAMING = Stack__Naming(section_prefix='opensearch')


class OpenSearch__AWS__Client(Type_Safe):
    sg       : object = None
    ami      : object = None
    instance : object = None
    tags     : object = None
    launch   : object = None

    def setup(self) -> 'OpenSearch__AWS__Client':
        from sg_compute_specs.opensearch.service.OpenSearch__SG__Helper       import OpenSearch__SG__Helper
        from sg_compute_specs.opensearch.service.OpenSearch__AMI__Helper      import OpenSearch__AMI__Helper
        from sg_compute_specs.opensearch.service.OpenSearch__Instance__Helper import OpenSearch__Instance__Helper
        from sg_compute_specs.opensearch.service.OpenSearch__Launch__Helper   import OpenSearch__Launch__Helper
        from sg_compute_specs.opensearch.service.OpenSearch__Tags__Builder    import OpenSearch__Tags__Builder
        self.sg       = OpenSearch__SG__Helper      ()
        self.ami      = OpenSearch__AMI__Helper     ()
        self.instance = OpenSearch__Instance__Helper()
        self.tags     = OpenSearch__Tags__Builder   ()
        self.launch   = OpenSearch__Launch__Helper  ()
        return self
