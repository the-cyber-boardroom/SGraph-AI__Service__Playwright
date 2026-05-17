# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Podman__AMI__Helper
# Resolves the latest AL2023 AMI for a given region via SSM public parameter.
# Mirrors Linux__AMI__Helper.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


AL2023_SSM_PARAM = '/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64'


class Podman__AMI__Helper(Type_Safe):

    def ssm_client(self, region: str):
        from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session  import Sg__Aws__Session
        from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store import Credentials__Store
        return Sg__Aws__Session(store=Credentials__Store()).boto3_client_from_context(
            service_name='ssm', region=region or '')

    def latest_al2023_ami_id(self, region: str) -> str:
        resp = self.ssm_client(region).get_parameter(Name=AL2023_SSM_PARAM)
        return resp.get('Parameter', {}).get('Value', '')
