# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Elastic: tests for Elastic__User_Data__Builder
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute_specs.elastic.primitives.Safe_Str__Elastic__Password                import Safe_Str__Elastic__Password
from sg_compute_specs.elastic.primitives.Safe_Str__Elastic__Stack__Name             import Safe_Str__Elastic__Stack__Name
from sg_compute_specs.elastic.service.Elastic__User_Data__Builder                   import (Elastic__User_Data__Builder,
                                                                                             PLACEHOLDERS              ,
                                                                                             ELASTIC_VERSION           ,
                                                                                             KIBANA_VERSION            ,
                                                                                             ES_JAVA_OPTS              ,
                                                                                             USER_DATA_TEMPLATE        )

SAMPLE_PASSWORD = 'SamplePassword1234567890'


class test_Elastic__User_Data__Builder(TestCase):

    def setUp(self):
        self.builder = Elastic__User_Data__Builder()

    def test_placeholders_are_locked(self):
        expected = ('stack_name', 'elastic_password', 'elastic_version', 'kibana_version',
                    'nginx_version', 'es_java_opts', 'sidecar_section', 'shutdown_section')
        assert PLACEHOLDERS == expected

    def test_template_contains_all_placeholders(self):
        for p in PLACEHOLDERS:
            assert '{' + p + '}' in USER_DATA_TEMPLATE, f'missing placeholder: {p}'

    def test_render_returns_str(self):
        result = self.builder.render(Safe_Str__Elastic__Stack__Name('cool-newton'),
                                     Safe_Str__Elastic__Password   (SAMPLE_PASSWORD))
        assert isinstance(result, str)

    def test_render_substitutes_stack_name(self):
        result = self.builder.render(Safe_Str__Elastic__Stack__Name('cool-newton'),
                                     Safe_Str__Elastic__Password   (SAMPLE_PASSWORD))
        assert 'cool-newton' in result

    def test_render_substitutes_password(self):
        result = self.builder.render(Safe_Str__Elastic__Stack__Name('st'),
                                     Safe_Str__Elastic__Password   (SAMPLE_PASSWORD))
        assert SAMPLE_PASSWORD in result

    def test_render_uses_elastic_version(self):
        result = self.builder.render(Safe_Str__Elastic__Stack__Name('st'),
                                     Safe_Str__Elastic__Password   (SAMPLE_PASSWORD))
        assert ELASTIC_VERSION in result

    def test_render_uses_kibana_version(self):
        result = self.builder.render(Safe_Str__Elastic__Stack__Name('st'),
                                     Safe_Str__Elastic__Password   (SAMPLE_PASSWORD))
        assert KIBANA_VERSION in result

    def test_render_uses_shebang(self):
        result = self.builder.render(Safe_Str__Elastic__Stack__Name('st'),
                                     Safe_Str__Elastic__Password   (SAMPLE_PASSWORD))
        assert result.startswith('#!/bin/bash')

    def test_elastic_version_constant(self):
        assert ELASTIC_VERSION == '8.13.4'

    def test_kibana_version_constant(self):
        assert KIBANA_VERSION == '8.13.4'

    def test_es_java_opts_constant(self):
        assert ES_JAVA_OPTS == '-Xms4g -Xmx4g'
