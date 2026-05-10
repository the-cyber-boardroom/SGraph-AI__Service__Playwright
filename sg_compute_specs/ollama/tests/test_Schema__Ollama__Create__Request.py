# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Schema__Ollama__Create__Request
# Defaults shifted in v0.2.7: model gpt-oss:20b, ami_base DLAMI, max_hours 1,
# instance_type g5.xlarge.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
from unittest import TestCase

from sg_compute_specs.ollama.enums.Enum__Ollama__AMI__Base           import Enum__Ollama__AMI__Base
from sg_compute_specs.ollama.schemas.Schema__Ollama__Create__Request import Schema__Ollama__Create__Request


class test_Schema__Ollama__Create__Request(TestCase):

    def test_defaults(self):
        req = Schema__Ollama__Create__Request()
        assert req.ami_base       == Enum__Ollama__AMI__Base.DLAMI
        assert str(req.model_name) == 'gpt-oss:20b'
        assert req.with_claude     is False
        assert req.expose_api      is False
        assert int(req.disk_size_gb) == 250
        assert req.max_hours       == 1
        assert req.instance_type   == 'g5.xlarge'

    def test_disk_size_accepts_200(self):
        req = Schema__Ollama__Create__Request(disk_size_gb=200)
        assert int(req.disk_size_gb) == 200

    def test_disk_size_rejects_too_large(self):
        with pytest.raises(Exception):
            Schema__Ollama__Create__Request(disk_size_gb=50000)

    def test_model_regex_accepts_known_names(self):
        for name in ('gpt-oss:20b', 'llama3.3', 'qwen2.5-coder:7b'):
            req = Schema__Ollama__Create__Request()
            req.model_name = name
            assert str(req.model_name) == name

    def test_model_regex_rejects_unsafe(self):
        req = Schema__Ollama__Create__Request()
        for bad in ('../etc/passwd', 'has spaces', 'UPPER'):
            with pytest.raises(Exception):
                req.model_name = bad
