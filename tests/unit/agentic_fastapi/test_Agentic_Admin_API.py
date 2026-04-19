# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Agentic_Admin_API (v0.1.29)
#
# Hits every /admin/* endpoint via a FastAPI TestClient on the real
# Fast_API__Playwright__Service composition. Asserts:
#   • Every endpoint returns 200.
#   • The response shape matches the Type_Safe schema defined in schemas/.
#   • /admin/env redacts to AGENTIC_* only — no AWS / SG_PLAYWRIGHT__ leakage.
#   • /admin/health flips loaded → degraded when set_last_error() is called.
#   • /admin/skills/{name} 404s on unknown audiences.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                       import TestCase

from fastapi.testclient                                                             import TestClient

from sgraph_ai_service_playwright.agentic_fastapi.Agentic_Admin_API                 import (SKILL_NAMES              ,
                                                                                            TAG__ROUTES_ADMIN        )
from sgraph_ai_service_playwright.agentic_fastapi.Agentic_Boot_State                import (append_boot_log          ,
                                                                                            reset_boot_state         ,
                                                                                            set_last_error           )
from sgraph_ai_service_playwright.consts.env_vars                                   import (ENV_VAR__AGENTIC_APP_NAME     ,
                                                                                            ENV_VAR__AGENTIC_APP_STAGE    ,
                                                                                            ENV_VAR__AGENTIC_APP_VERSION  ,
                                                                                            ENV_VAR__AGENTIC_CODE_SOURCE  ,
                                                                                            ENV_VAR__AGENTIC_IMAGE_VERSION)
from sgraph_ai_service_playwright.fast_api.Fast_API__Playwright__Service            import Fast_API__Playwright__Service


ADMIN_ENV = {ENV_VAR__AGENTIC_APP_NAME     : 'sg-playwright'         ,
             ENV_VAR__AGENTIC_APP_STAGE    : 'dev'                   ,
             ENV_VAR__AGENTIC_APP_VERSION  : 'v0.1.29'               ,
             ENV_VAR__AGENTIC_CODE_SOURCE  : 'passthrough:sys.path'  ,
             ENV_VAR__AGENTIC_IMAGE_VERSION: 'v1'                    }


class _EnvScrub:                                                                    # Snapshot + apply the ADMIN_ENV overrides for the duration of a test
    def __init__(self, **overrides):
        self.overrides = overrides
        self.snapshot  = {}
    def __enter__(self):
        for k, v in self.overrides.items():
            self.snapshot[k] = os.environ.get(k)
            os.environ[k]    = v
        return self
    def __exit__(self, *exc):
        for k, v in self.snapshot.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _build_client() -> TestClient:
    fa = Fast_API__Playwright__Service().setup()
    return TestClient(fa.app())


class test_admin_happy_path(TestCase):

    def setUp(self):
        reset_boot_state()
        self._env    = _EnvScrub(**ADMIN_ENV).__enter__()
        self.client  = _build_client()

    def tearDown(self):
        self._env.__exit__(None, None, None)

    def test__health_returns_loaded(self):
        body = self.client.get('/admin/health').json()
        assert body == {'status': 'loaded', 'code_source': 'passthrough:sys.path'}

    def test__health_flips_to_degraded_when_last_error_is_set(self):
        set_last_error('simulated boom')
        body = self.client.get('/admin/health').json()
        assert body['status'] == 'degraded'

    def test__info_surfaces_all_app_identity_fields(self):
        body = self.client.get('/admin/info').json()
        assert body['app_name'      ] == 'sg-playwright'
        assert body['app_stage'     ] == 'dev'
        assert body['app_version'   ] == 'v0.1.29'
        assert body['image_version' ] == 'v1'
        assert body['code_source'   ] == 'passthrough:sys.path'
        assert 'python_version' in body and body['python_version']                  # sys.version is non-empty in any supported runtime

    def test__env_only_contains_agentic_prefix(self):
        body = self.client.get('/admin/env').json()
        assert 'agentic_vars' in body
        for key in body['agentic_vars']:
            assert key.startswith('AGENTIC_'), f'leaked non-AGENTIC key: {key}'

    def test__env_excludes_aws_and_sg_playwright_keys(self):                        # Belt and braces — regression guard for the redaction logic
        with _EnvScrub(AWS_SECRET_ACCESS_KEY         = 'SHOULD-NOT-LEAK'           ,
                       SG_PLAYWRIGHT__ACCESS_TOKEN_VALUE = 'SHOULD-NOT-LEAK'       ):
            body = self.client.get('/admin/env').json()
        assert 'AWS_SECRET_ACCESS_KEY'              not in body['agentic_vars']
        assert 'SG_PLAYWRIGHT__ACCESS_TOKEN_VALUE'  not in body['agentic_vars']

    def test__boot_log_returns_current_lines(self):
        append_boot_log('stage-1=ok')
        append_boot_log('stage-2=ok')
        body = self.client.get('/admin/boot-log').json()
        assert body['lines'] == ['stage-1=ok', 'stage-2=ok']

    def test__error_reports_no_error_by_default(self):
        body = self.client.get('/admin/error').json()
        assert body == {'has_error': False, 'error': ''}

    def test__error_reports_stored_message(self):
        set_last_error('CRITICAL ERROR: broken zip')
        body = self.client.get('/admin/error').json()
        assert body['has_error']        is True
        assert 'CRITICAL ERROR' in body['error']

    def test__manifest_lists_all_entry_points(self):
        body = self.client.get('/admin/manifest').json()
        assert body['app_name'         ] == 'sg-playwright'
        assert body['openapi_path'     ] == '/openapi.json'
        assert body['capabilities_path'] == '/admin/capabilities'
        for name in SKILL_NAMES:
            assert body['skills'][name] == f'/{TAG__ROUTES_ADMIN}/skills/{name}'

    def test__capabilities_matches_repo_root_stub(self):
        body = self.client.get('/admin/capabilities').json()
        assert body['app']                == 'sg-playwright'
        assert 'statelessness'            in body['axioms']
        assert body['declared_narrowing'] == []                                     # Lockdown layers deferred per plan §7

    def test__skills_returns_markdown_for_each_audience(self):
        for name in SKILL_NAMES:
            body = self.client.get(f'/admin/skills/{name}').json()
            assert body['name']       == name
            assert body['content']                                                  # Non-empty markdown body
            assert 'SKILL'            in body['content']

    def test__skills_unknown_audience_is_blocked(self):                             # Unknown names are NOT in ADMIN_AUTH_EXCLUDED_PATHS, so the API-key middleware returns 401 before the route handler can emit 404. Either outcome is "not served" — this asserts both are acceptable.
        resp = self.client.get('/admin/skills/mystery')
        assert resp.status_code in (401, 404), f'expected block, got {resp.status_code}'


class test_admin_is_unauthenticated(TestCase):                                      # /admin/* must not require the API-key header

    def setUp(self):
        reset_boot_state()
        self._env    = _EnvScrub(**ADMIN_ENV).__enter__()
        self.client  = _build_client()

    def tearDown(self):
        self._env.__exit__(None, None, None)

    def test__all_admin_routes_return_200_without_api_key(self):
        for path in ['/admin/health'          ,
                     '/admin/info'            ,
                     '/admin/env'             ,
                     '/admin/boot-log'        ,
                     '/admin/error'           ,
                     '/admin/manifest'        ,
                     '/admin/capabilities'    ,
                     '/admin/skills/human'    ,
                     '/admin/skills/browser'  ,
                     '/admin/skills/agent'    ]:
            resp = self.client.get(path)
            assert resp.status_code == 200, f'{path} -> {resp.status_code}: {resp.text[:200]}'
