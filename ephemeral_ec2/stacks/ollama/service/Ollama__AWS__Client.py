# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Ollama__AWS__Client
# Composition shell wiring the per-concern AWS helpers for the ollama stack.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from ephemeral_ec2.helpers.aws.EC2__AMI__Helper      import EC2__AMI__Helper
from ephemeral_ec2.helpers.aws.EC2__Instance__Helper import EC2__Instance__Helper
from ephemeral_ec2.helpers.aws.EC2__Launch__Helper   import EC2__Launch__Helper
from ephemeral_ec2.helpers.aws.EC2__SG__Helper       import EC2__SG__Helper
from ephemeral_ec2.helpers.aws.EC2__Tags__Builder    import EC2__Tags__Builder
from ephemeral_ec2.helpers.aws.Stack__Naming         import Stack__Naming

from ephemeral_ec2.stacks.ollama.service.Ollama__Stack__Mapper import STACK_TYPE

OL_NAMING = Stack__Naming(section_prefix='ol')


class Ollama__AWS__Client(Type_Safe):
    sg       : object = None    # EC2__SG__Helper
    ami      : object = None    # EC2__AMI__Helper
    instance : object = None    # EC2__Instance__Helper
    tags     : object = None    # EC2__Tags__Builder
    launch   : object = None    # EC2__Launch__Helper

    def setup(self) -> 'Ollama__AWS__Client':
        self.sg       = EC2__SG__Helper      ().setup(OL_NAMING)
        self.ami      = EC2__AMI__Helper      ()
        self.instance = EC2__Instance__Helper ()
        self.tags     = EC2__Tags__Builder    (stack_type=STACK_TYPE)
        self.launch   = EC2__Launch__Helper   ()
        return self
