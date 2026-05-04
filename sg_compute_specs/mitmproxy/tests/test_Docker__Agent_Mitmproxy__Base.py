# ═══════════════════════════════════════════════════════════════════════════════
# Tests — sg_compute_specs.mitmproxy.docker.Docker__Agent_Mitmproxy__Base
#
# Asserts path composition + image name constant. setup() pulls in
# osbot_docker (via Create_Image_ECR) which isn't installed in every env;
# tests that require it are skipped cleanly when absent.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from unittest                                                                        import TestCase, skipUnless

import sg_compute_specs.mitmproxy as _pkg
from sg_compute_specs.mitmproxy.docker.Docker__Agent_Mitmproxy__Base                 import (Docker__Agent_Mitmproxy__Base,
                                                                                             IMAGE_NAME                  )


def _osbot_docker_available() -> bool:
    try:
        import osbot_docker                                                          # noqa: F401
        return True
    except ModuleNotFoundError:
        return False


class test_Docker__Agent_Mitmproxy__Base(TestCase):

    def test__image_name_constant(self):
        assert IMAGE_NAME == 'agent_mitmproxy'

    def test__mitmproxy_path_is_a_dir(self):
        assert os.path.isdir(_pkg.path)

    def test__dockerfile_exists_on_disk(self):                                       # Path math hard-pins the dockerfile location; test against the real file without touching Create_Image_ECR
        expected = os.path.join(_pkg.path, 'docker', 'images', IMAGE_NAME, 'dockerfile')
        assert os.path.isfile(expected)

    @skipUnless(_osbot_docker_available(), 'osbot_docker not installed in this env; covered in CI')
    def test__path_composition(self):
        base = Docker__Agent_Mitmproxy__Base().setup()
        assert base.image_name == IMAGE_NAME
        assert base.path_images.endswith('mitmproxy/docker/images')
        assert base.path_docker().endswith('mitmproxy/docker/images/agent_mitmproxy')
        assert base.path_dockerfile() == os.path.join(base.path_docker(), 'dockerfile')
