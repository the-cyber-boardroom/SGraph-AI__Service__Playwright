# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Docker__SP__CLI path resolution + build-context staging
# No Docker daemon required. Exercises stage_build_context (which now
# delegates to Image__Build__Service) so the SP-CLI-specific composition of
# stage items (4 source trees + dockerfile + requirements + the
# extra-ignore for the deploy/images folder) is locked in. Generic ignore
# behaviour is covered separately in
# tests/unit/.../image/service/test_Image__Build__Service.py.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import shutil
import tempfile
from unittest                                                                                                              import TestCase

from sgraph_ai_service_playwright__cli.deploy.Docker__SP__CLI                                                              import (Docker__SP__CLI        ,
                                                                                                                                DOCKERFILE_NAME          ,
                                                                                                                                IMAGE_FOLDER_NAME        ,
                                                                                                                                IMAGE_NAME               )


class test_Docker__SP__CLI(TestCase):

    def setUp(self):
        self.docker = Docker__SP__CLI()

    def test__init__defaults(self):
        assert str(self.docker.image_name)        == IMAGE_NAME
        assert str(self.docker.image_folder_name) == IMAGE_FOLDER_NAME

    def test_repo_root_has_pyproject(self):
        assert (self.docker.repo_root() / 'pyproject.toml').is_file()

    def test_dockerfile_exists(self):
        assert self.docker.path_dockerfile().is_file()

    def test_requirements_exists(self):
        assert self.docker.path_requirements().is_file()
        text = self.docker.path_requirements().read_text()
        assert 'mangum'    in text                                                  # Required for the Mangum(app) handler
        assert 'fastapi'   in text
        assert 'osbot-aws' in text

    def test_dockerfile_references_handler(self):                                   # CMD must point at the Mangum handler we wired in lambda_handler.py
        dockerfile = self.docker.path_dockerfile().read_text()
        assert 'sgraph_ai_service_playwright__cli.fast_api.lambda_handler.handler' in dockerfile
        assert 'public.ecr.aws/lambda/python:3.12'                                  in dockerfile

    def test_build_request__has_all_four_source_trees_with_correct_target_names(self):  # Locks in the SP-CLI image composition
        request = self.docker.build_request()
        targets = {str(item.target_name): item for item in request.stage_items}
        assert set(targets) == {'sgraph_ai_service_playwright__cli', 'sgraph_ai_service_playwright', 'agent_mitmproxy', 'scripts'}
        for item in request.stage_items:                                            # All four are tree copies
            assert item.is_tree is True
        assert 'images' in list(targets['sgraph_ai_service_playwright__cli'].extra_ignore_names)  # Excludes the deploy/images folder

    def test_stage_build_context__copies_expected_trees(self):
        staging = tempfile.mkdtemp(prefix='sp_cli_build_test_')
        try:
            self.docker.stage_build_context(staging)

            assert os.path.isfile(os.path.join(staging, DOCKERFILE_NAME))
            assert os.path.isfile(os.path.join(staging, 'requirements.txt'))
            assert os.path.isdir (os.path.join(staging, 'sgraph_ai_service_playwright__cli'))
            assert os.path.isdir (os.path.join(staging, 'sgraph_ai_service_playwright'))           # Shared boot shim + version file
            assert os.path.isdir (os.path.join(staging, 'agent_mitmproxy'))                        # IMAGE_NAME constant for provision_ec2
            assert os.path.isdir (os.path.join(staging, 'scripts'))

            assert os.path.isfile(os.path.join(staging, 'sgraph_ai_service_playwright__cli',
                                               'fast_api', 'lambda_handler.py'))    # The handler the Lambda CMD references
            assert os.path.isfile(os.path.join(staging, 'scripts', 'provision_ec2.py'))
            assert os.path.isfile(os.path.join(staging, 'sgraph_ai_service_playwright', 'version'))             # Baked at /var/task; runtime_version reads it as a fallback when AGENTIC_APP_VERSION is unset

            assert not os.path.isdir(os.path.join(staging, 'sgraph_ai_service_playwright__cli', 'deploy', 'images'))   # images/ folder is filtered out via the per-item extra_ignore_names
        finally:
            shutil.rmtree(staging, ignore_errors=True)
