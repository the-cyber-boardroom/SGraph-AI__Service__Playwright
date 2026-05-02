# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Neko: Neko__Tags__Builder
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.neko.primitives.Safe_Str__IP__Address                         import Safe_Str__IP__Address
from sg_compute_specs.neko.primitives.Safe_Str__Neko__Stack__Name                   import Safe_Str__Neko__Stack__Name
from sg_compute_specs.neko.service.Neko__AWS__Client                                import (TAG_ALLOWED_IP_KEY ,
                                                                                             TAG_CREATOR_KEY    ,
                                                                                             TAG_PURPOSE_KEY    ,
                                                                                             TAG_PURPOSE_VALUE  ,
                                                                                             TAG_SECTION_KEY    ,
                                                                                             TAG_SECTION_VALUE  ,
                                                                                             TAG_STACK_NAME_KEY ,
                                                                                             NEKO_NAMING        )


class Neko__Tags__Builder(Type_Safe):

    def build(self, stack_name: Safe_Str__Neko__Stack__Name,
                    caller_ip : Safe_Str__IP__Address      ,
                    creator   : str = '') -> List[dict]:
        return [{'Key': 'Name'             , 'Value': NEKO_NAMING.aws_name_for_stack(stack_name)},
                {'Key': TAG_PURPOSE_KEY    , 'Value': TAG_PURPOSE_VALUE                         },
                {'Key': TAG_SECTION_KEY    , 'Value': TAG_SECTION_VALUE                         },
                {'Key': TAG_STACK_NAME_KEY , 'Value': str(stack_name)                           },
                {'Key': TAG_ALLOWED_IP_KEY , 'Value': str(caller_ip)                            },
                {'Key': TAG_CREATOR_KEY    , 'Value': str(creator) or 'unknown'                 }]
