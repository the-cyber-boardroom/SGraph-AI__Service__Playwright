# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/creds — Schema__Creds__Export
# Temporary credentials ready for export to the shell or downstream tooling.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Creds__Export(Type_Safe):
    access_key_id     : str = ''
    secret_access_key : str = ''
    session_token     : str = ''
    expiration        : str = ''
    region            : str = ''
