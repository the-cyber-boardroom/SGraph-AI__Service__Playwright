# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Linux__AWS__Client (composition shell, pure structure)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.linux.service.Linux__AWS__Client             import (Linux__AWS__Client,
                                                                                              LINUX_NAMING      ,
                                                                                              TAG_PURPOSE_VALUE ,
                                                                                              TAG_SECTION_VALUE )


class test_Linux__AWS__Client(TestCase):

    def test_naming_constants(self):
        assert LINUX_NAMING.section_prefix == 'linux'
        assert TAG_PURPOSE_VALUE           == 'linux'
        assert TAG_SECTION_VALUE           == 'linux'

    def test_aws_name_for_stack__adds_prefix_when_missing(self):
        assert LINUX_NAMING.aws_name_for_stack('happy-turing') == 'linux-happy-turing'

    def test_aws_name_for_stack__does_not_double_prefix(self):
        assert LINUX_NAMING.aws_name_for_stack('linux-happy-turing') == 'linux-happy-turing'

    def test_sg_name_for_stack__uses_suffix(self):                                  # AWS rejects GroupName starting with 'sg-'
        sg_name = LINUX_NAMING.sg_name_for_stack('happy-turing')
        assert sg_name == 'happy-turing-sg'
        assert not sg_name.startswith('sg-')

    def test_setup_returns_self(self):                                               # Lazy imports — just verify setup() doesn't crash and returns the client
        client = Linux__AWS__Client().setup()
        assert client is not None
        assert client.sg       is not None
        assert client.ami      is not None
        assert client.instance is not None
        assert client.tags     is not None
        assert client.launch   is not None
