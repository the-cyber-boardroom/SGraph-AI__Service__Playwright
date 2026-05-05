# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — EC2__Platform
# Implements the Platform interface using the EC2 helpers.
# list_nodes / get_node / delete_node use the spec-service tag convention
# (sg:stack-name, sg:purpose) so they find nodes from any spec.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.core.node.schemas.Schema__Node__Create__Request__Base        import Schema__Node__Create__Request__Base
from sg_compute.core.node.schemas.Schema__Node__Delete__Response             import Schema__Node__Delete__Response
from sg_compute.core.node.schemas.Schema__Node__Info                         import Schema__Node__Info
from sg_compute.core.node.schemas.Schema__Node__List                         import Schema__Node__List
from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry              import Schema__Spec__Manifest__Entry
from sg_compute.platforms.Platform                                            import Platform
from sg_compute.platforms.exceptions.Exception__AWS__No_Credentials          import Exception__AWS__No_Credentials
from sg_compute.primitives.enums.Enum__Node__State                           import Enum__Node__State


class EC2__Platform(Platform):
    name : str = 'ec2'

    def setup(self) -> 'EC2__Platform':
        return self

    @staticmethod
    def _tag(raw: dict, key: str) -> str:
        for t in raw.get('Tags', []):
            if t.get('Key') == key:
                return t.get('Value', '')
        return ''

    def _raw_to_node_info(self, raw: dict, region: str, spec_id: str = '') -> Schema__Node__Info:
        from sg_compute.platforms.ec2.helpers.EC2__Stack__Mapper import state_str, uptime_seconds
        state_map = {
            'running'      : Enum__Node__State.READY      ,
            'pending'      : Enum__Node__State.BOOTING    ,
            'shutting-down': Enum__Node__State.TERMINATING,
            'terminated'   : Enum__Node__State.TERMINATED ,
            'stopping'     : Enum__Node__State.TERMINATING,
            'stopped'      : Enum__Node__State.TERMINATED ,
        }
        node_id = self._tag(raw, 'sg:stack-name') or self._tag(raw, 'StackName')
        spec_id = spec_id or self._tag(raw, 'sg:purpose') or self._tag(raw, 'StackType')
        return Schema__Node__Info(
            node_id       = node_id                                                      ,
            spec_id       = spec_id                                                      ,
            region        = region                                                       ,
            state         = state_map.get(state_str(raw), Enum__Node__State.FAILED)     ,
            public_ip     = raw.get('PublicIpAddress',  '')                              ,
            private_ip    = raw.get('PrivateIpAddress', '')                              ,
            instance_id   = raw.get('InstanceId',       '')                              ,
            instance_type = raw.get('InstanceType',     '')                              ,
            ami_id        = raw.get('ImageId',          '')                              ,
            uptime_seconds= uptime_seconds(raw)                                          ,
        )

    def list_nodes(self, region: str = 'eu-west-2') -> Schema__Node__List:
        from sg_compute.platforms.ec2.helpers.EC2__Instance__Helper import EC2__Instance__Helper
        region = region or 'eu-west-2'
        try:
            raw_nodes = EC2__Instance__Helper().list_all_managed(region)
        except Exception as e:
            if 'credential' in str(e).lower() or 'NoCredential' in type(e).__name__:
                raise Exception__AWS__No_Credentials(str(e)) from e
            raise
        nodes = [self._raw_to_node_info(raw, region) for raw in raw_nodes.values()]
        return Schema__Node__List(nodes=nodes, total=len(nodes), region=region)

    def get_node(self, node_id: str, region: str = 'eu-west-2') -> 'Schema__Node__Info | None':
        from sg_compute.platforms.ec2.helpers.EC2__Instance__Helper import EC2__Instance__Helper
        region = region or 'eu-west-2'
        raw    = EC2__Instance__Helper().find_by_sg_stack_name(region, node_id)
        return self._raw_to_node_info(raw, region) if raw else None

    def delete_node(self, node_id: str, region: str = 'eu-west-2') -> Schema__Node__Delete__Response:
        from sg_compute.platforms.ec2.helpers.EC2__Instance__Helper import EC2__Instance__Helper
        region  = region or 'eu-west-2'
        helper  = EC2__Instance__Helper()
        raw     = helper.find_by_sg_stack_name(region, node_id)
        if raw is None:
            return Schema__Node__Delete__Response(node_id=node_id, deleted=False, message='node not found')
        deleted = helper.terminate(region, raw.get('InstanceId', ''))
        return Schema__Node__Delete__Response(node_id  = node_id                                  ,
                                              deleted  = deleted                                   ,
                                              message  = 'terminated' if deleted else 'failed'    )

    def create_node(self,
                    request : Schema__Node__Create__Request__Base,
                    spec    : Schema__Spec__Manifest__Entry) -> Schema__Node__Info:
        raise NotImplementedError('create_node: call the spec-specific service directly')
