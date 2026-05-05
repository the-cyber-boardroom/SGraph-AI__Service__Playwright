# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Cli__Firefox (per-spec CLI, T2.2)
# All tests use CliRunner — no AWS calls, no network.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from typer.testing                                                                  import CliRunner

from sg_compute_specs.firefox.cli.Cli__Firefox                                      import app


class test_Cli__Firefox(TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_no_args_shows_help(self):
        result = self.runner.invoke(app, ['--help'])
        assert result.exit_code == 0
        assert 'list'             in result.output
        assert 'info'             in result.output
        assert 'create'           in result.output
        assert 'delete'           in result.output
        assert 'set-credentials'  in result.output
        assert 'upload-mitm-script' in result.output

    def test_list_help(self):
        result = self.runner.invoke(app, ['list', '--help'])
        assert result.exit_code == 0
        assert 'region' in result.output

    def test_info_help(self):
        result = self.runner.invoke(app, ['info', '--help'])
        assert result.exit_code == 0
        assert 'stack-name' in result.output or 'STACK_NAME' in result.output

    def test_create_help(self):
        result = self.runner.invoke(app, ['create', '--help'])
        assert result.exit_code == 0
        assert 'region'        in result.output
        assert 'instance-type' in result.output
        assert 'max-hours'     in result.output

    def test_delete_help(self):
        result = self.runner.invoke(app, ['delete', '--help'])
        assert result.exit_code == 0
        assert 'stack-name' in result.output or 'STACK_NAME' in result.output
        assert 'yes'        in result.output

    def test_set_credentials_help(self):
        result = self.runner.invoke(app, ['set-credentials', '--help'])
        assert result.exit_code == 0
        assert 'node'     in result.output
        assert 'username' in result.output
        assert 'password' in result.output

    def test_upload_mitm_script_help(self):
        result = self.runner.invoke(app, ['upload-mitm-script', '--help'])
        assert result.exit_code == 0
        assert 'node' in result.output
        assert 'file' in result.output

    def test_set_credentials_raises_not_implemented(self):
        result = self.runner.invoke(app, ['set-credentials',
                                          '--node', 'ff-node-001',
                                          '--username', 'admin',
                                          '--password', 'secret'])
        assert result.exit_code != 0
        assert 'NotImplementedError' in str(result.exception) or \
               'T2.2b' in str(result.exception)

    def test_upload_mitm_script_raises_not_implemented(self):
        result = self.runner.invoke(app, ['upload-mitm-script',
                                          '--node', 'ff-node-001',
                                          '--file', '/tmp/script.py'])
        assert result.exit_code != 0
        assert 'NotImplementedError' in str(result.exception) or \
               'T2.2b' in str(result.exception)

    def test_dispatcher_loads_firefox_app(self):
        from sg_compute.cli.Spec__CLI__Loader import Spec__CLI__Loader
        loader      = Spec__CLI__Loader()
        loaded_app  = loader.load('firefox')
        assert loaded_app is not None
        cmd_names   = [c.name or c.callback.__name__ for c in loaded_app.registered_commands]
        assert 'set-credentials'   in cmd_names
        assert 'upload-mitm-script' in cmd_names
