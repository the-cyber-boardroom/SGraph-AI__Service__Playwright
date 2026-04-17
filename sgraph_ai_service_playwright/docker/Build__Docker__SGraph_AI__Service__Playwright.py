# ═══════════════════════════════════════════════════════════════════════════════
# Build__Docker__SGraph_AI__Service__Playwright — build the Docker image for the Playwright service
#
# Delegates to Create_Image_ECR for the heavy lifting (docker build). Exposes
# container lifecycle helpers (create/start/list) plus inspection helpers
# (dockerfile content, image architecture) used by unit/integration tests.
#
# build_docker_image() stages the build context in a tempdir rather than using
# the Create_Image_ECR default (which points at `docker/images/<image>/` and
# contains only the dockerfile + a thin requirements.txt). The dockerfile's
# `COPY . ./` would otherwise ship an empty package into /var/task, which made
# the container exit with `ModuleNotFoundError: No module named
# 'sgraph_ai_service_playwright'` on startup. Staging copies:
#   • the dockerfile + requirements.txt from the existing image folder
#   • the whole `sgraph_ai_service_playwright/` package source (minus __pycache__)
# so `python3 -m sgraph_ai_service_playwright.fast_api.lambda_handler` resolves.
# ═══════════════════════════════════════════════════════════════════════════════

import shutil
import tempfile

from osbot_utils.utils.Files                                                            import file_contents, path_combine

import sgraph_ai_service_playwright

from sgraph_ai_service_playwright.docker.Docker__SGraph_AI__Service__Playwright__Base   import (CONTAINER_PORT                               ,
                                                                                                 Docker__SGraph_AI__Service__Playwright__Base,
                                                                                                 LOCAL_PORT                                   )


def _ignore_build_noise(directory, names):                                              # Keep the build context lean — pycache + compiled files add MBs
    return [n for n in names if n in ('__pycache__', '.pytest_cache', '.mypy_cache') or n.endswith('.pyc')]


class Build__Docker__SGraph_AI__Service__Playwright(Docker__SGraph_AI__Service__Playwright__Base):

    def build_docker_image(self):
        src_context   = self.create_image_ecr.path_image()                              # .../docker/images/sgraph_ai_service_playwright/ (dockerfile + requirements.txt)
        pkg_src       = sgraph_ai_service_playwright.path                               # .../sgraph_ai_service_playwright/ (the actual Python package)
        pkg_name      = 'sgraph_ai_service_playwright'

        build_context = tempfile.mkdtemp(prefix='sgraph_playwright_build_')
        try:
            shutil.copy(path_combine(src_context, 'dockerfile'      ), path_combine(build_context, 'dockerfile'      ))
            shutil.copy(path_combine(src_context, 'requirements.txt'), path_combine(build_context, 'requirements.txt'))
            shutil.copytree(pkg_src, path_combine(build_context, pkg_name), ignore=_ignore_build_noise)
            return self.create_image_ecr.docker_image.build(build_context)
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
