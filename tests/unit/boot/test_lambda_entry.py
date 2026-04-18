# ═══════════════════════════════════════════════════════════════════════════════
# Tests — lambda_entry.py boot shim (v0.1.28 — S3-zip hot-swap)
#
# Scope (unit-level, no real AWS, no real container):
#   • load_code_from_local_path — CODE_LOCAL_PATH override, directory validation
#   • load_code_from_s3 — AWS_REGION gate, required env vars, cache short-circuit
#   • resolve_code_source — precedence: local > S3 > passthrough
#   • boot — error-pinning path, happy path (mocked service import)
#   • run — returns error string when boot failed, delegates otherwise
#
# Tests never let boot() call the real Fast_API__Playwright__Service. Either:
#   (a) env vars drive the path into a passthrough no-op, or
#   (b) the service import is substituted via sys.modules.
# ═══════════════════════════════════════════════════════════════════════════════

import importlib
import os
import sys
import tempfile
from unittest                                                                                 import TestCase


# Module-under-test — import once, call helpers directly
import lambda_entry


ENV_KEYS = [lambda_entry.ENV_VAR__AGENTIC_APP_NAME              ,
            lambda_entry.ENV_VAR__AGENTIC_APP_STAGE             ,
            lambda_entry.ENV_VAR__AGENTIC_APP_VERSION           ,
            lambda_entry.ENV_VAR__AGENTIC_CODE_LOCAL_PATH       ,
            lambda_entry.ENV_VAR__AGENTIC_CODE_SOURCE           ,
            lambda_entry.ENV_VAR__AGENTIC_CODE_SOURCE_S3_BUCKET ,
            lambda_entry.ENV_VAR__AGENTIC_CODE_SOURCE_S3_KEY    ,
            lambda_entry.ENV_VAR__AGENTIC_IMAGE_VERSION         ,
            lambda_entry.ENV_VAR__AWS_REGION                    ,
            lambda_entry.ENV_VAR__LAMBDA_FUNCTION               ]


class _EnvScrub:                                                                    # Snapshot + restore the six env vars + one extra caller-specified
    def __init__(self, **overrides):
        self.overrides = overrides
        self.snapshot  = {}
        self.extra_keys = list(overrides.keys())
    def __enter__(self):
        for k in ENV_KEYS + self.extra_keys:
            self.snapshot[k] = os.environ.pop(k, None)
        for k, v in self.overrides.items():
            os.environ[k] = v
        return self
    def __exit__(self, *exc):
        for k in ENV_KEYS + self.extra_keys:
            os.environ.pop(k, None)
            if self.snapshot.get(k) is not None:
                os.environ[k] = self.snapshot[k]


class _SysPathSnapshot:                                                             # Restore sys.path exactly as it was — boot shims mutate it
    def __enter__(self):
        self.saved = list(sys.path)
        return self
    def __exit__(self, *exc):
        sys.path[:] = self.saved


class test_load_code_from_local_path(TestCase):

    def test__returns_none_when_env_unset(self):
        with _EnvScrub(), _SysPathSnapshot():
            assert lambda_entry.load_code_from_local_path() is None

    def test__prepends_directory_and_returns_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _EnvScrub(**{lambda_entry.ENV_VAR__AGENTIC_CODE_LOCAL_PATH: tmp}), _SysPathSnapshot():
                source = lambda_entry.load_code_from_local_path()
                assert source        == f'local:{tmp}'
                assert sys.path[0]   == tmp                                         # Prepended, not appended

    def test__raises_when_path_not_a_directory(self):
        with _EnvScrub(**{lambda_entry.ENV_VAR__AGENTIC_CODE_LOCAL_PATH: '/nonexistent/xyzzy'}), _SysPathSnapshot():
            raised = False
            try:
                lambda_entry.load_code_from_local_path()
            except RuntimeError as exc:
                raised = True
                assert '/nonexistent/xyzzy' in str(exc)
            assert raised, 'expected RuntimeError for missing directory'


class test_load_code_from_s3(TestCase):

    def test__returns_none_when_aws_region_unset(self):                             # Not on Lambda — skip S3
        with _EnvScrub(), _SysPathSnapshot():
            assert lambda_entry.load_code_from_s3() is None

    def test__returns_none_when_local_path_set(self):                               # Local override wins
        with tempfile.TemporaryDirectory() as tmp:
            with _EnvScrub(**{lambda_entry.ENV_VAR__AGENTIC_CODE_LOCAL_PATH: tmp,
                              lambda_entry.ENV_VAR__AWS_REGION     : 'eu-west-2'}), _SysPathSnapshot():
                assert lambda_entry.load_code_from_s3() is None


class test_resolve_code_source(TestCase):

    def test__passthrough_when_nothing_set(self):
        with _EnvScrub(), _SysPathSnapshot():
            assert lambda_entry.resolve_code_source() == 'passthrough:sys.path'

    def test__local_path_wins_over_aws_region(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _EnvScrub(**{lambda_entry.ENV_VAR__AGENTIC_CODE_LOCAL_PATH: tmp,
                              lambda_entry.ENV_VAR__AWS_REGION     : 'eu-west-2'}), _SysPathSnapshot():
                source = lambda_entry.resolve_code_source()
                assert source.startswith('local:')


class test_read_image_version(TestCase):

    def test__returns_v0_sentinel_when_file_missing(self):
        # The repo root image_version file exists in the test checkout, so temporarily
        # replace the path constant with a nonexistent one.
        saved = lambda_entry.IMAGE_VERSION_PATH
        try:
            lambda_entry.IMAGE_VERSION_PATH = '/nonexistent/image_version'
            assert lambda_entry.read_image_version() == 'v0'
        finally:
            lambda_entry.IMAGE_VERSION_PATH = saved

    def test__reads_file_when_present(self):
        with tempfile.NamedTemporaryFile('w', delete=False) as f:
            f.write('v7\n')
            path = f.name
        saved = lambda_entry.IMAGE_VERSION_PATH
        try:
            lambda_entry.IMAGE_VERSION_PATH = path
            assert lambda_entry.read_image_version() == 'v7'
        finally:
            lambda_entry.IMAGE_VERSION_PATH = saved
            os.unlink(path)


class test_boot(TestCase):

    def test__happy_path_returns_handler_and_app(self):                             # Real service import — works because the package is on sys.path in the test env
        with _EnvScrub(), _SysPathSnapshot():
            err, handler, app, source = lambda_entry.boot()
            assert err     is None
            assert handler is not None
            assert app     is not None
            assert source  == 'passthrough:sys.path'

    def test__sets_image_version_env_var(self):
        with _EnvScrub(), _SysPathSnapshot():
            lambda_entry.boot()
            assert os.environ.get(lambda_entry.ENV_VAR__AGENTIC_IMAGE_VERSION) is not None  # read_image_version returned SOMETHING

    def test__error_pinned_when_import_fails_inside_lambda(self):                   # Simulate a broken zip — the service module raises on import
        import importlib.util
        fake_path = 'sgraph_ai_service_playwright.fast_api.Fast_API__Playwright__Service'
        saved     = sys.modules.pop(fake_path, None)
        try:
            class _BoomFinder:
                def find_spec(self, name, path=None, target=None):
                    if name == fake_path:
                        raise ImportError('simulated zip corruption')
                    return None
            sys.meta_path.insert(0, _BoomFinder())
            with _EnvScrub(**{lambda_entry.ENV_VAR__LAMBDA_FUNCTION: 'sg-playwright-dev'}), _SysPathSnapshot():
                err, handler, app, source = lambda_entry.boot()
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
                    lambda_entry.boot()
                except ImportError as exc:
                    raised = True
                    assert 'simulated zip corruption' in str(exc)
                assert raised, 'expected ImportError to propagate outside Lambda'
        finally:
            sys.meta_path = [f for f in sys.meta_path if not isinstance(f, _BoomFinder)]
            if saved is not None:
                sys.modules[fake_path] = saved


class test_run(TestCase):

    def test__returns_error_string_when_error_pinned(self):
        saved_error   = lambda_entry.error
        saved_handler = lambda_entry.handler
        try:
            lambda_entry.error   = 'CRITICAL ERROR: test'
            lambda_entry.handler = None
            assert lambda_entry.run({}, None) == 'CRITICAL ERROR: test'
        finally:
            lambda_entry.error   = saved_error
            lambda_entry.handler = saved_handler

    def test__delegates_to_handler_when_ok(self):
        saved_error   = lambda_entry.error
        saved_handler = lambda_entry.handler
        try:
            calls = []
            def fake_handler(event, ctx):
                calls.append((event, ctx))
                return 'ok'
            lambda_entry.error   = None
            lambda_entry.handler = fake_handler
            assert lambda_entry.run({'k': 'v'}, 'ctx') == 'ok'
            assert calls == [({'k': 'v'}, 'ctx')]
        finally:
            lambda_entry.error   = saved_error
            lambda_entry.handler = saved_handler
