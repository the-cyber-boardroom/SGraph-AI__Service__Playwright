# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Open_Design__AWS__Client
# Composition shell wiring the per-concern AWS helpers for the open-design stack.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.platforms.ec2.helpers.EC2__AMI__Helper      import EC2__AMI__Helper
from sg_compute.platforms.ec2.helpers.EC2__Instance__Helper import EC2__Instance__Helper
from sg_compute.platforms.ec2.helpers.EC2__Launch__Helper   import EC2__Launch__Helper
from sg_compute.platforms.ec2.helpers.EC2__SG__Helper       import EC2__SG__Helper
from sg_compute.platforms.ec2.helpers.EC2__Tags__Builder    import EC2__Tags__Builder
from sg_compute.platforms.ec2.helpers.Stack__Naming         import Stack__Naming

STACK_TYPE   = 'open-design'
OD_NAMING    = Stack__Naming(section_prefix='od')


class Open_Design__AWS__Client(Type_Safe):
    sg       : object = None    # EC2__SG__Helper
    ami      : object = None    # EC2__AMI__Helper
    instance : object = None    # EC2__Instance__Helper
    tags     : object = None    # EC2__Tags__Builder
    launch   : object = None    # EC2__Launch__Helper

    def setup(self) -> 'Open_Design__AWS__Client':
        self.sg       = EC2__SG__Helper      ().setup(OD_NAMING)
        self.ami      = EC2__AMI__Helper      ()
        self.instance = EC2__Instance__Helper ()
        self.tags     = EC2__Tags__Builder    (stack_type=STACK_TYPE)
        self.launch   = EC2__Launch__Helper   ()
        return self
