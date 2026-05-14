# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Manifest__Interpreter
# The allowlist boundary. interpret() maps a verified declarative manifest to an
# ordered Schema__Provisioning__Plan of allowlisted steps — or rejects it with a
# specific Enum__Manifest__Error_Code. It never falls through to "just run it":
# the closed Enum__Provisioning__Step_Kind vocabulary is the allowlist, and there
# is no step kind that runs arbitrary code.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                  import Optional

from osbot_utils.type_safe.Type_Safe                         import Type_Safe

from vault_publish.schemas.Enum__Manifest__Error_Code        import Enum__Manifest__Error_Code
from vault_publish.schemas.Enum__Provisioning__Step_Kind     import Enum__Provisioning__Step_Kind
from vault_publish.schemas.Enum__Vault_App__Runtime          import Enum__Vault_App__Runtime
from vault_publish.schemas.Enum__Vault_App__Type             import Enum__Vault_App__Type
from vault_publish.schemas.Safe_Str__Message                 import Safe_Str__Message
from vault_publish.schemas.Schema__Provisioning__Plan        import Schema__Provisioning__Plan
from vault_publish.schemas.Schema__Provisioning__Step        import Schema__Provisioning__Step
from vault_publish.schemas.Schema__Vault_App__Manifest       import Schema__Vault_App__Manifest

# app_type → the runtimes allowed with it
COMPATIBLE_RUNTIMES = {
    Enum__Vault_App__Type.STATIC_SITE  : {Enum__Vault_App__Runtime.STATIC}                              ,
    Enum__Vault_App__Type.VAULT_JS_APP : {Enum__Vault_App__Runtime.STATIC, Enum__Vault_App__Runtime.NODE},
}


class Manifest__Interpreter(Type_Safe):

    def interpret(self, manifest: Schema__Vault_App__Manifest) -> tuple:    # -> (plan|None, error_code|None)
        error_code = self._validate(manifest)
        if error_code is not None:
            return None, error_code

        plan = Schema__Provisioning__Plan()
        plan.steps.append(self._step(Enum__Provisioning__Step_Kind.SET_RUNTIME    , manifest.runtime.value      ))
        plan.steps.append(self._step(Enum__Provisioning__Step_Kind.MOUNT_CONTENT  , str(manifest.content_root)  ))
        for key, value in manifest.env.items():
            plan.steps.append(self._step(Enum__Provisioning__Step_Kind.SET_ENV       , f'{key}={value}'         ))
        for path, content in manifest.routes.items():
            plan.steps.append(self._step(Enum__Provisioning__Step_Kind.REGISTER_ROUTE, f'{path}->{content}'     ))
        plan.steps.append(self._step(Enum__Provisioning__Step_Kind.SET_HEALTH_PATH, str(manifest.health_path)   ))
        return plan, None

    def _validate(self, manifest: Schema__Vault_App__Manifest) -> Optional[Enum__Manifest__Error_Code]:
        if manifest.app_type is None or manifest.app_type not in COMPATIBLE_RUNTIMES:
            return Enum__Manifest__Error_Code.UNSUPPORTED_APP_TYPE
        if manifest.runtime is None:
            return Enum__Manifest__Error_Code.UNSUPPORTED_RUNTIME
        if manifest.runtime not in COMPATIBLE_RUNTIMES[manifest.app_type]:
            return Enum__Manifest__Error_Code.INCOMPATIBLE_RUNTIME
        if not str(manifest.content_root):
            return Enum__Manifest__Error_Code.MISSING_CONTENT_ROOT
        if not str(manifest.health_path):
            return Enum__Manifest__Error_Code.MISSING_HEALTH_PATH
        return None

    def _step(self, kind: Enum__Provisioning__Step_Kind, target: str) -> Schema__Provisioning__Step:
        return Schema__Provisioning__Step(kind=kind, target=Safe_Str__Message(target))
