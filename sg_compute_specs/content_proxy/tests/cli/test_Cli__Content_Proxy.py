# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: CLI + Service wiring tests
# Gated on osbot_aws (the EC2 foundation dep) — skips cleanly where absent.
# No AWS calls: only the CLI build + service composition + cli_spec are asserted.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

import pytest

pytest.importorskip('osbot_aws')                                                   # EC2 foundation dep

from sg_compute_specs.content_proxy.cli.Cli__Content_Proxy import app
from sg_compute_specs.content_proxy.service.Content_Proxy__Service import Content_Proxy__Service


class test_Cli__Content_Proxy(TestCase):

    def test_8_standard_verbs_present(self):
        cmds = {c.name or (c.callback.__name__ if c.callback else '') for c in app.registered_commands}
        for verb in ('list', 'info', 'create', 'delete', 'wait', 'health', 'connect', 'exec'):
            assert verb in cmds, verb

    def test_groups_present(self):
        groups = {g.name for g in app.registered_groups}
        assert {'ami', 'cert', 'local'} <= groups                                   # builder groups + our local lifecycle

    def test_local_group_has_up_down_status(self):
        local = [g for g in app.registered_groups if g.name == 'local'][0]
        names = {c.name or '' for c in local.typer_instance.registered_commands}
        assert {'up', 'down', 'status'} <= names


class test_Content_Proxy__Service_wiring(TestCase):

    def test_setup_is_aws_free_and_composes_helpers(self):
        svc = Content_Proxy__Service().setup()
        assert svc.aws_client        is not None
        assert svc.name_gen          is not None
        assert svc.user_data_builder is not None
        assert svc.mapper            is not None

    def test_cli_spec(self):
        sp = Content_Proxy__Service().cli_spec()
        assert sp.spec_id       == 'content_proxy'
        assert sp.health_port   == 443
        assert sp.health_scheme == 'https'

    def test_name_gen_generates(self):
        name = Content_Proxy__Service().setup().name_gen.generate()
        assert '-' in name                                                          # adjective-scientist
