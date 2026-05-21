# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Cli__CF__Iam
# Drives the Typer app with an injected in-memory provisioner (Fake__IAM). Covers
# show/plan rendering, the mutation gate on create/delete, and the create→in-sync flow.
# No AWS, no TTY. ctx.obj is seeded via CliRunner's obj= passthrough.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest import TestCase

from typer.testing import CliRunner

from sgraph_ai_service_playwright__cli.aws._shared.auth                            import AWS__Role__Profiles as profiles
from sgraph_ai_service_playwright__cli.aws._shared.auth.AWS__Role__Provisioner     import AWS__Role__Provisioner
from sgraph_ai_service_playwright__cli.aws._shared.auth.tests.test_AWS__Role__Provisioner import Fake__IAM
from sgraph_ai_service_playwright__cli.elastic.lets.cf.iam.cli.Cli__CF__Iam        import iam_app


class test_Cli__CF__Iam(TestCase):

    def setUp(self):
        self.runner = CliRunner()
        self.prov   = AWS__Role__Provisioner(iam=Fake__IAM(), account_id='123456789012')
        os.environ.pop('SG_AWS__IAM__ALLOW_MUTATIONS', None)

    def _invoke(self, args):
        return self.runner.invoke(iam_app, args, obj={'provisioner': self.prov})

    def test_show_json(self):
        r = self._invoke(['show', '--json'])
        assert r.exit_code == 0
        assert 'sg-lets-cf'                  in r.output
        assert 's3:GetObject'                in r.output

    def test_plan_absent(self):
        r = self._invoke(['plan'])
        assert r.exit_code == 0
        assert 'does not exist' in r.output
        assert '+ s3:GetObject' in r.output

    def test_create_gated_off(self):
        r = self._invoke(['create', '--yes'])
        assert r.exit_code == 1
        assert 'SG_AWS__IAM__ALLOW_MUTATIONS' in r.output

    def test_create_then_in_sync(self):
        os.environ['SG_AWS__IAM__ALLOW_MUTATIONS'] = '1'
        try:
            r = self._invoke(['create', '--yes'])
            assert r.exit_code == 0, r.output
            assert 'Created sg-lets-cf' in r.output
            r2 = self._invoke(['plan'])
            assert 'in_sync=True' in r2.output
        finally:
            os.environ.pop('SG_AWS__IAM__ALLOW_MUTATIONS', None)

    def test_dry_run_create_makes_no_changes(self):
        r = self._invoke(['create', '--dry-run'])
        assert r.exit_code == 0
        assert self.prov.plan(profiles.get_profile('el-lets-cf')).exists is False

    def test_delete_gated_off(self):
        r = self._invoke(['delete', '--yes'])
        assert r.exit_code == 1
        assert 'SG_AWS__IAM__ALLOW_MUTATIONS' in r.output
