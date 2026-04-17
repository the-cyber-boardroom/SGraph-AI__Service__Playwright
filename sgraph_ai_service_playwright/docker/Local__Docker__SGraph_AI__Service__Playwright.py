# ═══════════════════════════════════════════════════════════════════════════════
# Local__Docker__SGraph_AI__Service__Playwright — local dev container lifecycle
#
# Runs the built image locally on port 8888 (→ container port 8000). Label-based
# container reuse: containers are tagged with `source=local__docker__sgraph_ai_service_playwright`
# so the same container can be picked up across invocations.
# ═══════════════════════════════════════════════════════════════════════════════

import requests

from osbot_utils.utils.Misc                                                             import wait_for

from sgraph_ai_service_playwright.docker.Docker__SGraph_AI__Service__Playwright__Base   import (CONTAINER_PORT                               ,
                                                                                                 Docker__SGraph_AI__Service__Playwright__Base,
                                                                                                 LOCAL_PORT                                   )


LABEL_SOURCE = 'local__docker__sgraph_ai_service_playwright'


class Local__Docker__SGraph_AI__Service__Playwright(Docker__SGraph_AI__Service__Playwright__Base):

    label_source : str    = LABEL_SOURCE
    local_port   : int    = LOCAL_PORT
    container    : object = None

    def create_or_reuse_container(self):
        containers = self.containers_with_label()
        if len(containers) > 0:
            return next(iter(containers.values()))
        kwargs = {'labels'       : {'source': self.label_source}      ,
                  'port_bindings': {CONTAINER_PORT: self.local_port} }
        self.container = self.create_image_ecr.docker_image.create_container(**kwargs)
        return self.container.start()

    def containers_with_label(self):
        by_labels = self.api_docker().containers_all__by_labels()
        return by_labels.get('source', {}).get(self.label_source, {})

    def delete_container(self):
        if self.container:
            self.container.stop()
            return self.container.delete()
        return False

    def GET(self, path=''):
        return requests.get(self.local_url(path)).text

    def POST(self, path='', data=None):
        return requests.post(self.local_url(path), data=data,
                             headers={'Content-Type': 'application/json'}).text

    def local_url(self, path):
        if not path.startswith('/'):
            path = f'/{path}'
        return f'http://localhost:{self.local_port}{path}'

    def uvicorn_server_running(self):
        return 'Uvicorn running on ' in (self.container.logs() if self.container else '')

    def wait_for_uvicorn_server_running(self, max_count=40, delay=0.5):
        if self.container is None:
            return False
        for i in range(max_count):
            if self.container.status() != 'running':
                return False
            if self.uvicorn_server_running():
                return True
            wait_for(delay)
        return False
