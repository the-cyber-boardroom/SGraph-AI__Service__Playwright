# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Manifest__Interpreter (no mocks, no patches)
# The allowlist boundary: a valid manifest produces an ordered allowlisted plan;
# anything outside the vocabulary is rejected with a specific error code.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from vault_publish.schemas.Enum__Manifest__Error_Code    import Enum__Manifest__Error_Code
from vault_publish.schemas.Enum__Provisioning__Step_Kind import Enum__Provisioning__Step_Kind
from vault_publish.schemas.Enum__Vault_App__Runtime      import Enum__Vault_App__Runtime
from vault_publish.schemas.Enum__Vault_App__Type         import Enum__Vault_App__Type
from vault_publish.schemas.Safe_Str__Manifest__Path      import Safe_Str__Manifest__Path
from vault_publish.schemas.Safe_Str__Message             import Safe_Str__Message
from vault_publish.schemas.Schema__Vault_App__Manifest   import Schema__Vault_App__Manifest
from vault_publish.service.Manifest__Interpreter         import Manifest__Interpreter


def _manifest(app_type=Enum__Vault_App__Type.STATIC_SITE,
              runtime =Enum__Vault_App__Runtime.STATIC,
              content_root='public', health_path='healthz') -> Schema__Vault_App__Manifest:
    manifest = Schema__Vault_App__Manifest()
    if app_type is not None:
        manifest.app_type = app_type
    if runtime is not None:
        manifest.runtime = runtime
    manifest.content_root = Safe_Str__Manifest__Path(content_root)
    manifest.health_path  = Safe_Str__Manifest__Path(health_path)
    return manifest


class test_Manifest__Interpreter(TestCase):

    def setUp(self):
        self.interpreter = Manifest__Interpreter()

    # ── valid ────────────────────────────────────────────────────────────────

    def test_valid_manifest_produces_plan(self):
        plan, error = self.interpreter.interpret(_manifest())
        assert error is None
        assert plan  is not None
        kinds = [step.kind for step in plan.steps]
        assert Enum__Provisioning__Step_Kind.SET_RUNTIME     in kinds
        assert Enum__Provisioning__Step_Kind.MOUNT_CONTENT   in kinds
        assert Enum__Provisioning__Step_Kind.SET_HEALTH_PATH in kinds

    def test_plan_includes_env_and_route_steps(self):
        manifest = _manifest()
        manifest.env[Safe_Str__Message('LANG')] = Safe_Str__Message('en')
        manifest.routes[Safe_Str__Manifest__Path('/')] = Safe_Str__Manifest__Path('index.html')
        plan, error = self.interpreter.interpret(manifest)
        assert error is None
        kinds = [step.kind for step in plan.steps]
        assert Enum__Provisioning__Step_Kind.SET_ENV        in kinds
        assert Enum__Provisioning__Step_Kind.REGISTER_ROUTE in kinds

    def test_first_step_is_set_runtime(self):
        plan, _ = self.interpreter.interpret(_manifest())
        assert plan.steps[0].kind == Enum__Provisioning__Step_Kind.SET_RUNTIME

    # ── rejections ───────────────────────────────────────────────────────────

    def test_missing_app_type_rejected(self):
        plan, error = self.interpreter.interpret(_manifest(app_type=None))
        assert plan  is None
        assert error == Enum__Manifest__Error_Code.UNSUPPORTED_APP_TYPE

    def test_missing_runtime_rejected(self):
        plan, error = self.interpreter.interpret(_manifest(runtime=None))
        assert plan  is None
        assert error == Enum__Manifest__Error_Code.UNSUPPORTED_RUNTIME

    def test_incompatible_runtime_rejected(self):                            # static-site cannot use the node runtime
        manifest = _manifest(app_type=Enum__Vault_App__Type.STATIC_SITE,
                             runtime =Enum__Vault_App__Runtime.NODE)
        plan, error = self.interpreter.interpret(manifest)
        assert plan  is None
        assert error == Enum__Manifest__Error_Code.INCOMPATIBLE_RUNTIME

    def test_node_runtime_allowed_for_vault_js_app(self):
        manifest = _manifest(app_type=Enum__Vault_App__Type.VAULT_JS_APP,
                             runtime =Enum__Vault_App__Runtime.NODE)
        plan, error = self.interpreter.interpret(manifest)
        assert error is None
        assert plan  is not None

    def test_missing_content_root_rejected(self):
        plan, error = self.interpreter.interpret(_manifest(content_root=''))
        assert plan  is None
        assert error == Enum__Manifest__Error_Code.MISSING_CONTENT_ROOT

    def test_missing_health_path_rejected(self):
        plan, error = self.interpreter.interpret(_manifest(health_path=''))
        assert plan  is None
        assert error == Enum__Manifest__Error_Code.MISSING_HEALTH_PATH
