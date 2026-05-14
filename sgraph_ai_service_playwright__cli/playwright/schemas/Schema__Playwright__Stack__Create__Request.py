# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Playwright__Stack__Create__Request
# Inputs for `sp playwright create [NAME]`. POD backend: the stack is one
# diniscruz/sg-playwright container started on a host via the host-plane
# pods API.
#
# host_url + host_api_key locate + authenticate the target host control
# plane. api_key is the FAST_API__AUTH__API_KEY__VALUE baked into the
# launched Playwright pod's environment.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text         import Safe_Str__Text
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url             import Safe_Str__Url

from sgraph_ai_service_playwright__cli.playwright.primitives.Safe_Str__Playwright__Stack__Name import Safe_Str__Playwright__Stack__Name


class Schema__Playwright__Stack__Create__Request(Type_Safe):
    stack_name   : Safe_Str__Playwright__Stack__Name = ''                           # Empty → service generates "{adj}-{scientist}"
    host_url     : Safe_Str__Url                                                    # Host-plane base URL (empty → resolved from SG_PLAYWRIGHT__HOST_PLANE_URL)
    host_api_key : Safe_Str__Text                                                   # Host-plane API key  (empty → resolved from SG_PLAYWRIGHT__HOST_PLANE_API_KEY)
    image_tag    : Safe_Str__Text                    = 'latest'                     # diniscruz/sg-playwright:<tag>
    api_key      : Safe_Str__Text                                                   # FAST_API__AUTH__API_KEY__VALUE baked into the launched pod
    host_port    : int                               = 8000                        # Host port mapped to the pod's :8000
