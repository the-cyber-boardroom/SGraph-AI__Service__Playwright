# ═══════════════════════════════════════════════════════════════════════════════
# CI guard — test_no_legacy_imports
# Fails if any file under sg_compute/ or sg_compute_specs/ imports from the
# legacy sgraph_ai_service_playwright* tree. BV2.7 broke the cycle; this
# guard prevents regression.
# ═══════════════════════════════════════════════════════════════════════════════

import pathlib
import re


_OBJECT_NONE_ALLOWLIST = {
    # osbot_docker.Docker_Container not installed in this env; cannot type without adding a dev dep
    'sg_compute_specs/playwright/core/docker/Local__Docker__SGraph_AI__Service__Playwright.py',
}


def test_no_object_none_annotations():
    pattern   = re.compile(r':\s*object\s*=\s*None')
    offenders = []
    for root in [pathlib.Path('sg_compute'), pathlib.Path('sg_compute_specs')]:
        for py_file in root.rglob('*.py'):
            key = str(py_file)
            if key in _OBJECT_NONE_ALLOWLIST:
                continue
            if pattern.search(py_file.read_text()):
                offenders.append(key)
    assert not offenders, '`object = None` annotations found (use Optional[T] = None):\n' + '\n'.join(offenders)


def test_sg_compute_does_not_import_legacy():
    legacy_pattern = re.compile(
        r'from\s+sgraph_ai_service_playwright[^_]|import\s+sgraph_ai_service_playwright[^_]'
    )
    offenders = []
    for root in [pathlib.Path('sg_compute'), pathlib.Path('sg_compute_specs')]:
        for py_file in root.rglob('*.py'):
            if legacy_pattern.search(py_file.read_text()):
                offenders.append(str(py_file))
    assert not offenders, f"Legacy imports found in new tree:\n" + "\n".join(offenders)
