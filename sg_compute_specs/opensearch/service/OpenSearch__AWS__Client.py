# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — OpenSearch: OpenSearch__AWS__Client
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.opensearch.service.OpenSearch__AMI__Helper                   import OpenSearch__AMI__Helper
from sg_compute_specs.opensearch.service.OpenSearch__Instance__Helper              import OpenSearch__Instance__Helper
from sg_compute_specs.opensearch.service.OpenSearch__Launch__Helper                import OpenSearch__Launch__Helper
from sg_compute_specs.opensearch.service.OpenSearch__SG__Helper                    import OpenSearch__SG__Helper
from sg_compute_specs.opensearch.service.OpenSearch__Tags__Builder                 import OpenSearch__Tags__Builder
from sg_compute_specs.opensearch.service.OpenSearch__Tags                          import (OS_NAMING            ,
                                                                                            TAG_ALLOWED_IP_KEY   ,
                                                                                            TAG_CREATOR_KEY      ,
                                                                                            TAG_PURPOSE_KEY      ,
                                                                                            TAG_PURPOSE_VALUE    ,
                                                                                            TAG_SECTION_KEY      ,
                                                                                            TAG_SECTION_VALUE    ,
                                                                                            TAG_STACK_NAME_KEY   )


class OpenSearch__AWS__Client(Type_Safe):
    sg       : Optional[OpenSearch__SG__Helper]       = None
    ami      : Optional[OpenSearch__AMI__Helper]      = None
    instance : Optional[OpenSearch__Instance__Helper] = None
    tags     : Optional[OpenSearch__Tags__Builder]    = None
    launch   : Optional[OpenSearch__Launch__Helper]   = None

    def setup(self) -> 'OpenSearch__AWS__Client':
        self.sg       = OpenSearch__SG__Helper      ()
        self.ami      = OpenSearch__AMI__Helper     ()
        self.instance = OpenSearch__Instance__Helper()
        self.tags     = OpenSearch__Tags__Builder   ()
        self.launch   = OpenSearch__Launch__Helper  ()
        return self
