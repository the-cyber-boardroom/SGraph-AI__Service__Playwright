# ═══════════════════════════════════════════════════════════════════════════════
# ephemeral_ec2 tests — Stack__Name__Generator
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from ephemeral_ec2.helpers.networking.Stack__Name__Generator import Stack__Name__Generator


class test_Stack__Name__Generator(TestCase):

    def test_generate__returns_hyphenated_string(self):
        name = Stack__Name__Generator().generate()
        assert '-' in name
        parts = name.split('-')
        assert len(parts) == 2

    def test_generate__all_lowercase(self):
        name = Stack__Name__Generator().generate()
        assert name == name.lower()

    def test_generate__produces_variety(self):
        gen   = Stack__Name__Generator()
        names = {gen.generate() for _ in range(20)}
        assert len(names) > 1                                                       # should not always produce the same name
