# ═══════════════════════════════════════════════════════════════════════════════
# Waker — Endpoint__Resolver
# Abstract base class for slug → live-endpoint resolution.
# Phase 2c implements EC2 (Endpoint__Resolver__EC2).
# Phase 3 will add Fargate (Endpoint__Resolver__Fargate) — out of plan scope.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.waker.schemas.Schema__Endpoint__Resolution import Schema__Endpoint__Resolution


class Endpoint__Resolver(Type_Safe):

    def resolve(self, slug: str) -> Schema__Endpoint__Resolution:
        raise NotImplementedError

    def start(self, instance_id: str) -> bool:
        raise NotImplementedError
