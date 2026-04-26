# ═══════════════════════════════════════════════════════════════════════════════
# Build__Docker__SGraph_AI__Service__Playwright — build the Docker image for the Playwright service
#
# Exposes container lifecycle helpers (create/start/list) plus inspection
# helpers (dockerfile content, image architecture) used by unit/integration
# tests.
#
# build_docker_image() delegates to the shared Image__Build__Service which
# stages the build context in a tempdir, calls the docker SDK directly
# (bypassing osbot-docker's @catch wrapper so BuildError / APIError
# surface), and returns a Type_Safe Schema__Image__Build__Result.
#
# This builder's responsibility is to compose the Schema__Image__Build__Request
# specific to the Playwright image:
#   • the dockerfile + requirements.txt from the existing image folder
#   • lambda_entry.py + image_version from the repo root (v0.1.28 boot shim)
#   • the whole `sgraph_ai_service_playwright/` package source (minus pycache)
# so `python3 lambda_entry.py` resolves at container start.
#
# The dockerfile is named `dockerfile` (lowercase) — Docker daemon defaults
# to `Dockerfile` (capital D) on case-sensitive filesystems (Linux / GH
# Actions runners). The shared service defaults to lowercase too.
# ═══════════════════════════════════════════════════════════════════════════════

import os

from osbot_utils.utils.Dev                                                              import pprint
from osbot_utils.utils.Files                                                            import file_contents

import sgraph_ai_service_playwright

from sgraph_ai_service_playwright.docker.Docker__SGraph_AI__Service__Playwright__Base   import (CONTAINER_PORT                               ,
                                                                                                 Docker__SGraph_AI__Service__Playwright__Base,
                                                                                                 LOCAL_PORT                                   )
from sgraph_ai_service_playwright__cli.image.schemas.Schema__Image__Build__Request       import Schema__Image__Build__Request
from sgraph_ai_service_playwright__cli.image.schemas.Schema__Image__Build__Result        import Schema__Image__Build__Result
from sgraph_ai_service_playwright__cli.image.schemas.Schema__Image__Stage__Item          import Schema__Image__Stage__Item
from sgraph_ai_service_playwright__cli.image.service.Image__Build__Service               import Image__Build__Service


BOOT_SHIM_FILENAME   = 'lambda_entry.py'                                                # v0.1.28 — copied from repo root into /var/task/; boots before the code zip lands
IMAGE_VERSION_FILE   = 'image_version'                                                  # v0.1.28 — repo-root file; read by the boot shim to set AGENTIC_IMAGE_VERSION


class Build__Docker__SGraph_AI__Service__Playwright(Docker__SGraph_AI__Service__Playwright__Base):

    def build_request(self) -> Schema__Image__Build__Request:                           # Compose the Playwright-specific build request — testable in isolation
        src_context = self.create_image_ecr.path_image()                                # .../docker/images/sgraph_ai_service_playwright/
        pkg_src     = sgraph_ai_service_playwright.path                                 # .../sgraph_ai_service_playwright/ (the actual Python package)
        repo_root   = os.path.dirname(pkg_src)                                          # v0.1.28 — lambda_entry.py + image_version live next to the package
        pkg_name    = 'sgraph_ai_service_playwright'

        return Schema__Image__Build__Request(
            image_folder         = src_context                                          ,
            image_tag            = self.create_image_ecr.docker_image.image_name_with_tag(),
            build_context_prefix = 'sgraph_playwright_build_'                           ,
            stage_items          = [Schema__Image__Stage__Item(source_path=os.path.join(repo_root, BOOT_SHIM_FILENAME), target_name=BOOT_SHIM_FILENAME),
                                    Schema__Image__Stage__Item(source_path=os.path.join(repo_root, IMAGE_VERSION_FILE), target_name=IMAGE_VERSION_FILE),
                                    Schema__Image__Stage__Item(source_path=pkg_src, target_name=pkg_name, is_tree=True)])

    def build_docker_image(self) -> Schema__Image__Build__Result:                       # Returns Schema__Image__Build__Result; CI test asserts on its fields
        result = Image__Build__Service().build(self.build_request(), self.api_docker().client_docker())
        pprint(result.json())                                                           # CI log visibility — first line tells us the tag landed
        return result

    def create_container(self):
        port_bindings = {CONTAINER_PORT: LOCAL_PORT}
        return self.api_docker().container_create(image_name    = self.repository() ,
                                                   command       = ''                ,
                                                   port_bindings = port_bindings     )

    def start_container(self):
        container = self.create_container()
        container.start()
        return container

    def created_containers(self):
        created = {}
        for container in self.api_docker().containers_all__with_image(self.repository()):
            created[container.container_id] = container
        return created

    def dockerfile(self):
        return file_contents(self.path_dockerfile())

    def image_architecture(self):
        return self.create_image_ecr.docker_image.architecture()
