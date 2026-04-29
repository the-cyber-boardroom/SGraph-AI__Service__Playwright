# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Docker__SP__CLI
# Docker image build + ECR push helpers for the SP CLI Lambda.
#
# This class composes a Schema__Image__Build__Request specific to the SP CLI
# image (four source trees referenced by COPY) and hands it to the shared
# Image__Build__Service. The push step (ecr.push_image) stays here because
# it depends on the section's ECR helper.
#
# We do NOT use osbot-aws's `Create_Image_ECR.build_image()` / `.create()`
# because that helper uses `path_image()` = `images/<image_name>/` as the
# build context, and our dockerfile's COPY targets live at the repo root.
# Image__Build__Service stages a tempdir + calls the docker SDK directly
# (bypassing osbot-docker's @catch wrapper so real build failures propagate).
# ═══════════════════════════════════════════════════════════════════════════════

from pathlib                                                                        import Path

from osbot_aws.AWS_Config                                                           import AWS_Config
from osbot_aws.helpers.Create_Image_ECR                                             import Create_Image_ECR

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.image.schemas.Schema__Image__Build__Request   import Schema__Image__Build__Request
from sgraph_ai_service_playwright__cli.image.schemas.Schema__Image__Stage__Item      import Schema__Image__Stage__Item
from sgraph_ai_service_playwright__cli.image.service.Image__Build__Service           import Image__Build__Service


IMAGE_NAME        = 'sp-playwright-cli'                                             # Used for the ECR repo name
IMAGE_FOLDER_NAME = 'sp_cli'                                                        # Subfolder under images/ that holds the dockerfile + requirements (Python-friendly short name; decoupled from the ECR repo name because we stage into a tempdir)
DOCKERFILE_NAME   = 'dockerfile'                                                    # Kept for tests that check the dockerfile path; the shared service defaults to the same value


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

    def build_request(self) -> Schema__Image__Build__Request:                       # Compose the SP-CLI-specific build request — testable in isolation, no Docker required
        src_image_folder = self.path_images() / self.image_folder_name
        repo_root        = self.repo_root()
        return Schema__Image__Build__Request(
            image_folder         = str(src_image_folder)                ,
            image_tag            = self.create_image_ecr.full_image_name() if self.create_image_ecr else self.image_uri(),
            build_context_prefix = 'sp_cli_build_'                      ,
            stage_items          = [Schema__Image__Stage__Item(source_path=str(repo_root / 'sgraph_ai_service_playwright__cli'),
                                                              target_name='sgraph_ai_service_playwright__cli', is_tree=True,
                                                              extra_ignore_names=['images']),                                       # images/ holds the dockerfile itself; no reason to bake it
                                    Schema__Image__Stage__Item(source_path=str(repo_root / 'sgraph_ai_service_playwright')     ,    # Needed by scripts.provision_ec2's top-level import of IMAGE_NAME; Playwright's own imports are lazy
                                                              target_name='sgraph_ai_service_playwright'     , is_tree=True),
                                    Schema__Image__Stage__Item(source_path=str(repo_root / 'agent_mitmproxy')                  ,    # scripts.provision_ec2 imports IMAGE_NAME from agent_mitmproxy.docker.Docker__Agent_Mitmproxy__Base
                                                              target_name='agent_mitmproxy'                  , is_tree=True),
                                    Schema__Image__Stage__Item(source_path=str(repo_root / 'scripts')                          ,
                                                              target_name='scripts'                          , is_tree=True),
                                    Schema__Image__Stage__Item(source_path=str(repo_root / 'sgraph_ai_service_playwright__api_site'),  # Static UI assets served at /ui by Fast_API__SP__CLI._mount_ui()
                                                              target_name='sgraph_ai_service_playwright__api_site', is_tree=True)])

    def build_and_push(self) -> dict:                                               # Build via shared service, then push via ECR helper. Returns ECR URI + docker image id + push string.
        ecr = self.create_image_ecr
        ecr.create_repository()                                                     # Idempotent — creates the ECR repo if missing

        result      = Image__Build__Service().build(self.build_request(), ecr.api_docker.client_docker())
        push_result = ecr.push_image()                                              # Handles ecr_login internally + pushes the image we just built
        return {'image_uri' : self.image_uri()         ,
                'image_id'  : str(result.image_id)     ,
                'push'      : push_result              }

    def stage_build_context(self, build_context: str) -> None:                      # Backwards-compat seam used by tests/unit/.../test_Docker__SP__CLI.py — delegates to the shared service
        Image__Build__Service().stage_build_context(self.build_request(), build_context)
