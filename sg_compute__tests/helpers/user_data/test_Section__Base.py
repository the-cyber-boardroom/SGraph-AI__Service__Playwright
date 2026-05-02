# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Section__Base
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute.platforms.ec2.user_data.Section__Base import Section__Base


class test_Section__Base(TestCase):

    def test_render__starts_with_shebang(self):
        out = Section__Base().render('my-stack')
        assert out.startswith('#!/usr/bin/env bash')

    def test_render__contains_stack_name(self):
        out = Section__Base().render('quiet-fermi')
        assert 'quiet-fermi' in out

    def test_render__strict_mode(self):
        out = Section__Base().render('x')
        assert 'set -euo pipefail' in out

    def test_render__installs_essentials(self):
        out = Section__Base().render('x')
        assert 'dnf install -y git curl jq unzip' in out

    def test_render__ssm_agent(self):
        out = Section__Base().render('x')
        assert 'amazon-ssm-agent' in out
