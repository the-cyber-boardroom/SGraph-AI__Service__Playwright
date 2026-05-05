# ═══════════════════════════════════════════════════════════════════════════════
# CI guard — test_no_legacy_imports
# Fails if any file under sg_compute/ or sg_compute_specs/ imports from the
# legacy sgraph_ai_service_playwright* tree. BV2.7 broke the cycle; this
# guard prevents regression.
# ═══════════════════════════════════════════════════════════════════════════════

import pathlib
import re


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
