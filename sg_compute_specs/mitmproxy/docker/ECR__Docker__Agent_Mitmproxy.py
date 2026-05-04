# ═══════════════════════════════════════════════════════════════════════════════
# ECR__Docker__Agent_Mitmproxy — ECR repo management + image push
#
# Same Docker-Desktop credsStore workaround as the Playwright image: delete
# ~/.docker/config.json when it carries `{'credsStore': 'desktop'}` because
# that breaks the Python Docker SDK's ECR login.
# ═══════════════════════════════════════════════════════════════════════════════

import os

from osbot_utils.utils.Files                                                            import (file_delete    ,
                                                                                                 file_exists    ,
                                                                                                 file_not_exists,
                                                                                                 path_combine   )
from osbot_utils.utils.Json                                                             import json_file_load

from sg_compute_specs.mitmproxy.docker.Docker__Agent_Mitmproxy__Base                   import Docker__Agent_Mitmproxy__Base


class ECR__Docker__Agent_Mitmproxy(Docker__Agent_Mitmproxy__Base):

    def ecr_setup(self):
        return self.create_image_ecr.create_repository()

    def publish_docker_image(self):
        self.check_for_docker_config_json()
        return self.create_image_ecr.push_image()

    def check_for_docker_config_json(self):                                             # Docker Desktop credsStore workaround
        expected_config = {'credsStore': 'desktop'}
        config_path     = path_combine(os.environ.get('HOME', ''), '.docker/config.json')
        if file_exists(config_path):
            config = json_file_load(config_path)
            if config == expected_config:
                print(f'## Warning: deleting {config_path} (credsStore: desktop breaks ECR login)')
                file_delete(config_path)
        return file_not_exists(config_path)
