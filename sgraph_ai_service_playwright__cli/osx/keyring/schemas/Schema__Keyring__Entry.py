# ═══════════════════════════════════════════════════════════════════════════════
# SG Credentials — Schema__Keyring__Entry
# One keychain item: service name + account name.
# Value is NOT stored in the schema — read it via Keyring__Mac__OS.get().
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                           import Type_Safe

from sgraph_ai_service_playwright__cli.osx.keyring.primitives.Safe_Str__Keyring__Account      import Safe_Str__Keyring__Account
from sgraph_ai_service_playwright__cli.osx.keyring.primitives.Safe_Str__Keyring__Service_Name import Safe_Str__Keyring__Service_Name


class Schema__Keyring__Entry(Type_Safe):
    service_name    : Safe_Str__Keyring__Service_Name
    account         : Safe_Str__Keyring__Account
