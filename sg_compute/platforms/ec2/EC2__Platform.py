# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — EC2__Platform
# Implements the Platform interface using the EC2 helpers.
# Wraps the existing helpers; spec services that want low-level control still
# call the helpers directly.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.core.node.schemas.Schema__Node__Create__Request__Base        import Schema__Node__Create__Request__Base
from sg_compute.core.node.schemas.Schema__Node__Delete__Response             import Schema__Node__Delete__Response
from sg_compute.core.node.schemas.Schema__Node__Info                         import Schema__Node__Info
from sg_compute.core.node.schemas.Schema__Node__List                         import Schema__Node__List
from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry              import Schema__Spec__Manifest__Entry
from sg_compute.platforms.Platform                                            import Platform
from sg_compute.primitives.enums.Enum__Node__State                           import Enum__Node__State


class EC2__Platform(Platform):
    name : str = 'ec2'

    def setup(self) -> 'EC2__Platform':
        return self

    def _raw_to_node_info(self, raw: dict, region: str, spec_id: str = '') -> Schema__Node__Info:
        from sg_compute.platforms.ec2.helpers.EC2__Stack__Mapper import tag_value, state_str, uptime_seconds
        state_map = {
            'running'      : Enum__Node__State.READY      ,
            'pending'      : Enum__Node__State.BOOTING    ,
            'shutting-down': Enum__Node__State.TERMINATING,
            'terminated'   : Enum__Node__State.TERMINATED ,
            'stopping'     : Enum__Node__State.TERMINATING,
            'stopped'      : Enum__Node__State.TERMINATED ,
        }
        raw_state = state_str(raw)
        return Schema__Node__Info(
            node_id       = tag_value(raw, 'StackName')                      ,
            spec_id       = spec_id or tag_value(raw, 'StackType')           ,
            region        = region                                            ,
            state         = state_map.get(raw_state, Enum__Node__State.FAILED),
            public_ip     = raw.get('PublicIpAddress',  '')                  ,
            private_ip    = raw.get('PrivateIpAddress', '')                  ,
            instance_id   = raw.get('InstanceId',       '')                  ,
            instance_type = raw.get('InstanceType',     '')                  ,
            ami_id        = raw.get('ImageId',          '')                  ,
            uptime_seconds= uptime_seconds(raw)                              ,
        )

    def list_nodes(self, region: str = '') -> Schema__Node__List:
        from sg_compute.platforms.ec2.helpers.EC2__Instance__Helper import EC2__Instance__Helper
        from sg_compute.platforms.ec2.helpers.EC2__Tags__Builder    import TAG_PURPOSE_VALUE
        helper = EC2__Instance__Helper()
        raw_nodes = helper.list_by_stack_type(region, TAG_PURPOSE_VALUE)
        nodes = [self._raw_to_node_info(raw, region) for raw in raw_nodes.values()]
        return Schema__Node__List(nodes=nodes)

    def get_node(self, node_id: str, region: str = '') -> 'Schema__Node__Info | None':
        from sg_compute.platforms.ec2.helpers.EC2__Instance__Helper import EC2__Instance__Helper
        helper = EC2__Instance__Helper()
        raw = helper.find_by_stack_name(region, node_id)
        if raw is None:
            return None
        return self._raw_to_node_info(raw, region)

    def delete_node(self, node_id: str, region: str = '') -> Schema__Node__Delete__Response:
        from sg_compute.platforms.ec2.helpers.EC2__Instance__Helper import EC2__Instance__Helper
        helper = EC2__Instance__Helper()
        raw = helper.find_by_stack_name(region, node_id)
        if raw is None:
            return Schema__Node__Delete__Response(node_id=node_id, deleted=False, message='node not found')
        instance_id = raw.get('InstanceId', '')
        deleted = helper.terminate(region, instance_id)
        return Schema__Node__Delete__Response(node_id=node_id, deleted=deleted, message='terminated' if deleted else 'terminate failed')

    def create_node(self,
                    request : Schema__Node__Create__Request__Base,
                    spec    : Schema__Spec__Manifest__Entry) -> Schema__Node__Info:
        # Spec-specific services call their own AWS clients for now.
        # This generic path is a placeholder — spec services own orchestration.
        raise NotImplementedError('create_node: call the spec-specific service for now')
