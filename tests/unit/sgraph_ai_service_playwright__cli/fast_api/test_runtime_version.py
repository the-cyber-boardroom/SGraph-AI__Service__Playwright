# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for runtime_version
# Asserts the resolution order: env var > image version file > fallback. No
# AWS / no Lambda — pure stdlib.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from pathlib                                                                        import Path
from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.fast_api.runtime_version                     import (resolve_version            ,
                                                                                            ENV_VAR__AGENTIC_APP_VERSION,
                                                                                            IMAGE_VERSION_FILE_RELATIVE ,
                                                                                            VERSION_FALLBACK            )


class test_runtime_version(TestCase):

    def setUp(self):
        self.preserved_env = os.environ.pop(ENV_VAR__AGENTIC_APP_VERSION, None)     # Isolate from a stray env on the runner

    def tearDown(self):
        if self.preserved_env is not None:
            os.environ[ENV_VAR__AGENTIC_APP_VERSION] = self.preserved_env
        else:
            os.environ.pop(ENV_VAR__AGENTIC_APP_VERSION, None)

    def test__env_var_wins(self):                                                   # Agentic Lambda: AGENTIC_APP_VERSION pinned by Lambda__SP__CLI must be the source of truth
        os.environ[ENV_VAR__AGENTIC_APP_VERSION] = 'v9.9.9'
        assert resolve_version() == 'v9.9.9'

    def test__env_var_blank_falls_through(self):                                    # Empty / whitespace env var should not be treated as an explicit pin
        os.environ[ENV_VAR__AGENTIC_APP_VERSION] = '   '
        assert resolve_version() != '   '
        assert resolve_version().startswith('v')

    def test__falls_back_to_repo_version_file(self):                                # No env var: locally we should pick up sgraph_ai_service_playwright/version
        repo_root = Path(__file__).resolve().parents[4]
        file_text = (repo_root / IMAGE_VERSION_FILE_RELATIVE).read_text().strip()
        assert resolve_version() == file_text

    def test__fallback_constant_format(self):                                       # The hardcoded fallback must look like a version (Safe_Str__Version regex starts with 'v')
        assert VERSION_FALLBACK.startswith('v')
        assert VERSION_FALLBACK == 'v0.0.0'
