# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode: Vscode__User_Data__Builder
# Composes Section__* fragments into a cloud-init bash script.
# Order: Base (incl. auto-terminate timer) → Docker → code-server container.
# The timer is baked into Section__Base so it fires even if a later step aborts.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute.platforms.ec2.user_data.Section__Base   import Section__Base
from sg_compute.platforms.ec2.user_data.Section__Docker import Section__Docker

from sg_compute_specs.vscode.enums.Enum__Vscode__Distribution import Enum__Vscode__Distribution
from sg_compute_specs.vscode.service.Vscode__Compose__Template import Vscode__Compose__Template
from sg_compute_specs.vscode.service.Vscode__Stack__Mapper     import EDITOR_PORT

FOOTER = ('\ntouch /var/lib/sg-compute-boot-ok\n'
          'echo "[sg-compute] vscode boot complete at $(date -u +%FT%TZ)"\n')


class Vscode__User_Data__Builder(Type_Safe):

    def render(self, stack_name   : str                        ,
                     region       : str                        ,
                     password     : str                        ,
                     distribution : Enum__Vscode__Distribution = Enum__Vscode__Distribution.CODE_SERVER,
                     max_hours    : float                      = 4.0) -> str:
        parts = [
            Section__Base()           .render(stack_name=stack_name, max_hours=max_hours) ,
            Section__Docker()         .render()                                           ,
            Vscode__Compose__Template().render(distribution=distribution                  ,
                                               password=password                          ,
                                               port=EDITOR_PORT)                          ,
        ]
        parts.append(FOOTER)
        return '\n'.join(p for p in parts if p)
