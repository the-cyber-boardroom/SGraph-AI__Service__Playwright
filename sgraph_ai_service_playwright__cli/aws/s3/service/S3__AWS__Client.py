# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — S3__AWS__Client (Foundation interface stub)
# Real bodies owned by Slice A (v0.2.29__sg-aws-s3).
# Slice H builds against this stub for S3__Source__Adapter; the final
# rebase before Slice H's PR swaps in Slice A's implementation.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class S3__AWS__Client(Type_Safe):

    def list_buckets(self) -> list:
        raise NotImplementedError("Slice A owns this body — see library/dev_packs/v0.2.29__sg-aws-s3/")

    def list_objects(self, bucket: str, prefix: str = '', max_keys: int = 1000) -> list:
        raise NotImplementedError("Slice A owns this body — see library/dev_packs/v0.2.29__sg-aws-s3/")

    def get_object(self, bucket: str, key: str) -> bytes:
        raise NotImplementedError("Slice A owns this body — see library/dev_packs/v0.2.29__sg-aws-s3/")

    def head_object(self, bucket: str, key: str) -> dict:
        raise NotImplementedError("Slice A owns this body — see library/dev_packs/v0.2.29__sg-aws-s3/")

    def put_object(self, bucket: str, key: str, body: bytes, content_type: str = '') -> bool:
        raise NotImplementedError("Slice A owns this body — see library/dev_packs/v0.2.29__sg-aws-s3/")

    def delete_object(self, bucket: str, key: str) -> bool:
        raise NotImplementedError("Slice A owns this body — see library/dev_packs/v0.2.29__sg-aws-s3/")

    def generate_presigned_url(self, bucket: str, key: str, ttl_seconds: int = 3600) -> str:
        raise NotImplementedError("Slice A owns this body — see library/dev_packs/v0.2.29__sg-aws-s3/")

    def get_bucket_region(self, bucket: str) -> str:
        raise NotImplementedError("Slice A owns this body — see library/dev_packs/v0.2.29__sg-aws-s3/")
