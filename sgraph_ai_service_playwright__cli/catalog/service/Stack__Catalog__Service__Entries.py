# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Stack__Catalog__Service__Entries
# Mixin: builds Schema__Stack__Type__Catalog__Entry for each stack type.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.catalog.enums.Enum__Stack__Type              import Enum__Stack__Type
from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Type__Catalog__Entry import Schema__Stack__Type__Catalog__Entry


T3_MEDIUM = 't3.medium'

def _paths(type_id: Enum__Stack__Type) -> dict:                                     # Derives the 5 endpoint paths from the type's value string
    v = type_id.value
    return dict(
        create_endpoint_path  = f'/{v}/stack'          ,
        list_endpoint_path    = f'/{v}/stacks'         ,
        info_endpoint_path    = f'/{v}/stack/{{name}}' ,
        delete_endpoint_path  = f'/{v}/stack/{{name}}' ,
        health_endpoint_path  = f'/{v}/stack/{{name}}/health',
    )


class Stack__Catalog__Service__Entries(Type_Safe):

    def entry__docker(self) -> Schema__Stack__Type__Catalog__Entry:
        return Schema__Stack__Type__Catalog__Entry(
            type_id=Enum__Stack__Type.DOCKER, display_name='Docker host',
            description='EC2 with Docker + Compose pre-installed.',
            available=True, default_instance_type=T3_MEDIUM, expected_boot_seconds=600,
            **_paths(Enum__Stack__Type.DOCKER))

    def entry__podman(self) -> Schema__Stack__Type__Catalog__Entry:
        return Schema__Stack__Type__Catalog__Entry(
            type_id=Enum__Stack__Type.PODMAN, display_name='Podman host',
            description='EC2 with Podman pre-installed (daemonless, rootless-capable).',
            available=True, default_instance_type=T3_MEDIUM, expected_boot_seconds=120,
            **_paths(Enum__Stack__Type.PODMAN))

    def entry__elastic(self) -> Schema__Stack__Type__Catalog__Entry:
        return Schema__Stack__Type__Catalog__Entry(
            type_id=Enum__Stack__Type.ELASTIC, display_name='Elastic + Kibana',
            description='Single-node Elasticsearch + Kibana on EC2.',
            available=True, default_instance_type=T3_MEDIUM, expected_boot_seconds=90,
            **_paths(Enum__Stack__Type.ELASTIC))

    def entry__opensearch(self) -> Schema__Stack__Type__Catalog__Entry:
        return Schema__Stack__Type__Catalog__Entry(
            type_id=Enum__Stack__Type.OPENSEARCH, display_name='OpenSearch + Dashboards',
            description='Coming soon.',
            available=False, default_instance_type=T3_MEDIUM, expected_boot_seconds=120,
            **_paths(Enum__Stack__Type.OPENSEARCH))

    def entry__vnc(self) -> Schema__Stack__Type__Catalog__Entry:
        return Schema__Stack__Type__Catalog__Entry(
            type_id=Enum__Stack__Type.VNC, display_name='VNC bastion (browser-in-browser)',
            description='Full desktop browser-in-browser with mitmweb traffic inspection.',
            available=True, default_instance_type='t3.large', expected_boot_seconds=120,
            **_paths(Enum__Stack__Type.VNC))
