# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Schema__Content_Proxy__Create__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.content_proxy.schemas.Schema__Content_Proxy__Stack__Info       import Schema__Content_Proxy__Stack__Info


class Schema__Content_Proxy__Create__Response(Type_Safe):
    stack_info         : Schema__Content_Proxy__Stack__Info = None
    fastapi_api_key    : str  = ''   # interceptor ↔ mitm-service auth (from --env-file, or generated)
    access_token       : str  = ''   # vault key + sg-playwright /pw key + set-cookie token (from --env-file, or generated)
    secrets_from_env   : bool = False  # True when the keys came from a supplied --env-file
    proxyauth_user     : str  = ''   # mitmproxy-ext (Mode 1) basic-auth user (default 'demo', or --proxyauth-user)
    proxyauth_pass     : str  = ''   # mitmproxy-ext (Mode 1) basic-auth pass (generated GUID, or --proxyauth-pass)
    message            : str  = ''
    elapsed_ms         : int  = 0
