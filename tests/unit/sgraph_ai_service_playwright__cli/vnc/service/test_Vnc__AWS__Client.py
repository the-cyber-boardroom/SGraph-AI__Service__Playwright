# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Vnc__AWS__Client (skeleton)
# Phase B step 7a covers VNC_NAMING + tag constants only. AWS-touching
# helpers + their tests land in step 7c.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.aws.Stack__Naming                            import Stack__Naming
from sgraph_ai_service_playwright__cli.vnc.service.Vnc__AWS__Client                 import (TAG_ALLOWED_IP_KEY    ,
                                                                                              TAG_CREATOR_KEY       ,
                                                                                              TAG_INTERCEPTOR_KEY   ,
                                                                                              TAG_INTERCEPTOR_NONE  ,
                                                                                              TAG_PURPOSE_KEY       ,
                                                                                              TAG_PURPOSE_VALUE     ,
                                                                                              TAG_SECTION_KEY       ,
                                                                                              TAG_SECTION_VALUE     ,
                                                                                              TAG_STACK_NAME_KEY    ,
                                                                                              VNC_NAMING            ,
                                                                                              Vnc__AWS__Client      )


class test_VNC_NAMING(TestCase):

    def test__is_a_Stack__Naming_instance(self):
        assert isinstance(VNC_NAMING, Stack__Naming)

    def test__section_prefix_is_vnc(self):
        assert str(VNC_NAMING.section_prefix) == 'vnc'

    def test__aws_name_for_stack__adds_vnc_prefix(self):
        assert VNC_NAMING.aws_name_for_stack('quiet-fermi') == 'vnc-quiet-fermi'

    def test__aws_name_for_stack__never_doubles_prefix(self):
        assert VNC_NAMING.aws_name_for_stack('vnc-prod') == 'vnc-prod'

    def test__sg_name_for_stack__appends_sg_suffix(self):
        assert VNC_NAMING.sg_name_for_stack('quiet-fermi') == 'quiet-fermi-sg'


class test_tag_constants(TestCase):

    def test__purpose_value_is_vnc(self):
        assert TAG_PURPOSE_VALUE == 'vnc'
        assert TAG_PURPOSE_KEY   == 'sg:purpose'

    def test__section_value_is_vnc(self):
        assert TAG_SECTION_VALUE == 'vnc'
        assert TAG_SECTION_KEY   == 'sg:section'

    def test__interceptor_constants(self):                                           # N5: 'none' is the default; name:/inline forms set in Tags__Builder
        assert TAG_INTERCEPTOR_KEY  == 'sg:interceptor'
        assert TAG_INTERCEPTOR_NONE == 'none'

    def test__namespace_keys_are_sg_prefixed(self):
        for key in (TAG_PURPOSE_KEY, TAG_STACK_NAME_KEY, TAG_ALLOWED_IP_KEY,
                    TAG_CREATOR_KEY, TAG_SECTION_KEY, TAG_INTERCEPTOR_KEY):
            assert key.startswith('sg:'), f'{key} must use the sg: namespace'


class test_Vnc__AWS__Client__skeleton(TestCase):

    def test__instantiates_cleanly(self):                                           # Methods land in Phase B step 7c
        client = Vnc__AWS__Client()
        assert client is not None
