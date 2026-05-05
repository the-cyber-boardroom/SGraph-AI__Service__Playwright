# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Routes__Host__Images
# First-class image management — no shell execute required.
#
# GET    /images                        → Schema__Image__List
# GET    /images/{name}                 → Schema__Image__Info  (404 on miss)
# POST   /images/load/from/local-path   → Schema__Image__Load__Response
# POST   /images/load/from/s3           → Schema__Image__Load__Response
# POST   /images/load/from/upload       → Schema__Image__Upload__Response
# DELETE /images/delete/{name}          → Schema__Image__Remove__Response
# ═══════════════════════════════════════════════════════════════════════════════

import os
import tempfile

from fastapi                                                                    import HTTPException, UploadFile, File
from osbot_fast_api.api.routes.Fast_API__Routes                                import Fast_API__Routes
from osbot_utils.type_safe.Type_Safe                                           import Type_Safe

from sg_compute.host_plane.images.schemas.Schema__Image__Upload__Response      import Schema__Image__Upload__Response
from sg_compute.host_plane.images.service.Image__Runtime__Docker               import Image__Runtime__Docker

TAG__ROUTES_HOST_IMAGES = 'images'

MAX_UPLOAD_BYTES = 20 * 1024 * 1024 * 1024     # 20 GiB hard cap


class Schema__Image__Load__Local__Request(Type_Safe):
    path : str = ''


class Schema__Image__Load__S3__Request(Type_Safe):
    bucket : str = ''
    key    : str = ''


class Routes__Host__Images(Fast_API__Routes):
    tag : str = TAG__ROUTES_HOST_IMAGES

    def _runtime(self) -> Image__Runtime__Docker:
        return Image__Runtime__Docker()

    def list_images(self) -> dict:                                          # GET /images
        return self._runtime().list_images().json()
    list_images.__route_path__ = ''

    def get_image(self, name: str) -> dict:                                 # GET /images/{name}
        result = self._runtime().inspect(name)
        if result is None:
            raise HTTPException(status_code=404, detail=f'image {name!r} not found')
        return result.json()
    get_image.__route_path__ = '/{name}'

    def load_from_local_path(self, body: Schema__Image__Load__Local__Request) -> dict:  # POST /images/load/from/local-path
        if not body.path:
            raise HTTPException(status_code=422, detail='path must not be empty')
        if not os.path.isfile(body.path):
            raise HTTPException(status_code=404, detail=f'file not found on host: {body.path!r}')
        return self._runtime().load(body.path).json()
    load_from_local_path.__route_path__ = '/load/from/local-path'

    def load_from_s3(self, body: Schema__Image__Load__S3__Request) -> dict:  # POST /images/load/from/s3
        if not body.bucket or not body.key:
            raise HTTPException(status_code=422, detail='bucket and key must not be empty')
        tmp_path = ''
        try:
            with tempfile.NamedTemporaryFile(suffix='.tar', delete=False) as tmp:
                tmp_path = tmp.name
            result = self._runtime().load_from_s3(body.bucket, body.key, tmp_path)
            return result.json()
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
    load_from_s3.__route_path__ = '/load/from/s3'

    def remove_image(self, name: str) -> dict:                              # DELETE /images/delete/{name}
        result = self._runtime().remove(name)
        if not result.removed:
            raise HTTPException(status_code=404, detail=result.error or f'image {name!r} not found')
        return result.json()
    remove_image.__route_path__ = '/delete/{name}'

    def setup_routes(self):
        self.add_route_get   (self.list_images        )
        self.add_route_get   (self.get_image          )
        self.add_route_post  (self.load_from_local_path)
        self.add_route_post  (self.load_from_s3       )
        self.add_route_delete(self.remove_image       )
        self.router.add_api_route('/load/from/upload', self._load_from_upload,
                                  methods=['POST'], tags=[self.tag])

    async def _load_from_upload(self, file: UploadFile = File(...)) -> dict:  # POST /images/load/from/upload
        size_bytes = 0
        tmp_path   = ''
        try:
            with tempfile.NamedTemporaryFile(suffix='.tar', delete=False) as tmp:
                tmp_path = tmp.name
                while True:
                    chunk = await file.read(1024 * 1024)                    # 1 MiB chunks
                    if not chunk:
                        break
                    size_bytes += len(chunk)
                    if size_bytes > MAX_UPLOAD_BYTES:
                        raise HTTPException(status_code=413, detail='upload exceeds 20 GiB limit')
                    tmp.write(chunk)
            result = self._runtime().load(tmp_path)
            return Schema__Image__Upload__Response(
                loaded     = result.loaded,
                output     = result.output,
                error      = result.error,
                size_bytes = size_bytes,
            ).json()
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
