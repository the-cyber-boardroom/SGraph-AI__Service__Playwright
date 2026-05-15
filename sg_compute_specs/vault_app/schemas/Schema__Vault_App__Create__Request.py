# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-app: Schema__Vault_App__Create__Request
# Inputs for `sg vault-app create`. Pure data.
#
# Modes:
#   just-vault     (default)  — 2 containers: host-plane + sg-send-vault
#   with-playwright           — 4 containers: + sg-playwright + agent-mitmproxy
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Vault_App__Create__Request(Type_Safe):
    region           : str   = 'eu-west-2'
    instance_type    : str   = 't3.medium'
    from_ami         : str   = ''          # explicit AMI ID; blank = resolve latest AL2023
    stack_name       : str   = ''          # blank = auto-generate
    caller_ip        : str   = ''          # blank = auto-detect
    max_hours        : float = 1.0         # D2 — fractional hours supported: 0.1 = 6 min
    with_playwright  : bool  = False        # False = just-vault (2 containers); True = + playwright/mitmproxy
    container_engine : str   = 'docker'    # docker | podman
    storage_mode     : str   = 'disk'      # sg-send-vault SEND__STORAGE_MODE: disk | memory | s3
    seed_vault_keys  : str   = ''          # comma-separated sgit keys passed to sg-send-vault on boot
    access_token     : str   = ''          # shared stack secret; auto-generated if blank
    disk_size_gb     : int   = 20          # root volume — vault data + container images
    use_spot         : bool  = True        # spot by default (~70% cheaper)
    with_tls_check   : bool  = True         # default: serve HTTPS on :443 via the cert sidecar
    tls_mode         : str   = 'letsencrypt-ip' # default: a real Let's Encrypt IP cert (vs self-signed offline)
    acme_prod        : bool  = True         # default: LE production directory (browser-trusted)
