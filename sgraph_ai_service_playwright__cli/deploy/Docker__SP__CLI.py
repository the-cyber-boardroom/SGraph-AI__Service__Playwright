# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Docker__SP__CLI
# Docker image build + ECR push helpers for the SP CLI Lambda.
#
# Build strategy: a temp directory is staged with only what the image needs
# (dockerfile + requirements + the two source trees referenced by COPY), then
# `docker build` is called directly. Two reasons we do NOT use
# osbot-aws's `Create_Image_ECR.build_image()` / `.create()`:
#
#   1. That helper uses `path_image()` = `images/<image_name>/` as the build
#      context. Our dockerfile's `COPY sgraph_ai_service_playwright__cli/` +
#      `COPY scripts/` point at folders that live at the repo root, not under
#      `images/<image_name>/`. The helper's context would skip them.
#   2. osbot-docker's `Docker_Image.build()` is @catch-wrapped and swallows
#      BuildError / APIError into `{'status': 'error', ...}`. We call the
#      Docker SDK directly so real build failures surface with a stack trace.
#
# This mirrors `Build__Docker__SGraph_AI__Service__Playwright.build_docker_image`
# — same pattern, simpler inputs (no boot shim, no version file, no Playwright
# package tree).
# ═══════════════════════════════════════════════════════════════════════════════

import os
import shutil
import tempfile
from pathlib                                                                        import Path

from osbot_aws.AWS_Config                                                           import AWS_Config
from osbot_aws.helpers.Create_Image_ECR                                             import Create_Image_ECR

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


IMAGE_NAME        = 'sp-playwright-cli'                                             # Used for the ECR repo name
IMAGE_FOLDER_NAME = 'sp_cli'                                                        # Subfolder under images/ that holds the dockerfile + requirements (Python-friendly short name; decoupled from the ECR repo name because we stage into a tempdir)
DOCKERFILE_NAME   = 'dockerfile'                                                    # Explicit — daemon defaults to 'Dockerfile' (case-sensitive on Linux)


def ignore_build_noise(directory, names):                                           # Keep the staged context lean — pycache + compiled files add MBs per run
    return [n for n in names
            if n in ('__pycache__', '.pytest_cache', '.mypy_cache', 'images')       # images/ inside sgraph_ai_service_playwright__cli/deploy/ holds the dockerfile itself; no reason to bake it into the image
            or n.endswith('.pyc')]


class Docker__SP__CLI(Type_Safe):
    image_name        : str    = IMAGE_NAME
    image_folder_name : str    = IMAGE_FOLDER_NAME
    create_image_ecr  : object = None                                               # Create_Image_ECR — lazy; instantiated in setup(). Skipped when only image_uri() is needed.

    def setup(self) -> 'Docker__SP__CLI':                                           # Only call when a build or push is about to happen — imports osbot-docker
        self.create_image_ecr = Create_Image_ECR(image_name  = self.image_name,
                                                 path_images = str(self.path_images()))
        return self

    def repo_root(self) -> Path:                                                    # Repo root — two parents above sgraph_ai_service_playwright__cli/deploy/
        return Path(__file__).resolve().parents[2]

    def path_images(self) -> Path:                                                  # Folder that HOLDS the per-image subfolders
        return Path(__file__).resolve().parent / 'images'

    def path_dockerfile(self) -> Path:
        return self.path_images() / self.image_folder_name / DOCKERFILE_NAME

    def path_requirements(self) -> Path:
        return self.path_images() / self.image_folder_name / 'requirements.txt'

    def repository(self) -> str:                                                    # ECR repo URI — computed directly from AWS_Config so callers that only need the URI (e.g. the provision-lambda CI step) do NOT need osbot-docker installed
        config = AWS_Config()
        return f'{config.aws_session_account_id()}.dkr.ecr.{config.aws_session_region_name()}.amazonaws.com/{self.image_name}'

    def image_uri(self) -> str:
        return f'{self.repository()}:latest'

    def build_and_push(self) -> dict:                                               # Build from a staged tempdir, push via ECR helper. Returns the ECR URI + docker image id.
        ecr = self.create_image_ecr
        ecr.create_repository()                                                     # Idempotent — creates the ECR repo if missing

        build_context = tempfile.mkdtemp(prefix='sp_cli_build_')
        try:
            self.stage_build_context(build_context)

            image_tag         = ecr.full_image_name()                               # <account>.dkr.ecr.<region>.amazonaws.com/<image_name>:latest
            client_docker     = ecr.api_docker.client_docker()                      # Direct SDK — bypass osbot-docker's @catch wrapper
            image, _logs      = client_docker.images.build(path       = build_context,
                                                            tag        = image_tag    ,
                                                            dockerfile = DOCKERFILE_NAME,
                                                            rm         = True         )

            push_result       = ecr.push_image()                                    # Handles ecr_login internally + pushes the image we just built
            return {'image_uri' : self.image_uri(),
                    'image_id'  : image.id         ,
                    'push'      : push_result      }
        finally:
            shutil.rmtree(build_context, ignore_errors=True)

    def stage_build_context(self, build_context: str) -> None:                      # Populate a tempdir with dockerfile + requirements + the four source trees referenced by COPY
        src_image_folder = self.path_images() / self.image_folder_name
        repo_root        = self.repo_root()

        shutil.copy    (str(src_image_folder / DOCKERFILE_NAME   ), os.path.join(build_context, DOCKERFILE_NAME   ))
        shutil.copy    (str(src_image_folder / 'requirements.txt'), os.path.join(build_context, 'requirements.txt'))
        shutil.copytree(str(repo_root / 'sgraph_ai_service_playwright__cli') ,
                        os.path.join(build_context, 'sgraph_ai_service_playwright__cli') ,
                        ignore=ignore_build_noise)
        shutil.copytree(str(repo_root / 'sgraph_ai_service_playwright')      ,            # Needed by scripts.provision_ec2's top-level import of IMAGE_NAME; Playwright's own imports are lazy so no runtime dep explosion
                        os.path.join(build_context, 'sgraph_ai_service_playwright')      ,
                        ignore=ignore_build_noise)
        shutil.copytree(str(repo_root / 'agent_mitmproxy')                   ,            # scripts.provision_ec2 imports IMAGE_NAME from agent_mitmproxy.docker.Docker__Agent_Mitmproxy__Base
                        os.path.join(build_context, 'agent_mitmproxy')                   ,
                        ignore=ignore_build_noise)
        shutil.copytree(str(repo_root / 'scripts') ,
                        os.path.join(build_context, 'scripts') ,
                        ignore=ignore_build_noise)
