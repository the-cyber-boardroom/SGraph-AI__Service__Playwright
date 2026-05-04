# ═══════════════════════════════════════════════════════════════════════════════
# Tests — scripts/package_code.py (v0.1.28 — S3-zip hot-swap)
#
# Scope (unit-level, no real AWS):
#   • build_code_zip() — packages the sgraph_ai_service_playwright/ source,
#     includes .py files, excludes non-Python noise, and the archive is not empty.
#   • main() surface — the module is importable and exposes the CLI + deploy_code.
#
# We do NOT call resolve_bucket_name() or deploy_code() here — those hit sts /
# S3. End-to-end upload verification lives in tests/deploy/.
# ═══════════════════════════════════════════════════════════════════════════════

import io
import zipfile
from unittest                                                                       import TestCase

from scripts                                                                 import package_code


class test_build_code_zip(TestCase):

    def test__packages_the_service_source(self):
        zb        = package_code.build_code_zip()
        assert len(zb.zip_bytes) > 1000                                             # Sanity — the package has dozens of modules

        with zipfile.ZipFile(io.BytesIO(zb.zip_bytes), 'r') as zf:
            names = zf.namelist()
        assert any(n == 'sgraph_ai_service_playwright/consts/version.py'               for n in names)   # Locks the zip shape — package prefix MUST be present so `import sgraph_ai_service_playwright.consts.version` resolves after sys.path.insert on the extract dir
        assert any(n == 'sgraph_ai_service_playwright/service/Capability__Detector.py' for n in names)
        assert all(n.startswith('sgraph_ai_service_playwright/')                       for n in names)
        assert all(n.endswith  ('.py'                            )                     for n in names)
        assert not any('__pycache__' in n                                              for n in names)

    def test__accepts_multiple_package_names(self):                                 # Locks the sibling-app contract: a list of folder names all get zipped in
        zb = package_code.build_code_zip(package_names=['sgraph_ai_service_playwright__cli', 'scripts'])
        with zipfile.ZipFile(io.BytesIO(zb.zip_bytes), 'r') as zf:
            names = zf.namelist()

        assert any(n.startswith('sgraph_ai_service_playwright__cli/') for n in names)
        assert any(n.startswith('scripts/')                           for n in names)
        assert not any(n.startswith('sgraph_ai_service_playwright/')  for n in names)  # Default package NOT included — list overrides
        assert all(n.endswith('.py')                                  for n in names)

    def test__empty_list_falls_back_to_default(self):                               # Belt-and-braces — main(--package) never used = default Playwright package
        zb_none  = package_code.build_code_zip(package_names=None)
        zb_empty = package_code.build_code_zip(package_names=[])
        assert len(zb_none.zip_bytes)  > 1000
        assert len(zb_empty.zip_bytes) > 1000

        with zipfile.ZipFile(io.BytesIO(zb_empty.zip_bytes), 'r') as zf:
            names = zf.namelist()
        assert any(n.startswith('sgraph_ai_service_playwright/')      for n in names)

    def test__multi_package_entries_are_importable(self):                           # Belt-and-braces on the real use case — both prefixes must appear intact
        zb = package_code.build_code_zip(package_names=['sgraph_ai_service_playwright__cli', 'scripts'])
        with zipfile.ZipFile(io.BytesIO(zb.zip_bytes), 'r') as zf:
            names = zf.namelist()
        assert any(n == 'sgraph_ai_service_playwright__cli/fast_api/lambda_handler.py' for n in names)
        assert any(n == 'scripts/provision_ec2.py'                                     for n in names)


class test_module_surface(TestCase):

    def test__exposes_expected_symbols(self):
        for attr in ('build_code_zip', 'deploy_code', 'resolve_bucket_name', 'main',
                     'PACKAGE_NAME'  , 'BUCKET_NAME_FORMAT'  , 'KEY_FORMAT'  , 'DEFAULT_APP_NAME'):
            assert hasattr(package_code, attr), f'missing: {attr}'

    def test__bucket_format_matches_boot_shim(self):
        assert package_code.BUCKET_NAME_FORMAT == '{account_id}--sgraph-ai--{region_name}'

    def test__key_format_matches_boot_shim(self):
        assert package_code.KEY_FORMAT == 'apps/{app_name}/{stage}/{version}.zip'
