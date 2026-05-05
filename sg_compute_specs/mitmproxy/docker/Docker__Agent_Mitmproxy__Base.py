# ═══════════════════════════════════════════════════════════════════════════════
# Docker__Agent_Mitmproxy__Base — shared init for all Docker helpers
#
# Wires Create_Image_ECR against the mitmproxy package's docker context.
# No Deploy_Lambda here — mitmproxy runs on EC2, not Lambda (tunnels + CONNECT
# semantics don't survive the Lambda Function URL adapter).
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                             import Optional

from osbot_aws.helpers.Create_Image_ECR                                                 import Create_Image_ECR
from osbot_utils.type_safe.Type_Safe                                                    import Type_Safe
from osbot_utils.utils.Files                                                            import path_combine

import sg_compute_specs.mitmproxy as _pkg


IMAGE_NAME = 'agent_mitmproxy'


class Docker__Agent_Mitmproxy__Base(Type_Safe):

    image_name       : str    = IMAGE_NAME
    path_images      : str    = ''
    create_image_ecr : Optional[Create_Image_ECR] = None

    def setup(self) -> 'Docker__Agent_Mitmproxy__Base':
        self.path_images      = path_combine(_pkg.path, 'docker/images')
        self.create_image_ecr = Create_Image_ECR(image_name  = self.image_name ,
                                                 path_images = self.path_images)
        return self

    def api_docker(self):
        return self.create_image_ecr.api_docker

    def image_uri(self):
        return f'{self.repository()}:latest'

    def repository(self):
        return self.create_image_ecr.image_repository()

    def path_docker(self):
        return path_combine(_pkg.path, f'docker/images/{self.image_name}')

    def path_dockerfile(self):
        return f'{self.path_docker()}/dockerfile'
