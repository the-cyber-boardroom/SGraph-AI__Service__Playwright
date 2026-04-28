# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Prometheus__AWS__Client
# Phase B step 6a covered PROM_NAMING + tag constants. Step 6c wires the four
# per-concern helpers via setup(); Launch__Helper joins in step 6f.4a.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.aws.Stack__Naming                            import Stack__Naming
from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__AMI__Helper   import Prometheus__AMI__Helper
from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__AWS__Client   import (PROM_NAMING            ,
                                                                                              Prometheus__AWS__Client,
                                                                                              TAG_ALLOWED_IP_KEY     ,
                                                                                              TAG_CREATOR_KEY        ,
                                                                                              TAG_PURPOSE_KEY        ,
                                                                                              TAG_PURPOSE_VALUE      ,
                                                                                              TAG_SECTION_KEY        ,
                                                                                              TAG_SECTION_VALUE      ,
                                                                                              TAG_STACK_NAME_KEY     )
from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__Instance__Helper import Prometheus__Instance__Helper
from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__SG__Helper    import Prometheus__SG__Helper
from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__Tags__Builder import Prometheus__Tags__Builder


class test_PROM_NAMING(TestCase):

    def test__is_a_Stack__Naming_instance(self):
        assert isinstance(PROM_NAMING, Stack__Naming)

    def test__section_prefix_is_prometheus(self):
        assert str(PROM_NAMING.section_prefix) == 'prometheus'

    def test__aws_name_for_stack__adds_prometheus_prefix(self):
        assert PROM_NAMING.aws_name_for_stack('quiet-fermi') == 'prometheus-quiet-fermi'

    def test__aws_name_for_stack__never_doubles_prefix(self):
        assert PROM_NAMING.aws_name_for_stack('prometheus-prod') == 'prometheus-prod'

    def test__sg_name_for_stack__appends_sg_suffix(self):
        assert PROM_NAMING.sg_name_for_stack('quiet-fermi') == 'quiet-fermi-sg'


class test_tag_constants(TestCase):

    def test__purpose_value_is_prometheus(self):
        assert TAG_PURPOSE_VALUE == 'prometheus'
        assert TAG_PURPOSE_KEY   == 'sg:purpose'

    def test__section_value_is_short_alias(self):                                   # 'prom' matches the typer subcommand short alias
        assert TAG_SECTION_VALUE == 'prom'
        assert TAG_SECTION_KEY   == 'sg:section'

    def test__namespace_keys_are_sg_prefixed(self):
        for key in (TAG_PURPOSE_KEY, TAG_STACK_NAME_KEY, TAG_ALLOWED_IP_KEY, TAG_CREATOR_KEY, TAG_SECTION_KEY):
            assert key.startswith('sg:'), f'{key} must use the sg: namespace'


class test_Prometheus__AWS__Client(TestCase):

    def test__instantiates_cleanly(self):
        client = Prometheus__AWS__Client()
        assert client is not None
        assert client.sg       is None                                              # Helpers are None until setup() runs
        assert client.ami      is None
        assert client.instance is None
        assert client.tags     is None

    def test__setup_wires_all_four_helpers(self):
        client = Prometheus__AWS__Client().setup()
        assert isinstance(client.sg      , Prometheus__SG__Helper      )
        assert isinstance(client.ami     , Prometheus__AMI__Helper     )
        assert isinstance(client.instance, Prometheus__Instance__Helper)
        assert isinstance(client.tags    , Prometheus__Tags__Builder   )

    def test__setup_returns_self_for_chaining(self):                                # Allows `Prometheus__AWS__Client().setup()` one-liner
        client   = Prometheus__AWS__Client()
        returned = client.setup()
        assert returned is client
