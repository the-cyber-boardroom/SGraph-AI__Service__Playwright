# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — List__Schema__EC2__Block_Device__Mapping
# Typed list of EBS block device mapping schemas.
# Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Block_Device__Mapping import Schema__EC2__Block_Device__Mapping


class List__Schema__EC2__Block_Device__Mapping(Type_Safe__List):
    expected_type = Schema__EC2__Block_Device__Mapping
