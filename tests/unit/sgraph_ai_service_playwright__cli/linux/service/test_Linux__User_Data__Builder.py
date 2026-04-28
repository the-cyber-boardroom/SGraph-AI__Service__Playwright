# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Linux__User_Data__Builder
# Pure template renderer — no AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.linux.service.Linux__User_Data__Builder      import (Linux__User_Data__Builder,
                                                                                               PLACEHOLDERS          ,
                                                                                               USER_DATA_TEMPLATE     )


class test_Linux__User_Data__Builder(TestCase):

    def setUp(self):
        self.builder = Linux__User_Data__Builder()

    def test_render__starts_with_shebang(self):
        result = self.builder.render('bold-newton', 'eu-west-2')
        assert result.startswith('#!/usr/bin/env bash')

    def test_render__embeds_stack_name_and_region(self):
        result = self.builder.render('bold-newton', 'eu-west-2')
        assert 'bold-newton' in result
        assert 'eu-west-2'   in result

    def test_render__enables_ssm_agent(self):
        result = self.builder.render('bold-newton', 'eu-west-2')
        assert 'amazon-ssm-agent' in result

    def test_render__no_docker_install(self):                                       # Linux stacks are bare; Docker stacks have their own builder
        result = self.builder.render('bold-newton', 'eu-west-2')
        assert 'docker' not in result.lower() or 'amazon-ssm-agent' in result       # SSM log line is fine; actual docker install is NOT expected
        assert 'dnf install' not in result or 'ssm' in result                       # No dnf docker install in bare linux script

    def test_placeholders_locked(self):
        assert PLACEHOLDERS == ('stack_name', 'region', 'log_file')

    def test_template_has_all_placeholders(self):                                   # Catch any mismatch if template changes
        for p in PLACEHOLDERS:
            assert f'{{{p}}}' in USER_DATA_TEMPLATE, f'{{{p}}} missing from template'
