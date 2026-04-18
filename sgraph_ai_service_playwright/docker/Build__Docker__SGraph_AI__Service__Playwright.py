# ═══════════════════════════════════════════════════════════════════════════════
# Build__Docker__SGraph_AI__Service__Playwright — build the Docker image for the Playwright service
#
# Exposes container lifecycle helpers (create/start/list) plus inspection
# helpers (dockerfile content, image architecture) used by unit/integration
# tests.
#
# build_docker_image() stages the build context in a tempdir rather than
# pointing docker at `docker/images/<image>/` (which contains only the
# dockerfile + a thin requirements.txt). The dockerfile's `COPY . ./` would
# otherwise ship an empty package into /var/task, which made the container
# exit with `ModuleNotFoundError: No module named 'sgraph_ai_service_playwright'`
# on startup. Staging copies:
#   • the dockerfile + requirements.txt from the existing image folder
#   • lambda_entry.py + image_version from the repo root (v0.1.28 boot shim)
#   • the whole `sgraph_ai_service_playwright/` package source (minus __pycache__)
# so `python3 lambda_entry.py` resolves at container start.
#
# Two deliberate workarounds vs. calling osbot_docker's `Docker_Image.build()`:
#   1. The dockerfile is named `dockerfile` (lowercase). Docker daemon's
#      default is `Dockerfile` (capital D) on case-sensitive filesystems
#      (Linux / GH Actions runners), so we pass `dockerfile='dockerfile'`
#      explicitly to the SDK.
#   2. `Docker_Image.build()` is wrapped in `@catch` which swallows
#      `BuildError` / `APIError` into `{'status': 'error', ...}`. Our test
#      only asserted `result is not None`, so real build failures silently
#      passed the test and the downstream `docker inspect` was the one that
#      blew up with a confusing "No such object" error. We now call the
#      docker SDK directly so errors propagate and the `status` key reflects
#      the real outcome.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import shutil
import tempfile

from osbot_utils.utils.Dev                                                              import pprint
from osbot_utils.utils.Files                                                            import file_contents, path_combine

import sgraph_ai_service_playwright

from sgraph_ai_service_playwright.docker.Docker__SGraph_AI__Service__Playwright__Base   import (CONTAINER_PORT                               ,
                                                                                                 Docker__SGraph_AI__Service__Playwright__Base,
                                                                                                 LOCAL_PORT                                   )


DOCKERFILE_NAME      = 'dockerfile'                                                     # Explicit — daemon defaults to 'Dockerfile' (case-sensitive on Linux) when not passed
BOOT_SHIM_FILENAME   = 'lambda_entry.py'                                                # v0.1.28 — copied from repo root into /var/task/; boots before the code zip lands
IMAGE_VERSION_FILE   = 'image_version'                                                  # v0.1.28 — repo-root file; read by the boot shim to set AGENTIC_IMAGE_VERSION


def _ignore_build_noise(directory, names):                                              # Keep the build context lean — pycache + compiled files add MBs
    return [n for n in names if n in ('__pycache__', '.pytest_cache', '.mypy_cache') or n.endswith('.pyc')]


class Build__Docker__SGraph_AI__Service__Playwright(Docker__SGraph_AI__Service__Playwright__Base):

    def build_docker_image(self):
        src_context   = self.create_image_ecr.path_image()                              # .../docker/images/sgraph_ai_service_playwright/ (dockerfile + requirements.txt)
        pkg_src       = sgraph_ai_service_playwright.path                               # .../sgraph_ai_service_playwright/ (the actual Python package)
        repo_root     = os.path.dirname(pkg_src)                                        # v0.1.28 — lambda_entry.py + image_version live next to the package
        pkg_name      = 'sgraph_ai_service_playwright'
        image_tag     = self.create_image_ecr.docker_image.image_name_with_tag()        # Full ECR URI + :latest

        build_context = tempfile.mkdtemp(prefix='sgraph_playwright_build_')
        try:
            shutil.copy(path_combine(src_context, DOCKERFILE_NAME   ), path_combine(build_context, DOCKERFILE_NAME   ))
            shutil.copy(path_combine(src_context, 'requirements.txt'), path_combine(build_context, 'requirements.txt'))
            shutil.copy(path_combine(repo_root   , BOOT_SHIM_FILENAME), path_combine(build_context, BOOT_SHIM_FILENAME))
            shutil.copy(path_combine(repo_root   , IMAGE_VERSION_FILE), path_combine(build_context, IMAGE_VERSION_FILE))
            shutil.copytree(pkg_src, path_combine(build_context, pkg_name), ignore=_ignore_build_noise)

            client_docker   = self.api_docker().client_docker()                         # Direct docker SDK — bypass @catch so BuildError / APIError surface to the caller
            image, _logs    = client_docker.images.build(path       = build_context,
                                                          tag        = image_tag    ,
                                                          dockerfile = DOCKERFILE_NAME,
                                                          rm         = True         )
            result = {'status': 'ok', 'image_id': image.id, 'tags': image.tags}
            pprint(result)                                                              # CI log visibility — first line tells us the tag landed
            return result
        finally:
            shutil.rmtree(build_context, ignore_errors=True)

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
