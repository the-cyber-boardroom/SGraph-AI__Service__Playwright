# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Deploy__SP__CLI__Code
# Covers the module surface + version-file resolution. Actual S3 upload /
# Lambda env flip is exercised by scripts.deploy_code (already unit-tested)
# + real CI against live AWS.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.deploy                               import deploy_code as sp_cli_deploy_code
from sgraph_ai_service_playwright__cli.deploy.deploy_code                   import (Deploy__SP__CLI__Code,
                                                                                    PACKAGE_NAMES        ,
                                                                                    VERSION_FILE_RELATIVE,
                                                                                    read_version         )


class test_module_surface(TestCase):

    def test__exposes_entry_class_and_helpers(self):
        for attr in ('Deploy__SP__CLI__Code', 'PACKAGE_NAMES', 'VERSION_FILE_RELATIVE',
                     'read_version'        , 'main'          ):
            assert hasattr(sp_cli_deploy_code, attr), f'missing: {attr}'

    def test__package_names_are_the_three_hot_swap_trees(self):                     # Locked — the zip MUST contain all three trees so the agentic Lambda has every import path it needs (CLI tree, scripts/, agent_mitmproxy for IMAGE_NAME)
        assert PACKAGE_NAMES == ['sgraph_ai_service_playwright__cli', 'scripts', 'agent_mitmproxy']

    def test__version_file_is_shared_with_main_service(self):                       # Single source of truth — the CLI inherits the main Playwright service version
        assert VERSION_FILE_RELATIVE == 'sgraph_ai_service_playwright/version'


class test_read_version(TestCase):

    def test__reads_the_shared_version_file(self):                                  # File exists in repo-root — should match its contents (stripped)
        value = read_version()
        assert value                                                                # Non-empty
        assert value.startswith('v')                                                # Follows Safe_Str__Version convention

    def test__value_matches_shared_version_file_exactly(self):
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[4]                             # tests/unit/.../deploy/test_deploy_code.py → repo root (4 parents up)
        assert (repo_root / 'pyproject.toml').is_file()                             # Sanity — we located the repo root
        file_value = (repo_root / VERSION_FILE_RELATIVE).read_text().strip()
        assert read_version() == file_value


class test_Deploy__SP__CLI__Code(TestCase):

    def test__construction_is_side_effect_free(self):                               # Type_Safe construction — no network, no S3
        Deploy__SP__CLI__Code()                                                     # Must not raise
