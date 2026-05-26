# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode: Cli__Vscode tests
# Skips cleanly when the CLI deps (typer/rich/boto3) are not installed.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase, skipUnless

try:
    import typer                                                                # noqa: F401
    from sg_compute_specs.vscode.cli.Cli__Vscode import app, _set_extras
    from sg_compute_specs.vscode.schemas.Schema__Vscode__Create__Request import Schema__Vscode__Create__Request
    from sg_compute_specs.vscode.enums.Enum__Vscode__Distribution        import Enum__Vscode__Distribution
    from sg_compute_specs.vscode.enums.Enum__Vscode__Ingress             import Enum__Vscode__Ingress
    CLI_IMPORTABLE = True
except Exception:
    CLI_IMPORTABLE = False


@skipUnless(CLI_IMPORTABLE, 'CLI deps (typer/rich/boto3) not installed')
class test_Cli__Vscode(TestCase):

    def _command_names(self):
        return {c.name or c.callback.__name__ for c in app.registered_commands}

    def test_app_is_typer(self):
        import typer
        assert isinstance(app, typer.Typer)

    def test_standard_and_extra_verbs_present(self):
        names = self._command_names()
        for verb in ('list', 'info', 'create', 'wait', 'health',
                     'connect', 'exec', 'delete', 'forward', 'url'):
            assert verb in names, f'missing verb: {verb}'

    def test_set_extras_maps_enums(self):
        req = Schema__Vscode__Create__Request()
        _set_extras(req, distribution='serve-web', ingress='public-https',
                    disk_size=250, password='pw', use_spot=False)
        assert req.distribution == Enum__Vscode__Distribution.SERVE_WEB
        assert req.ingress      == Enum__Vscode__Ingress.PUBLIC_HTTPS
        assert int(req.disk_size_gb) == 250
        assert req.password     == 'pw'
        assert req.use_spot     is False
