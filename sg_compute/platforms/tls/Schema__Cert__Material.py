# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Cert__Material
# A cert + private key pair, both PEM-encoded. The output of Cert__Generator.
# PEM is ASCII so str is the natural carrier.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Cert__Material(Type_Safe):
    cert_pem : str
    key_pem  : str
