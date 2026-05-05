# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Neko: Neko__AWS__Client
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute.platforms.ec2.helpers.Stack__Naming                            import Stack__Naming

from typing import Optional


TAG_PURPOSE_KEY    = 'sg:purpose'
TAG_PURPOSE_VALUE  = 'neko'
TAG_STACK_NAME_KEY = 'sg:stack-name'
TAG_ALLOWED_IP_KEY = 'sg:allowed-ip'
TAG_CREATOR_KEY    = 'sg:creator'
TAG_SECTION_KEY    = 'sg:section'
TAG_SECTION_VALUE  = 'neko'

NEKO_NAMING = Stack__Naming(section_prefix='neko')


class Neko__AWS__Client(Type_Safe):
    sg       : Optional['Neko__SG__Helper']       = None
    ami      : Optional['Neko__AMI__Helper']      = None
    instance : Optional['Neko__Instance__Helper'] = None
    tags     : Optional['Neko__Tags__Builder']    = None
    launch   : Optional['Neko__Launch__Helper']   = None

    def setup(self) -> 'Neko__AWS__Client':
        from sg_compute_specs.neko.service.Neko__SG__Helper       import Neko__SG__Helper
        from sg_compute_specs.neko.service.Neko__AMI__Helper      import Neko__AMI__Helper
        from sg_compute_specs.neko.service.Neko__Instance__Helper import Neko__Instance__Helper
        from sg_compute_specs.neko.service.Neko__Launch__Helper   import Neko__Launch__Helper
        from sg_compute_specs.neko.service.Neko__Tags__Builder    import Neko__Tags__Builder
        self.sg       = Neko__SG__Helper      ()
        self.ami      = Neko__AMI__Helper     ()
        self.instance = Neko__Instance__Helper()
        self.tags     = Neko__Tags__Builder   ()
        self.launch   = Neko__Launch__Helper  ()
        return self
