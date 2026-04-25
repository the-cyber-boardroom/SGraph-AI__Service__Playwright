# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Docker__SP__CLI path resolution + build-context staging
# No Docker daemon required. Exercises the tempdir-staging helper directly so
# image-context bugs surface in unit tests instead of only in CI.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import shutil
import tempfile
from unittest                                                                                                              import TestCase

from sgraph_ai_service_playwright__cli.deploy.Docker__SP__CLI                                                              import (Docker__SP__CLI        ,
                                                                                                                                DOCKERFILE_NAME          ,
                                                                                                                                IMAGE_FOLDER_NAME        ,
                                                                                                                                IMAGE_NAME               ,
                                                                                                                                ignore_build_noise       )


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

    def test_ignore_build_noise__filters_caches_and_pycs(self):
        noisy  = ['__pycache__', 'real_module.py', 'fixture.pyc', '.pytest_cache', '.mypy_cache', 'something.txt']
        result = ignore_build_noise('/any/path', noisy)
        assert '__pycache__'    in result
        assert '.pytest_cache'  in result
        assert '.mypy_cache'    in result
        assert 'fixture.pyc'    in result
        assert 'real_module.py' not in result
        assert 'something.txt'  not in result

    def test_ignore_build_noise__filters_deploy_images_folder(self):                # images/ under sgraph_ai_service_playwright__cli/deploy/ holds the dockerfile itself; excluded from the staged context
        assert 'images' in ignore_build_noise('/any/path', ['images', 'service', 'schemas'])

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

            assert not os.path.isdir(os.path.join(staging, 'sgraph_ai_service_playwright__cli', 'deploy', 'images'))   # images/ folder is filtered out by ignore_build_noise
        finally:
            shutil.rmtree(staging, ignore_errors=True)
