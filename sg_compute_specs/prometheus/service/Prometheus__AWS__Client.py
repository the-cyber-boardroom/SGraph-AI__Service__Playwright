# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Prometheus: Prometheus__AWS__Client
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Optional

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.prometheus.service.Prometheus__AMI__Helper                   import Prometheus__AMI__Helper
from sg_compute_specs.prometheus.service.Prometheus__Instance__Helper              import Prometheus__Instance__Helper
from sg_compute_specs.prometheus.service.Prometheus__Launch__Helper                import Prometheus__Launch__Helper
from sg_compute_specs.prometheus.service.Prometheus__SG__Helper                    import Prometheus__SG__Helper
from sg_compute_specs.prometheus.service.Prometheus__Tags__Builder                 import Prometheus__Tags__Builder
from sg_compute_specs.prometheus.service.Prometheus__Tags                          import (PROM_NAMING         ,
                                                                                            TAG_ALLOWED_IP_KEY  ,
                                                                                            TAG_CREATOR_KEY     ,
                                                                                            TAG_PURPOSE_KEY     ,
                                                                                            TAG_PURPOSE_VALUE   ,
                                                                                            TAG_SECTION_KEY     ,
                                                                                            TAG_SECTION_VALUE   ,
                                                                                            TAG_STACK_NAME_KEY  )


class Prometheus__AWS__Client(Type_Safe):
    sg       : Optional[Prometheus__SG__Helper]       = None
    ami      : Optional[Prometheus__AMI__Helper]      = None
    instance : Optional[Prometheus__Instance__Helper] = None
    tags     : Optional[Prometheus__Tags__Builder]    = None
    launch   : Optional[Prometheus__Launch__Helper]   = None

    def setup(self) -> 'Prometheus__AWS__Client':
        self.sg       = Prometheus__SG__Helper      ()
        self.ami      = Prometheus__AMI__Helper     ()
        self.instance = Prometheus__Instance__Helper()
        self.tags     = Prometheus__Tags__Builder   ()
        self.launch   = Prometheus__Launch__Helper  ()
        return self
