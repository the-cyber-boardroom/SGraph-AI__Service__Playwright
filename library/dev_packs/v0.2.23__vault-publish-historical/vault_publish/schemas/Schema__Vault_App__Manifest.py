# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Schema__Vault_App__Manifest
# The declarative provisioning manifest carried inside the vault folder. It
# declares intent; Manifest__Interpreter maps it to an allowlisted plan. There
# is deliberately no command / script / exec field — the absence is the security
# property (see dev pack 06__security).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                       import Type_Safe

from vault_publish.schemas.Dict__Manifest__Env             import Dict__Manifest__Env
from vault_publish.schemas.Dict__Manifest__Routes          import Dict__Manifest__Routes
from vault_publish.schemas.Enum__Vault_App__Runtime        import Enum__Vault_App__Runtime
from vault_publish.schemas.Enum__Vault_App__Type           import Enum__Vault_App__Type
from vault_publish.schemas.Safe_Str__Manifest__Path        import Safe_Str__Manifest__Path


class Schema__Vault_App__Manifest(Type_Safe):
    app_type     : Enum__Vault_App__Type                   # allowlisted app kind
    runtime      : Enum__Vault_App__Runtime                # allowlisted runtime
    content_root : Safe_Str__Manifest__Path                # path within the vault folder to serve
    health_path  : Safe_Str__Manifest__Path                # path the warming page polls
    env          : Dict__Manifest__Env                     # allowlisted env settings
    routes       : Dict__Manifest__Routes                  # declarative request-path → content-path table
