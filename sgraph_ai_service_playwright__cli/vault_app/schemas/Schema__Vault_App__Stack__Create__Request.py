# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Vault_App__Stack__Create__Request
# Inputs for `sp vault-app create [NAME]`. All fields optional — service
# generates a random name, detects caller IP, generates the access token,
# picks the latest AL2023 AMI when none are supplied. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text        import Safe_Str__Text

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AMI__Id             import Safe_Str__AMI__Id
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.vault_app.primitives.Safe_Str__Vault_App__Access__Token import Safe_Str__Vault_App__Access__Token
from sgraph_ai_service_playwright__cli.vault_app.primitives.Safe_Str__Vault_App__Stack__Name   import Safe_Str__Vault_App__Stack__Name


class Schema__Vault_App__Stack__Create__Request(Type_Safe):
    stack_name    : Safe_Str__Vault_App__Stack__Name  = ''                          # Empty → service generates "va-{adj}-{scientist}"
    region        : Safe_Str__AWS__Region             = ''                          # Empty → resolved from AWS_Config
    instance_type : Safe_Str__Text                    = ''                          # Empty → 't3.medium'
    from_ami      : Safe_Str__AMI__Id                 = ''                          # Empty → latest AL2023 resolved by service
    access_token  : Safe_Str__Vault_App__Access__Token = ''                         # Empty → service generates one
    seed_vault_keys : Safe_Str__Text                  = ''                          # Comma-separated vault keys; service clones each on boot
    max_hours     : int                               = 4                           # Auto-terminate after N hours; 0 disables
    use_spot      : bool                              = True
    storage_mode  : Safe_Str__Text                    = 'disk'                      # disk | memory | s3
