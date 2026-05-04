# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Prometheus__Tags__Builder
# Builds the tag list applied to every EC2 instance + SG created for a
# Prometheus stack. Single responsibility: tag-spec construction. No AWS
# calls, fully testable as a pure mapper.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import List

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.prometheus.primitives.Safe_Str__IP__Address  import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.prometheus.primitives.Safe_Str__Prom__Stack__Name import Safe_Str__Prom__Stack__Name
from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__AWS__Client   import (PROM_NAMING            ,
                                                                                              TAG_ALLOWED_IP_KEY     ,
                                                                                              TAG_CREATOR_KEY        ,
                                                                                              TAG_PURPOSE_KEY        ,
                                                                                              TAG_PURPOSE_VALUE      ,
                                                                                              TAG_SECTION_KEY        ,
                                                                                              TAG_SECTION_VALUE      ,
                                                                                              TAG_STACK_NAME_KEY     )


class Prometheus__Tags__Builder(Type_Safe):

    def build(self, stack_name: Safe_Str__Prom__Stack__Name, caller_ip: Safe_Str__IP__Address, creator: str = '') -> List[dict]:
        return [{'Key': 'Name'                , 'Value': PROM_NAMING.aws_name_for_stack(stack_name)}, # Name tag carries 'prometheus-' prefix; never doubled
                {'Key': TAG_PURPOSE_KEY       , 'Value': TAG_PURPOSE_VALUE                         },
                {'Key': TAG_SECTION_KEY       , 'Value': TAG_SECTION_VALUE                         },
                {'Key': TAG_STACK_NAME_KEY    , 'Value': str(stack_name)                           },
                {'Key': TAG_ALLOWED_IP_KEY    , 'Value': str(caller_ip)                            },
                {'Key': TAG_CREATOR_KEY       , 'Value': str(creator) or 'unknown'                 }]
