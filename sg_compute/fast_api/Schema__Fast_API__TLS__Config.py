# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Fast_API__TLS__Config
# The resolved uvicorn-launch configuration for a FastAPI app: plain HTTP on
# :8000 by default, or HTTPS on :443 when the FAST_API__TLS__* env contract
# enables it. Computed from the environment by Fast_API__TLS__Launcher.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Fast_API__TLS__Config(Type_Safe):
    enabled   : bool = False
    host      : str  = '0.0.0.0'
    port      : int  = 8000
    cert_file : str  = ''
    key_file  : str  = ''
