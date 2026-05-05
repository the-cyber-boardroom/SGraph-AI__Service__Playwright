# ═══════════════════════════════════════════════════════════════════════════════
# Tests — ECR__Docker__SGraph_AI__Service__Playwright
#
# Shape tests + credsStore workaround behaviour (check_for_docker_config_json).
# Actual ECR repo creation + `docker push` lives in the deploy tests under
# tests/docker/test_ECR__Docker__SGraph-AI__Service__Playwright.py.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import tempfile
from unittest                                                                           import TestCase

from osbot_utils.utils.Files                                                            import file_exists
from osbot_utils.utils.Json                                                             import json_save_file

from sg_compute_specs.playwright.core.docker.Docker__SGraph_AI__Service__Playwright__Base   import Docker__SGraph_AI__Service__Playwright__Base
from sg_compute_specs.playwright.core.docker.ECR__Docker__SGraph_AI__Service__Playwright    import ECR__Docker__SGraph_AI__Service__Playwright


class test_class_shape(TestCase):

    def test__is_subclass_of_base(self):
        assert issubclass(ECR__Docker__SGraph_AI__Service__Playwright,
                          Docker__SGraph_AI__Service__Playwright__Base)

    def test__method_surface(self):
        for method in ('ecr_setup', 'publish_docker_image', 'check_for_docker_config_json'):
            assert callable(getattr(ECR__Docker__SGraph_AI__Service__Playwright, method)), \
                   f'missing method: {method}'


class test_check_for_docker_config_json(TestCase):                                      # Carries forward Docker Desktop credsStore workaround

    def test__deletes_credsStore_desktop_config_when_present(self):
        tmp_home    = tempfile.mkdtemp()
        config_dir  = os.path.join(tmp_home, '.docker')
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, 'config.json')
        json_save_file(path=config_path, python_object={'credsStore': 'desktop'})

        previous_home     = os.environ.get('HOME')
        os.environ['HOME'] = tmp_home
        try:
            ecr = ECR__Docker__SGraph_AI__Service__Playwright().setup()
            result = ecr.check_for_docker_config_json()
            assert result is True                                                       # file_not_exists() confirms delete
            assert file_exists(config_path) is False
        finally:
            if previous_home is None: os.environ.pop('HOME', None)
            else                    : os.environ['HOME'] = previous_home

    def test__leaves_other_configs_untouched(self):
        tmp_home    = tempfile.mkdtemp()
        config_dir  = os.path.join(tmp_home, '.docker')
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, 'config.json')
        json_save_file(path=config_path, python_object={'credsStore': 'ecr-login'})     # Different credsStore → keep

        previous_home     = os.environ.get('HOME')
        os.environ['HOME'] = tmp_home
        try:
            ecr = ECR__Docker__SGraph_AI__Service__Playwright().setup()
            result = ecr.check_for_docker_config_json()
            assert result is False                                                      # file still exists
            assert file_exists(config_path) is True
        finally:
            if previous_home is None: os.environ.pop('HOME', None)
            else                    : os.environ['HOME'] = previous_home

    def test__noop_when_no_config_file(self):
        tmp_home          = tempfile.mkdtemp()                                          # No .docker/config.json
        previous_home     = os.environ.get('HOME')
        os.environ['HOME'] = tmp_home
        try:
            ecr    = ECR__Docker__SGraph_AI__Service__Playwright().setup()
            result = ecr.check_for_docker_config_json()
            assert result is True                                                       # Absent → treated as "safe"
        finally:
            if previous_home is None: os.environ.pop('HOME', None)
            else                    : os.environ['HOME'] = previous_home
