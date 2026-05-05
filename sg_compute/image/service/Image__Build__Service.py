# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Image__Build__Service
# Single source of truth for Docker image builds across the repo. Every
# builder hands a Schema__Image__Build__Request to build() and gets a
# Schema__Image__Build__Result back.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import shutil
import tempfile
import time

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute.image.collections.List__Str                                         import List__Str
from sg_compute.image.schemas.Schema__Image__Build__Request                         import Schema__Image__Build__Request
from sg_compute.image.schemas.Schema__Image__Build__Result                          import Schema__Image__Build__Result
from sg_compute.image.schemas.Schema__Image__Stage__Item                            import Schema__Image__Stage__Item


DEFAULT_IGNORE_NAMES = ('__pycache__', '.pytest_cache', '.mypy_cache')              # Common Python noise; also filters anything ending '.pyc'


class Image__Build__Service(Type_Safe):

    def make_ignore_callable(self, extra_ignore_names):                             # Returns a shutil.copytree-compatible ignore callable; defaults + extras
        ignore_set = set(DEFAULT_IGNORE_NAMES) | set(extra_ignore_names or [])
        def _ignore(_directory, names):
            return [n for n in names if n in ignore_set or n.endswith('.pyc')]
        return _ignore

    def stage_one_item(self, item: Schema__Image__Stage__Item, build_context: str): # Copy a single Schema__Image__Stage__Item into the staged build context
        target = os.path.join(build_context, str(item.target_name))
        if item.is_tree:
            shutil.copytree(str(item.source_path), target,
                            ignore=self.make_ignore_callable(item.extra_ignore_names))
        else:
            shutil.copy(str(item.source_path), target)

    def stage_build_context(self, request: Schema__Image__Build__Request, build_context: str):
        image_folder      = str(request.image_folder)
        dockerfile_name   = str(request.dockerfile_name)
        requirements_name = str(request.requirements_name)

        shutil.copy(os.path.join(image_folder, dockerfile_name)  , os.path.join(build_context, dockerfile_name)  )
        shutil.copy(os.path.join(image_folder, requirements_name), os.path.join(build_context, requirements_name))

        for item in request.stage_items:                                            # Per-image extras (boot shim, package trees, scripts, etc.)
            self.stage_one_item(item, build_context)

    def build(self, request: Schema__Image__Build__Request, docker_client) -> Schema__Image__Build__Result:
        build_context = tempfile.mkdtemp(prefix=str(request.build_context_prefix))
        try:
            started_at = time.monotonic()
            self.stage_build_context(request, build_context)
            image, _logs = docker_client.images.build(path       = build_context              ,
                                                      tag        = str(request.image_tag)      ,
                                                      dockerfile = str(request.dockerfile_name),
                                                      rm         = True                        )
            duration_ms = int((time.monotonic() - started_at) * 1000)
            return Schema__Image__Build__Result(image_id    = str(image.id)         ,
                                                image_tags  = List__Str(image.tags or []),
                                                duration_ms = duration_ms           )
        finally:
            shutil.rmtree(build_context, ignore_errors=True)
