# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Ec2__Service__In_Memory
# Real subclass of Ec2__Service that overrides the three public methods with
# fixture-driven returns. No mocks. Keeps the routes thin enough that wiring
# bugs show up immediately even without real AWS.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Dict

from sgraph_ai_service_playwright__cli.ec2.collections.List__Instance__Id           import List__Instance__Id
from sgraph_ai_service_playwright__cli.ec2.schemas.Schema__Ec2__Create__Request     import Schema__Ec2__Create__Request
from sgraph_ai_service_playwright__cli.ec2.schemas.Schema__Ec2__Create__Response    import Schema__Ec2__Create__Response
from sgraph_ai_service_playwright__cli.ec2.schemas.Schema__Ec2__Delete__Response    import Schema__Ec2__Delete__Response
from sgraph_ai_service_playwright__cli.ec2.schemas.Schema__Ec2__Instance__Info      import Schema__Ec2__Instance__Info
from sgraph_ai_service_playwright__cli.ec2.schemas.Schema__Ec2__Instance__List      import Schema__Ec2__Instance__List, List__Ec2__Instance__Info
from sgraph_ai_service_playwright__cli.ec2.service.Ec2__Service                     import Ec2__Service


class Ec2__Service__In_Memory(Ec2__Service):
    fixture_create   : Schema__Ec2__Create__Response                                # Returned verbatim on create()
    fixture_instances: Dict[str, Schema__Ec2__Instance__Info]                       # target (deploy-name or instance-id) → info
    last_create      : Schema__Ec2__Create__Request    = None                       # Captured for assertions
    last_deleted     : Schema__Ec2__Instance__Info     = None

    def create(self, request: Schema__Ec2__Create__Request) -> Schema__Ec2__Create__Response:
        self.last_create = request
        return self.fixture_create

    def get_instance_info(self, target: str) -> Schema__Ec2__Instance__Info:
        return self.fixture_instances.get(str(target))                              # Safe_Str hash ≠ plain-str hash; normalise

    def list_instances(self) -> Schema__Ec2__Instance__List:                        # Dedup by instance_id — fixture_instances maps both deploy-name AND instance-id to the same Schema
        seen      = set()
        instances = List__Ec2__Instance__Info()
        for info in self.fixture_instances.values():
            key = str(info.instance_id)
            if key and key not in seen:
                seen.add(key)
                instances.append(info)
        return Schema__Ec2__Instance__List(region='eu-west-2', instances=instances)

    def delete_instance(self, target: str) -> Schema__Ec2__Delete__Response:
        info = self.fixture_instances.get(str(target))
        if info is None:
            return Schema__Ec2__Delete__Response()                                  # All fields empty ⇒ route returns 404
        self.last_deleted = info
        terminated        = List__Instance__Id()
        terminated.append(info.instance_id)
        return Schema__Ec2__Delete__Response(target                  = info.instance_id ,
                                             deploy_name             = info.deploy_name  ,
                                             terminated_instance_ids = terminated        )

    def delete_all_instances(self) -> Schema__Ec2__Delete__Response:                 # Bulk delete — dedup the fixture (which maps both deploy-name AND instance-id to the same Schema)
        seen       = set()
        terminated = List__Instance__Id()
        for info in self.fixture_instances.values():
            key = str(info.instance_id)
            if key and key not in seen:
                seen.add(key)
                terminated.append(info.instance_id)
        return Schema__Ec2__Delete__Response(target                  = ''           ,
                                             deploy_name             = ''           ,
                                             terminated_instance_ids = terminated   )
