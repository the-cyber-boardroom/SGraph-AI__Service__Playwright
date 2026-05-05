# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — VNC: Vnc__AWS__Client
# Tag convention:
#   sg:purpose     : vnc
#   sg:stack-name  : {stack_name}
#   sg:allowed-ip  : {caller_ip}
#   sg:creator     : git email or $USER
#   sg:section     : vnc
#   sg:interceptor : <name | inline | none>
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute.platforms.ec2.helpers.Stack__Naming                            import Stack__Naming


TAG_PURPOSE_KEY      = 'sg:purpose'
TAG_PURPOSE_VALUE    = 'vnc'
TAG_STACK_NAME_KEY   = 'sg:stack-name'
TAG_ALLOWED_IP_KEY   = 'sg:allowed-ip'
TAG_CREATOR_KEY      = 'sg:creator'
TAG_SECTION_KEY      = 'sg:section'
TAG_SECTION_VALUE    = 'vnc'
TAG_INTERCEPTOR_KEY  = 'sg:interceptor'
TAG_INTERCEPTOR_NONE = 'none'


VNC_NAMING = Stack__Naming(section_prefix='vnc')


class Vnc__AWS__Client(Type_Safe):
    sg       : object = None
    ami      : object = None
    instance : object = None
    tags     : object = None
    launch   : object = None

    def setup(self) -> 'Vnc__AWS__Client':
        from sg_compute_specs.vnc.service.Vnc__SG__Helper       import Vnc__SG__Helper
        from sg_compute_specs.vnc.service.Vnc__AMI__Helper      import Vnc__AMI__Helper
        from sg_compute_specs.vnc.service.Vnc__Instance__Helper import Vnc__Instance__Helper
        from sg_compute_specs.vnc.service.Vnc__Launch__Helper   import Vnc__Launch__Helper
        from sg_compute_specs.vnc.service.Vnc__Tags__Builder    import Vnc__Tags__Builder
        self.sg       = Vnc__SG__Helper      ()
        self.ami      = Vnc__AMI__Helper     ()
        self.instance = Vnc__Instance__Helper()
        self.tags     = Vnc__Tags__Builder   ()
        self.launch   = Vnc__Launch__Helper  ()
        return self
