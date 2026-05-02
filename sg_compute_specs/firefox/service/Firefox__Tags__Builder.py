# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Firefox: Firefox__Tags__Builder
# Pure mapper — no AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.firefox.service.Firefox__AWS__Client                          import (FIREFOX_NAMING     ,
                                                                                             TAG_ALLOWED_IP_KEY ,
                                                                                             TAG_CREATOR_KEY    ,
                                                                                             TAG_PURPOSE_KEY    ,
                                                                                             TAG_PURPOSE_VALUE  ,
                                                                                             TAG_SECTION_KEY    ,
                                                                                             TAG_SECTION_VALUE  ,
                                                                                             TAG_STACK_NAME_KEY )


class Firefox__Tags__Builder(Type_Safe):

    def build(self, stack_name: str, caller_ip: str, creator: str = '') -> List[dict]:
        return [{'Key': 'Name'            , 'Value': FIREFOX_NAMING.aws_name_for_stack(stack_name)},
                {'Key': TAG_PURPOSE_KEY   , 'Value': TAG_PURPOSE_VALUE                            },
                {'Key': TAG_SECTION_KEY   , 'Value': TAG_SECTION_VALUE                            },
                {'Key': TAG_STACK_NAME_KEY, 'Value': str(stack_name)                              },
                {'Key': TAG_ALLOWED_IP_KEY, 'Value': str(caller_ip)                               },
                {'Key': TAG_CREATOR_KEY   , 'Value': str(creator) or 'unknown'                    }]
