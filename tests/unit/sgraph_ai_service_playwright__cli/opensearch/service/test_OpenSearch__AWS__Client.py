# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for OpenSearch__AWS__Client
# Phase B step 5a covers only the OS_NAMING binding + tag constants. AWS-touching
# methods + their tests land in step 5c.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.aws.Stack__Naming                            import Stack__Naming
from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__AWS__Client           import (OS_NAMING                ,
                                                                                              OpenSearch__AWS__Client  ,
                                                                                              TAG_ALLOWED_IP_KEY       ,
                                                                                              TAG_CREATOR_KEY          ,
                                                                                              TAG_PURPOSE_KEY          ,
                                                                                              TAG_PURPOSE_VALUE        ,
                                                                                              TAG_SECTION_KEY          ,
                                                                                              TAG_SECTION_VALUE        ,
                                                                                              TAG_STACK_NAME_KEY       )


class test_OS_NAMING(TestCase):

    def test__is_a_Stack__Naming_instance(self):
        assert isinstance(OS_NAMING, Stack__Naming)

    def test__section_prefix_is_opensearch(self):
        assert str(OS_NAMING.section_prefix) == 'opensearch'

    def test__aws_name_for_stack__adds_opensearch_prefix(self):
        assert OS_NAMING.aws_name_for_stack('quiet-fermi') == 'opensearch-quiet-fermi'

    def test__aws_name_for_stack__never_doubles_prefix(self):
        assert OS_NAMING.aws_name_for_stack('opensearch-prod') == 'opensearch-prod'

    def test__sg_name_for_stack__appends_sg_suffix(self):
        assert OS_NAMING.sg_name_for_stack('quiet-fermi') == 'quiet-fermi-sg'


class test_tag_constants(TestCase):

    def test__purpose_value_is_opensearch(self):                                    # find_stacks (future) filters on this; keep stable
        assert TAG_PURPOSE_VALUE == 'opensearch'
        assert TAG_PURPOSE_KEY   == 'sg:purpose'

    def test__section_value_is_short_alias(self):                                   # 'os' matches the typer subcommand short alias
        assert TAG_SECTION_VALUE == 'os'
        assert TAG_SECTION_KEY   == 'sg:section'

    def test__namespace_keys_are_sg_prefixed(self):                                 # Every per-stack tag uses the sg: prefix
        for key in (TAG_PURPOSE_KEY, TAG_STACK_NAME_KEY, TAG_ALLOWED_IP_KEY, TAG_CREATOR_KEY, TAG_SECTION_KEY):
            assert key.startswith('sg:'), f'{key} must use the sg: namespace'


class test_OpenSearch__AWS__Client__composition(TestCase):                          # Phase B step 5c — composes the per-concern helpers

    def test__instantiates_with_helpers_unset(self):
        client = OpenSearch__AWS__Client()
        assert client.sg       is None
        assert client.ami      is None
        assert client.instance is None
        assert client.tags     is None

    def test__setup_wires_all_four_helpers(self):
        from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__SG__Helper       import OpenSearch__SG__Helper
        from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__AMI__Helper      import OpenSearch__AMI__Helper
        from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__Instance__Helper import OpenSearch__Instance__Helper
        from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__Tags__Builder    import OpenSearch__Tags__Builder

        client = OpenSearch__AWS__Client().setup()
        assert isinstance(client.sg      , OpenSearch__SG__Helper      )
        assert isinstance(client.ami     , OpenSearch__AMI__Helper     )
        assert isinstance(client.instance, OpenSearch__Instance__Helper)
        assert isinstance(client.tags    , OpenSearch__Tags__Builder   )

    def test__setup_returns_self_for_chaining(self):                                # Mirrors Docker__SP__CLI().setup() / Elastic patterns
        client = OpenSearch__AWS__Client()
        assert client.setup() is client
