# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Cli__Sentinel mounting
# Confirms `sg sentinel` is a real top-level peer surface with a working --help,
# and that the hidden `sn` alias resolves to the same app.
# ═══════════════════════════════════════════════════════════════════════════════

from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.sentinel.cli.Cli__Sentinel import app as sentinel_app


def test_sentinel_help_works():
    result = CliRunner().invoke(sentinel_app, ['--help'])
    assert result.exit_code == 0
    assert 'SG/Sentinel' in result.output


def test_mounted_in_root_sg_app():
    from sg_compute.cli.Cli__SG import app as sg_app
    names = {g.name for g in sg_app.registered_groups}
    assert 'sentinel' in names
    assert 'sn'       in names
