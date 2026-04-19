# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Agentic_Boot_Shim (v0.1.29)
#
# Scope (unit-level, no real AWS):
#   • read_image_version  — file present / absent, sentinel fallback.
#   • boot                — happy path (real service import via passthrough),
#                           image_version env var is written, error-pinning
#                           inside Lambda, re-raise outside Lambda.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys
import tempfile
from unittest                                                                       import TestCase

from sgraph_ai_service_playwright.agentic_fastapi_aws                        import Agentic_Boot_Shim      as agentic_boot_shim_module
from sgraph_ai_service_playwright.agentic_fastapi_aws.Agentic_Boot_Shim       import (Agentic_Boot_Shim        ,
                                                                                       FALLBACK_IMAGE_VERSION  ,
                                                                                       ENV_VAR__LAMBDA_FUNCTION)
from sgraph_ai_service_playwright.agentic_fastapi.Agentic_Boot_State                import (get_boot_log    ,
                                                                                            get_last_error  ,
                                                                                            reset_boot_state)
from sgraph_ai_service_playwright.consts.env_vars                                   import (ENV_VAR__AGENTIC_APP_NAME              ,
                                                                                            ENV_VAR__AGENTIC_APP_STAGE             ,
                                                                                            ENV_VAR__AGENTIC_APP_VERSION           ,
                                                                                            ENV_VAR__AGENTIC_CODE_LOCAL_PATH       ,
                                                                                            ENV_VAR__AGENTIC_CODE_SOURCE           ,
                                                                                            ENV_VAR__AGENTIC_CODE_SOURCE_S3_BUCKET ,
                                                                                            ENV_VAR__AGENTIC_CODE_SOURCE_S3_KEY    ,
                                                                                            ENV_VAR__AGENTIC_IMAGE_VERSION         ,
                                                                                            ENV_VAR__AWS_REGION                    )


ENV_KEYS = [ENV_VAR__AGENTIC_APP_NAME              ,
            ENV_VAR__AGENTIC_APP_STAGE             ,
            ENV_VAR__AGENTIC_APP_VERSION           ,
            ENV_VAR__AGENTIC_CODE_LOCAL_PATH       ,
            ENV_VAR__AGENTIC_CODE_SOURCE           ,
            ENV_VAR__AGENTIC_CODE_SOURCE_S3_BUCKET ,
            ENV_VAR__AGENTIC_CODE_SOURCE_S3_KEY    ,
            ENV_VAR__AGENTIC_IMAGE_VERSION         ,
            ENV_VAR__AWS_REGION                    ,
            ENV_VAR__LAMBDA_FUNCTION               ]


class _EnvScrub:
    def __init__(self, **overrides):
        self.overrides = overrides
        self.snapshot  = {}
    def __enter__(self):
        for k in ENV_KEYS:
            self.snapshot[k] = os.environ.pop(k, None)
        for k, v in self.overrides.items():
            os.environ[k] = v
        return self
    def __exit__(self, *exc):
        for k in ENV_KEYS:
            os.environ.pop(k, None)
            if self.snapshot.get(k) is not None:
                os.environ[k] = self.snapshot[k]


class _SysPathSnapshot:
    def __enter__(self):
        self.saved = list(sys.path)
        return self
    def __exit__(self, *exc):
        sys.path[:] = self.saved


class test_read_image_version(TestCase):

    def test__returns_sentinel_when_file_missing(self):                             # Repo root has an image_version file; swap the constant for a missing path
        saved = agentic_boot_shim_module.IMAGE_VERSION_PATH
        try:
            agentic_boot_shim_module.IMAGE_VERSION_PATH = '/nonexistent/image_version'
            assert Agentic_Boot_Shim().read_image_version() == FALLBACK_IMAGE_VERSION
        finally:
            agentic_boot_shim_module.IMAGE_VERSION_PATH = saved

    def test__reads_file_when_present(self):
        with tempfile.NamedTemporaryFile('w', delete=False) as f:
            f.write('v7\n')
            path = f.name
        saved = agentic_boot_shim_module.IMAGE_VERSION_PATH
        try:
            agentic_boot_shim_module.IMAGE_VERSION_PATH = path
            assert Agentic_Boot_Shim().read_image_version() == 'v7'
        finally:
            agentic_boot_shim_module.IMAGE_VERSION_PATH = saved
            os.unlink(path)


class test_boot(TestCase):

    def test__happy_path_returns_handler_and_app(self):                             # Real service import — works because the package is on sys.path in the test env
        with _EnvScrub(), _SysPathSnapshot():
            err, handler, app, source = Agentic_Boot_Shim().boot()
            assert err     is None
            assert handler is not None
            assert app     is not None
            assert source  == 'passthrough:sys.path'

    def test__sets_image_version_env_var(self):
        with _EnvScrub(), _SysPathSnapshot():
            Agentic_Boot_Shim().boot()
            assert os.environ.get(ENV_VAR__AGENTIC_IMAGE_VERSION) is not None

    def test__sets_code_source_env_var(self):
        with _EnvScrub(), _SysPathSnapshot():
            Agentic_Boot_Shim().boot()
            assert os.environ.get(ENV_VAR__AGENTIC_CODE_SOURCE) == 'passthrough:sys.path'

    def test__error_pinned_when_import_fails_inside_lambda(self):                   # Simulate a broken zip — the service module raises on import
        fake_path = 'sgraph_ai_service_playwright.fast_api.Fast_API__Playwright__Service'
        saved     = sys.modules.pop(fake_path, None)
        try:
            class _BoomFinder:
                def find_spec(self, name, path=None, target=None):
                    if name == fake_path:
                        raise ImportError('simulated zip corruption')
                    return None
            sys.meta_path.insert(0, _BoomFinder())
            with _EnvScrub(**{ENV_VAR__LAMBDA_FUNCTION: 'sg-playwright-dev'}), _SysPathSnapshot():
                err, handler, app, source = Agentic_Boot_Shim().boot()
                assert err is not None
                assert 'CRITICAL ERROR' in err
                assert 'simulated zip corruption' in err
                assert handler is None
                assert app     is None
        finally:
            sys.meta_path = [f for f in sys.meta_path if not isinstance(f, _BoomFinder)]
            if saved is not None:
                sys.modules[fake_path] = saved

    def test__reraises_when_import_fails_outside_lambda(self):                      # Outside Lambda — stack trace > error string
        fake_path = 'sgraph_ai_service_playwright.fast_api.Fast_API__Playwright__Service'
        saved     = sys.modules.pop(fake_path, None)
        try:
            class _BoomFinder:
                def find_spec(self, name, path=None, target=None):
                    if name == fake_path:
                        raise ImportError('simulated zip corruption')
                    return None
            sys.meta_path.insert(0, _BoomFinder())
            with _EnvScrub(), _SysPathSnapshot():                                   # LAMBDA_FUNCTION env NOT set
                raised = False
                try:
                    Agentic_Boot_Shim().boot()
                except ImportError as exc:
                    raised = True
                    assert 'simulated zip corruption' in str(exc)
                assert raised, 'expected ImportError to propagate outside Lambda'
        finally:
            sys.meta_path = [f for f in sys.meta_path if not isinstance(f, _BoomFinder)]
            if saved is not None:
                sys.modules[fake_path] = saved


class test_boot_writes_to_boot_state(TestCase):                                     # Shim → Agentic_Boot_State wiring; admin API reads the same state

    def setUp(self):
        reset_boot_state()

    def test__happy_path_appends_three_boot_log_lines(self):
        with _EnvScrub(), _SysPathSnapshot():
            Agentic_Boot_Shim().boot()
        log = get_boot_log()
        assert any(line.startswith('image_version=') for line in log)
        assert any(line.startswith('code_source=')   for line in log)
        assert 'status=loaded'                        in log

    def test__happy_path_clears_last_error(self):                                   # Warm success after a cold-start failure must reset the error holder
        with _EnvScrub(), _SysPathSnapshot():
            Agentic_Boot_Shim().boot()
        assert get_last_error() == ''

    def test__failure_inside_lambda_writes_error_and_degraded_log(self):
        fake_path = 'sgraph_ai_service_playwright.fast_api.Fast_API__Playwright__Service'
        saved     = sys.modules.pop(fake_path, None)
        try:
            class _BoomFinder:
                def find_spec(self, name, path=None, target=None):
                    if name == fake_path:
                        raise ImportError('simulated zip corruption')
                    return None
            sys.meta_path.insert(0, _BoomFinder())
            with _EnvScrub(**{ENV_VAR__LAMBDA_FUNCTION: 'sg-playwright-dev'}), _SysPathSnapshot():
                Agentic_Boot_Shim().boot()
            log = get_boot_log()
            assert any(line.startswith('status=degraded') for line in log)
            assert 'CRITICAL ERROR'          in get_last_error()
            assert 'simulated zip corruption' in get_last_error()
        finally:
            sys.meta_path = [f for f in sys.meta_path if not isinstance(f, _BoomFinder)]
            if saved is not None:
                sys.modules[fake_path] = saved
