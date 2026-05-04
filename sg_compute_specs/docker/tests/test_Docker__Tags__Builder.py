# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Docker: tests for Docker__Tags__Builder
# Pure mapper — no AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute_specs.docker.service.Docker__AWS__Client                            import (TAG_ALLOWED_IP_KEY,
                                                                                              TAG_CREATOR_KEY   ,
                                                                                              TAG_PURPOSE_KEY   ,
                                                                                              TAG_PURPOSE_VALUE ,
                                                                                              TAG_SECTION_KEY   ,
                                                                                              TAG_SECTION_VALUE ,
                                                                                              TAG_STACK_NAME_KEY)
from sg_compute_specs.docker.service.Docker__Tags__Builder                          import Docker__Tags__Builder


class test_Docker__Tags__Builder(TestCase):

    def setUp(self):
        self.builder = Docker__Tags__Builder()

    def test_build__name_tag_carries_docker_prefix(self):
        tags    = self.builder.build('fast-fermi', '1.2.3.4', 'tester@example.com')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict['Name'] == 'docker-fast-fermi'

    def test_build__name_tag_does_not_double_prefix(self):
        tags    = self.builder.build('docker-fast-fermi', '1.2.3.4')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict['Name'] == 'docker-fast-fermi'

    def test_build__includes_full_tag_set(self):
        tags    = self.builder.build('cool-newton', '10.0.0.1', 'dev@example.com')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict[TAG_PURPOSE_KEY]    == TAG_PURPOSE_VALUE
        assert as_dict[TAG_SECTION_KEY]    == TAG_SECTION_VALUE
        assert as_dict[TAG_STACK_NAME_KEY] == 'cool-newton'
        assert as_dict[TAG_ALLOWED_IP_KEY] == '10.0.0.1'
        assert as_dict[TAG_CREATOR_KEY]    == 'dev@example.com'

    def test_build__purpose_and_section_are_docker(self):
        tags    = self.builder.build('x-foo', '1.2.3.4', '')
        as_dict = {t['Key']: t['Value'] for t in tags}
        assert as_dict[TAG_PURPOSE_KEY] == 'docker'
        assert as_dict[TAG_SECTION_KEY] == 'docker'

    def test_build__sg_name_never_starts_with_sg_prefix(self):
        from sg_compute_specs.docker.service.Docker__AWS__Client import DOCKER_NAMING
        sg_name = DOCKER_NAMING.sg_name_for_stack('fast-fermi')
        assert not sg_name.startswith('sg-')
        assert sg_name == 'fast-fermi-sg'
