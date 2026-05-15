# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__ACME__Config
# Resolved configuration for one ACME issuance run. Pure data — built by
# cert_init from the SG__CERT_INIT__ACME_* env vars, consumed by Cert__ACME__Client.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__ACME__Config(Type_Safe):
    directory_url  : str = ''                            # LE staging or prod ACME directory
    contact_email  : str = ''                            # optional account contact
    profile        : str = 'shortlived'                  # LE requires the 'shortlived' profile for IP certs
    challenge_port : int = 80                            # http-01 challenge listener
