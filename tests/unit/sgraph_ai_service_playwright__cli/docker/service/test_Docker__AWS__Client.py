# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Docker__AWS__Client (composition shell, pure structure)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.docker.service.Docker__AWS__Client           import (Docker__AWS__Client,
                                                                                              DOCKER_NAMING     ,
                                                                                              TAG_PURPOSE_VALUE ,
                                                                                              TAG_SECTION_VALUE )


class test_Docker__AWS__Client(TestCase):

    def test_naming_constants(self):
        assert DOCKER_NAMING.section_prefix == 'docker'
        assert TAG_PURPOSE_VALUE            == 'docker'
        assert TAG_SECTION_VALUE            == 'docker'

    def test_aws_name_for_stack__adds_prefix_when_missing(self):
        assert DOCKER_NAMING.aws_name_for_stack('fast-fermi') == 'docker-fast-fermi'

    def test_aws_name_for_stack__does_not_double_prefix(self):
        assert DOCKER_NAMING.aws_name_for_stack('docker-fast-fermi') == 'docker-fast-fermi'

    def test_sg_name_for_stack__uses_suffix(self):
        sg_name = DOCKER_NAMING.sg_name_for_stack('fast-fermi')
        assert sg_name == 'fast-fermi-sg'
        assert not sg_name.startswith('sg-')

    def test_setup_returns_self(self):
        client = Docker__AWS__Client().setup()
        assert client is not None
        assert client.sg       is not None
        assert client.ami      is not None
        assert client.instance is not None
        assert client.tags     is not None
        assert client.launch   is not None
