# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — VNC: Vnc__Tags__Builder
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.vnc.enums.Enum__Vnc__Interceptor__Kind                        import Enum__Vnc__Interceptor__Kind
from sg_compute_specs.vnc.primitives.Safe_Str__IP__Address                          import Safe_Str__IP__Address
from sg_compute_specs.vnc.primitives.Safe_Str__Vnc__Stack__Name                     import Safe_Str__Vnc__Stack__Name
from sg_compute_specs.vnc.schemas.Schema__Vnc__Interceptor__Choice                  import Schema__Vnc__Interceptor__Choice
from sg_compute_specs.vnc.service.Vnc__Tags                                  import (TAG_ALLOWED_IP_KEY   ,
                                                                                              TAG_CREATOR_KEY      ,
                                                                                              TAG_INTERCEPTOR_KEY  ,
                                                                                              TAG_INTERCEPTOR_NONE ,
                                                                                              TAG_PURPOSE_KEY      ,
                                                                                              TAG_PURPOSE_VALUE    ,
                                                                                              TAG_SECTION_KEY      ,
                                                                                              TAG_SECTION_VALUE    ,
                                                                                              TAG_STACK_NAME_KEY   ,
                                                                                              VNC_NAMING           )


def _interceptor_tag_value(choice: Schema__Vnc__Interceptor__Choice) -> str:
    if choice.kind == Enum__Vnc__Interceptor__Kind.NAME:
        return f'name:{str(choice.name)}'
    if choice.kind == Enum__Vnc__Interceptor__Kind.INLINE:
        return 'inline'
    return TAG_INTERCEPTOR_NONE


class Vnc__Tags__Builder(Type_Safe):

    def build(self, stack_name : Safe_Str__Vnc__Stack__Name           ,
                    caller_ip  : Safe_Str__IP__Address                ,
                    creator    : str = ''                             ,
                    interceptor: Schema__Vnc__Interceptor__Choice = None) -> List[dict]:
        choice = interceptor or Schema__Vnc__Interceptor__Choice()
        return [{'Key': 'Name'             , 'Value': VNC_NAMING.aws_name_for_stack(stack_name)},
                {'Key': TAG_PURPOSE_KEY    , 'Value': TAG_PURPOSE_VALUE                        },
                {'Key': TAG_SECTION_KEY    , 'Value': TAG_SECTION_VALUE                        },
                {'Key': TAG_STACK_NAME_KEY , 'Value': str(stack_name)                          },
                {'Key': TAG_ALLOWED_IP_KEY , 'Value': str(caller_ip)                           },
                {'Key': TAG_CREATOR_KEY    , 'Value': str(creator) or 'unknown'                },
                {'Key': TAG_INTERCEPTOR_KEY, 'Value': _interceptor_tag_value(choice)           }]
