# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Build__Docker__SGraph_AI__Service__Playwright
#
# Shape/method-surface tests. The actual `docker build` lives in the
# integration test tests/docker/test_Build__Docker__SGraph-AI__Service__Playwright.py.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                           import TestCase

from sgraph_ai_service_playwright.docker.Build__Docker__SGraph_AI__Service__Playwright  import Build__Docker__SGraph_AI__Service__Playwright
from sgraph_ai_service_playwright.docker.Docker__SGraph_AI__Service__Playwright__Base   import Docker__SGraph_AI__Service__Playwright__Base


class test_class_shape(TestCase):

    def test__is_subclass_of_base(self):
        assert issubclass(Build__Docker__SGraph_AI__Service__Playwright,
                          Docker__SGraph_AI__Service__Playwright__Base)

    def test__method_surface(self):
        for method in ('build_docker_image', 'create_container'   ,
                       'start_container'   , 'created_containers' ,
                       'dockerfile'        , 'image_architecture' ):
            assert callable(getattr(Build__Docker__SGraph_AI__Service__Playwright, method)), \
                   f'missing method: {method}'


class test_dockerfile(TestCase):

    def test__returns_the_packaged_dockerfile_content(self):                            # Reads the file on disk; no docker required
        build = Build__Docker__SGraph_AI__Service__Playwright().setup()
        text  = build.dockerfile()
        assert 'mcr.microsoft.com/playwright/python' in text                            # Base image
        assert 'aws-lambda-adapter'                  in text                            # LWA layer copy
        assert 'lambda_handler'                      in text                            # CMD entrypoint
