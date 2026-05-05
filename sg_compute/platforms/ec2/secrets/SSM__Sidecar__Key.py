# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — SSM__Sidecar__Key
# Per-node sidecar API key stored as a SecureString in SSM Parameter Store.
# Path convention: /sg-compute/nodes/{node_id}/sidecar-api-key
#
# Why SSM and not user-data: EC2 user-data is readable from inside the instance
# via IMDS (169.254.169.254/latest/user-data). Any pod on the node can exfiltrate
# a plaintext key. SSM SecureString is read via the Node's IAM role at boot;
# the key never appears in user-data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

SSM_PATH_PREFIX = '/sg-compute/nodes'


class SSM__Sidecar__Key(Type_Safe):

    @staticmethod
    def path_for(node_id: str) -> str:
        return f'{SSM_PATH_PREFIX}/{node_id}/sidecar-api-key'

    def write(self, node_id: str, key: str) -> bool:
        from osbot_aws.helpers.Parameter import Parameter                       # osbot_aws wrapper; never raw boto3
        result = Parameter(name=self.path_for(node_id)).put_secret(key)
        return result is not None

    def read(self, node_id: str) -> str:
        from osbot_aws.helpers.Parameter import Parameter
        return Parameter(name=self.path_for(node_id)).value_secret() or ''

    def delete(self, node_id: str) -> bool:
        from osbot_aws.helpers.Parameter import Parameter
        return Parameter(name=self.path_for(node_id)).delete()

    def exists(self, node_id: str) -> bool:
        from osbot_aws.helpers.Parameter import Parameter
        return Parameter(name=self.path_for(node_id)).exists()
