# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Schema__Content_Proxy__Create__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__Stack__Info       import Schema__Content_Proxy__Stack__Info


class Schema__Content_Proxy__Create__Response(Type_Safe):
    stack_info         : Schema__Content_Proxy__Stack__Info = None
    fastapi_api_key    : str = ''    # generated once — interceptor ↔ mitm-service auth (also in the box .env)
    playwright_api_key : str = ''    # generated once — sg-playwright X-API-Key
    message            : str = ''
    elapsed_ms         : int = 0
