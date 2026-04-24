# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Docker__SP__CLI
# Docker image build + ECR push helpers for the SP CLI Lambda. Builds from the
# repository root (not the image folder) because the image COPYs the
# sgraph_ai_service_playwright__cli/ and scripts/ trees, which live above
# the dockerfile. .dockerignore in the image folder scopes the context down.
# ═══════════════════════════════════════════════════════════════════════════════

from pathlib                                                                        import Path

from osbot_aws.helpers.Create_Image_ECR                                             import Create_Image_ECR

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


IMAGE_NAME        = 'sp-playwright-cli'                                             # Used for the ECR repo name
IMAGE_FOLDER_NAME = 'sp_cli'                                                        # Subfolder under images/ that holds the dockerfile + requirements


class Docker__SP__CLI(Type_Safe):
    image_name        : str    = IMAGE_NAME
    image_folder_name : str    = IMAGE_FOLDER_NAME                                  # Folder name stays short + Python-friendly even though the ECR repo uses hyphens
    create_image_ecr  : object = None                                               # Create_Image_ECR — lazy

    def setup(self) -> 'Docker__SP__CLI':
        self.create_image_ecr = Create_Image_ECR(image_name  = self.image_name,
                                                 path_images = str(self.path_images()))
        return self

    def repo_root(self) -> Path:                                                    # Repo root — two parents above sgraph_ai_service_playwright__cli/deploy/
        return Path(__file__).resolve().parents[2]

    def path_images(self) -> Path:                                                  # Folder that HOLDS the per-image subfolders (matches osbot-aws Create_Image_ECR layout)
        return Path(__file__).resolve().parent / 'images'

    def path_dockerfile(self) -> Path:
        return self.path_images() / self.image_folder_name / 'dockerfile'

    def repository(self) -> str:
        return self.create_image_ecr.image_repository()

    def image_uri(self) -> str:
        return f'{self.repository()}:latest'

    def build_and_push(self) -> dict:                                               # Build locally, then push to ECR. Returns ECR URIs for the Lambda to reference.
        ecr     = self.create_image_ecr
        ecr.create_image_repository()                                               # Idempotent — creates repo if missing
        build   = ecr.build_and_push_image(path_build_context=str(self.repo_root()))
        return {'image_uri' : self.image_uri(),
                'build'     : build            }
