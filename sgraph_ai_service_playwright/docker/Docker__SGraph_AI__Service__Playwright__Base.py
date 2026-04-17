# ═══════════════════════════════════════════════════════════════════════════════
# Docker__SGraph_AI__Service__Playwright__Base — shared init for all Docker classes
#
# Addresses the 'todo: refactor this init code to a base class' in
# ECR__Docker_Playwright.py from OSBot-Playwright. All four Docker classes
# (Build / ECR / Lambda / Local) extend this base; the `setup()` call wires
# up `Create_Image_ECR` (image build + registry helpers) and `Deploy_Lambda`
# (Lambda function management) against the package's docker context.
#
# Spec identifier uses 'SGraph-AI' (hyphen). Python identifiers cannot contain
# hyphens, so the class/module name normalises to 'SGraph_AI' per CLAUDE.md §16.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_aws.deploy.Deploy_Lambda                                                     import Deploy_Lambda
from osbot_aws.helpers.Create_Image_ECR                                                 import Create_Image_ECR
from osbot_utils.type_safe.Type_Safe                                                    import Type_Safe
from osbot_utils.utils.Files                                                            import path_combine

import sgraph_ai_service_playwright
from sgraph_ai_service_playwright.fast_api.lambda_handler                               import run


IMAGE_NAME     = 'sgraph_ai_service_playwright'
LOCAL_PORT     = 8888
CONTAINER_PORT = 8000


class Docker__SGraph_AI__Service__Playwright__Base(Type_Safe):

    image_name       : str    = IMAGE_NAME
    path_images      : str    = ''
    create_image_ecr : object = None                                                    # Create_Image_ECR — lazy init
    deploy_lambda    : object = None                                                    # Deploy_Lambda    — lazy init

    def setup(self) -> 'Docker__SGraph_AI__Service__Playwright__Base':
        self.path_images      = path_combine(sgraph_ai_service_playwright.path, 'docker/images')
        self.create_image_ecr = Create_Image_ECR(image_name  = self.image_name ,
                                                 path_images = self.path_images)
        self.deploy_lambda    = Deploy_Lambda(run)
        return self

    def api_docker(self):
        return self.create_image_ecr.api_docker

    def image_uri(self):
        return f"{self.repository()}:latest"

    def repository(self):
        return self.create_image_ecr.image_repository()

    def path_docker(self):
        return path_combine(sgraph_ai_service_playwright.path, f'docker/images/{self.image_name}')

    def path_dockerfile(self):
        return f'{self.path_docker()}/dockerfile'

    def lambda_function(self):
        return self.deploy_lambda.lambda_function()
