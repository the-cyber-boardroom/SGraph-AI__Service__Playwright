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


class test_OpenSearch__AWS__Client__skeleton(TestCase):

    def test__instantiates_cleanly(self):                                           # Class is currently empty; methods land in Phase B step 5c
        client = OpenSearch__AWS__Client()
        assert client is not None
