# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Docker__SP__CLI path resolution
# No Docker daemon required. Confirms the dockerfile + requirements + .dockerignore
# live where the wrapper expects them.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                                                              import TestCase

from sgraph_ai_service_playwright__cli.deploy.Docker__SP__CLI                                                              import Docker__SP__CLI, IMAGE_NAME, IMAGE_FOLDER_NAME


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
        requirements = self.docker.path_images() / IMAGE_FOLDER_NAME / 'requirements.txt'
        assert requirements.is_file()
        text = requirements.read_text()
        assert 'mangum'   in text                                                   # Required for the Mangum(app) handler
        assert 'fastapi'  in text
        assert 'osbot-aws' in text

    def test_dockerignore_exists(self):                                             # Keeps build context tight — repo root excludes everything except cli + scripts
        ignore = self.docker.path_images() / IMAGE_FOLDER_NAME / '.dockerignore'
        assert ignore.is_file()
        text = ignore.read_text()
        assert '!sgraph_ai_service_playwright__cli/**' in text
        assert '!scripts/**'                             in text

    def test_dockerfile_references_handler(self):                                   # CMD must point at the Mangum handler we wired in lambda_handler.py
        dockerfile = self.docker.path_dockerfile().read_text()
        assert 'sgraph_ai_service_playwright__cli.fast_api.lambda_handler.handler' in dockerfile
        assert 'public.ecr.aws/lambda/python:3.12'                                  in dockerfile
