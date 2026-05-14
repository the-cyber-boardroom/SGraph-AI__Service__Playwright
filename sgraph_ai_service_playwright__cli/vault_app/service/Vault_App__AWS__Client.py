# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Vault_App__AWS__Client
# Composition shell for the per-concern AWS helpers. Owns the tag-key constants
# and the VAULT_APP_NAMING binding so the section's AWS surface lives in one
# shared header. Mirrors sister sections (vnc, prometheus, etc.).
#
# Tag convention:
#   sg:purpose    : vault_app
#   sg:stack-name : {stack_name}
#   sg:creator    : git email or $USER
#   sg:section    : vault_app
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.aws.Stack__Naming                            import Stack__Naming


TAG_PURPOSE_KEY   = 'sg:purpose'
TAG_PURPOSE_VALUE = 'vault_app'
TAG_STACK_NAME_KEY = 'sg:stack-name'
TAG_CREATOR_KEY   = 'sg:creator'
TAG_SECTION_KEY   = 'sg:section'

VAULT_APP_NAMING = Stack__Naming(purpose=TAG_PURPOSE_VALUE, section='vault_app')


class Vault_App__AWS__Client(Type_Safe):
    sg_helper       : object = None                                                 # Vault_App__SG__Helper    (lazy via setup())
    instance_helper : object = None                                                 # Vault_App__Instance__Helper (lazy via setup())
    tags_builder    : object = None                                                 # Vault_App__Tags__Builder (lazy via setup())
    launch_helper   : object = None                                                 # Vault_App__Launch__Helper (lazy via setup())

    def setup(self) -> 'Vault_App__AWS__Client':                                    # Lazy imports keep boot fast
        from sgraph_ai_service_playwright__cli.vault_app.service.Vault_App__SG__Helper       import Vault_App__SG__Helper
        from sgraph_ai_service_playwright__cli.vault_app.service.Vault_App__Instance__Helper import Vault_App__Instance__Helper
        from sgraph_ai_service_playwright__cli.vault_app.service.Vault_App__Tags__Builder    import Vault_App__Tags__Builder
        from sgraph_ai_service_playwright__cli.vault_app.service.Vault_App__Launch__Helper   import Vault_App__Launch__Helper
        self.sg_helper       = Vault_App__SG__Helper()
        self.instance_helper = Vault_App__Instance__Helper()
        self.tags_builder    = Vault_App__Tags__Builder()
        self.launch_helper   = Vault_App__Launch__Helper()
        return self
