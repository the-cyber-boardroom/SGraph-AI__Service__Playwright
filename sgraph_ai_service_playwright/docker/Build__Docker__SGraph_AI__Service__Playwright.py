# ═══════════════════════════════════════════════════════════════════════════════
# Build__Docker__SGraph_AI__Service__Playwright — build the Docker image for the Playwright service
#
# Delegates to Create_Image_ECR for the heavy lifting (docker build). Exposes
# container lifecycle helpers (create/start/list) plus inspection helpers
# (dockerfile content, image architecture) used by unit/integration tests.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.utils.Files                                                            import file_contents

from sgraph_ai_service_playwright.docker.Docker__SGraph_AI__Service__Playwright__Base   import (CONTAINER_PORT                               ,
                                                                                                 Docker__SGraph_AI__Service__Playwright__Base,
                                                                                                 LOCAL_PORT                                   )


class Build__Docker__SGraph_AI__Service__Playwright(Docker__SGraph_AI__Service__Playwright__Base):

    def build_docker_image(self):
        return self.create_image_ecr.build_image()

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
