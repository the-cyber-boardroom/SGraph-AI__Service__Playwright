# ═══════════════════════════════════════════════════════════════════════════════
# CI guard — verify sg_compute_specs wheel contains per-spec UI assets (T3.1)
# Catches regressions where the package-data glob is misconfigured and UI files
# silently don't ship to Lambda.
# ═══════════════════════════════════════════════════════════════════════════════

import subprocess
import zipfile
from pathlib import Path

import pytest


def _build_wheel(tmp_path: Path) -> Path:
    result = subprocess.run(
        ['python', '-m', 'build', 'sg_compute_specs/', '--wheel', '--outdir', str(tmp_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(f'wheel build failed:\n{result.stderr}')
    wheels = list(tmp_path.glob('sg_compute_specs-*.whl'))
    if not wheels:
        pytest.fail(f'no wheel found after build in {tmp_path}')
    return wheels[0]


def test_wheel_contains_ui_assets(tmp_path):
    wheel_path = _build_wheel(tmp_path)
    with zipfile.ZipFile(wheel_path) as zf:
        names = zf.namelist()

    ui_files = [n for n in names if '/ui/' in n and n.endswith(('.js', '.html', '.css'))]
    assert ui_files, (
        f'No UI assets found in {wheel_path.name}.\n'
        f'Check sg_compute_specs/pyproject.toml [tool.setuptools.package-data] '
        f'includes "*/ui/**/*".\n'
        f'Wheel contents (first 20): {names[:20]}'
    )

    # Sanity-check that at least one known spec's card JS is present
    card_js = [f for f in ui_files if 'card' in f and f.endswith('.js')]
    assert card_js, (
        f'No card JS found. UI files found: {ui_files[:10]}'
    )
