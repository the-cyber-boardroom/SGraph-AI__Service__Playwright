# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Docker__SGraph_AI__Service__Playwright__Base
#
# Shape/setup tests for the base class that all four Docker classes extend.
# Verifies:
#   • default attributes (image_name, path_images empty until setup)
#   • module-level port constants
#   • setup() populates create_image_ecr + deploy_lambda + path_images
#   • helper methods (path_docker, path_dockerfile) point at the right paths
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                           import TestCase

from osbot_aws.deploy.Deploy_Lambda                                                     import Deploy_Lambda
from osbot_aws.helpers.Create_Image_ECR                                                 import Create_Image_ECR

from sg_compute_specs.playwright.core.docker.Docker__SGraph_AI__Service__Playwright__Base   import (CONTAINER_PORT                               ,
                                                                                                 Docker__SGraph_AI__Service__Playwright__Base,
                                                                                                 IMAGE_NAME                                   ,
                                                                                                 LOCAL_PORT                                   )


class test_module_constants(TestCase):

    def test__image_name_and_ports(self):
        assert IMAGE_NAME     == 'sgraph_ai_service_playwright'                         # Canonical image name
        assert LOCAL_PORT     == 8888
        assert CONTAINER_PORT == 8000


class test_class_shape(TestCase):

    def test__defaults_before_setup(self):
        base = Docker__SGraph_AI__Service__Playwright__Base()
        assert base.image_name       == IMAGE_NAME
        assert base.path_images      == ''                                              # Set by setup()
        assert base.create_image_ecr is None
        assert base.deploy_lambda    is None


class test_setup(TestCase):

    def test__setup_is_chainable_and_wires_dependencies(self):
        base = Docker__SGraph_AI__Service__Playwright__Base()
        out  = base.setup()
        assert out is base                                                              # Chainable
        assert isinstance(base.create_image_ecr, Create_Image_ECR)
        assert isinstance(base.deploy_lambda   , Deploy_Lambda    )
        assert base.path_images.endswith('/docker/images')

    def test__setup_populates_path_images_under_package(self):
        import sg_compute_specs.playwright.core as _playwright_pkg
        base = Docker__SGraph_AI__Service__Playwright__Base().setup()
        assert base.path_images.startswith(_playwright_pkg.path)


class test_path_helpers(TestCase):

    def test__path_docker_and_path_dockerfile(self):
        base  = Docker__SGraph_AI__Service__Playwright__Base().setup()
        p     = base.path_docker()
        assert p.endswith(f'/docker/images/{IMAGE_NAME}')                               # Flat-per-image layout
        assert base.path_dockerfile() == f'{p}/dockerfile'


class test_ecr_delegation(TestCase):

    def test__api_docker_repository_image_uri_delegate(self):                           # Pure delegation to create_image_ecr
        base = Docker__SGraph_AI__Service__Playwright__Base().setup()
        assert base.api_docker() is base.create_image_ecr.api_docker
        assert base.image_uri().endswith(':latest')                                     # Always tag=latest


class test_lambda_delegation(TestCase):

    def test__lambda_function_delegates_to_deploy_lambda(self):
        base = Docker__SGraph_AI__Service__Playwright__Base().setup()
        assert base.lambda_function() is base.deploy_lambda.lambda_function()
