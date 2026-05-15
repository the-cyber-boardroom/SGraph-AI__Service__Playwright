# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Playwright__Tags__Builder
# Builds the tag list applied to every EC2 instance + SG created for a
# Playwright stack. Pure mapper, no AWS calls. Mirrors Vnc__Tags__Builder.
# Adds an `sg:with-mitmproxy` tag so `sp playwright info` can report the
# mitmproxy opt-in flag without re-reading user-data.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                      import List

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.playwright.primitives.Safe_Str__IP__Address    import Safe_Str__IP__Address
from sgraph_ai_service_playwright__cli.playwright.primitives.Safe_Str__Playwright__Stack__Name import Safe_Str__Playwright__Stack__Name
from sgraph_ai_service_playwright__cli.playwright.service.Playwright__AWS__Client     import (TAG_ALLOWED_IP_KEY      ,
                                                                                               TAG_CREATOR_KEY         ,
                                                                                               TAG_PURPOSE_KEY         ,
                                                                                               TAG_PURPOSE_VALUE       ,
                                                                                               TAG_SECTION_KEY         ,
                                                                                               TAG_SECTION_VALUE       ,
                                                                                               TAG_STACK_NAME_KEY      ,
                                                                                               TAG_WITH_MITMPROXY_KEY  ,
                                                                                               PLAYWRIGHT_NAMING       )


class Playwright__Tags__Builder(Type_Safe):

    def build(self, stack_name    : Safe_Str__Playwright__Stack__Name,
                    caller_ip     : Safe_Str__IP__Address            ,
                    creator       : str  = ''                        ,
                    with_mitmproxy: bool = False                     ) -> List[dict]:
        return [{'Key': 'Name'                  , 'Value': PLAYWRIGHT_NAMING.aws_name_for_stack(stack_name)},
                {'Key': TAG_PURPOSE_KEY         , 'Value': TAG_PURPOSE_VALUE                               },
                {'Key': TAG_SECTION_KEY         , 'Value': TAG_SECTION_VALUE                               },
                {'Key': TAG_STACK_NAME_KEY      , 'Value': str(stack_name)                                 },
                {'Key': TAG_ALLOWED_IP_KEY      , 'Value': str(caller_ip)                                  },
                {'Key': TAG_CREATOR_KEY         , 'Value': str(creator) or 'unknown'                       },
                {'Key': TAG_WITH_MITMPROXY_KEY  , 'Value': 'true' if with_mitmproxy else 'false'           }]
