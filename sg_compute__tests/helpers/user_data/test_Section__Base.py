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
        assert 'dnf install -y --allowerasing git curl jq unzip' in out

    def test_render__ssm_agent(self):
        out = Section__Base().render('x')
        assert 'amazon-ssm-agent' in out

    def test_render__pre_creates_ssm_user(self):
        # ssm-user is created lazily by SSM Session Manager but never by SSM
        # SendCommand. Pre-creating it at boot prevents Section__SGit_Venv /
        # Section__Claude_Code__Firstboot from blocking forever on instances
        # only ever accessed via `sg lc exec`.
        out = Section__Base().render('x')
        assert 'useradd ssm-user' in out
        assert '/home/ssm-user'   in out
