# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-app: Schema__Vault_App__Auto_DNS__Result
# Outcome of one --with-aws-dns run from inside `sp vault-app create`. Pure data —
# the helper class fills this in and the CLI prints it.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Vault_App__Auto_DNS__Result(Type_Safe):
    fqdn               : str  = ''     # FQDN the A record points at — e.g. warm-bohr.sg-compute.sgraph.ai
    public_ip          : str  = ''     # value the A record was set to
    zone_id            : str  = ''     # Route 53 hosted zone id that owns the FQDN
    zone_name          : str  = ''     # the zone's name (sg-compute.sgraph.ai)
    change_id          : str  = ''     # Route 53 change id (/change/CXXXXXXX) — empty if upsert failed
    insync             : bool = False  # Route 53 reported INSYNC inside the timeout
    authoritative_pass : bool = False  # all authoritative nameservers returned `public_ip`
    elapsed_ms         : int  = 0      # total time spent in the auto-DNS run
    error              : str  = ''     # populated on any failure path; '' on success
