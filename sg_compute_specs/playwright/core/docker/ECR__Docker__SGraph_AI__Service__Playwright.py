# ═══════════════════════════════════════════════════════════════════════════════
# ECR__Docker__SGraph_AI__Service__Playwright — ECR repository management and image push
#
# Carries forward the Docker Desktop `config.json` credsStore workaround from
# OSBot-Playwright: `{'credsStore': 'desktop'}` breaks the Python Docker API
# ECR login, so the file is deleted before push.
# ═══════════════════════════════════════════════════════════════════════════════

import os

from osbot_utils.utils.Files                                                            import (file_delete    ,
                                                                                                 file_exists    ,
                                                                                                 file_not_exists,
                                                                                                 path_combine   )
from osbot_utils.utils.Json                                                             import json_file_load

from sg_compute_specs.playwright.core.docker.Docker__SGraph_AI__Service__Playwright__Base   import Docker__SGraph_AI__Service__Playwright__Base


class ECR__Docker__SGraph_AI__Service__Playwright(Docker__SGraph_AI__Service__Playwright__Base):

    def ecr_setup(self):
        return self.create_image_ecr.create_repository()

    def publish_docker_image(self):
        self.check_for_docker_config_json()                                             # Workaround first
        return self.create_image_ecr.push_image()

    def check_for_docker_config_json(self):                                             # Docker Desktop credsStore workaround
        expected_config = {'credsStore': 'desktop'}                                     # This breaks the Python Docker API ECR login
        config_path     = path_combine(os.environ.get('HOME', ''), '.docker/config.json')
        if file_exists(config_path):
            config = json_file_load(config_path)
            if config == expected_config:
                print(f'## Warning: deleting {config_path} (credsStore: desktop breaks ECR login)')
                file_delete(config_path)
        return file_not_exists(config_path)
