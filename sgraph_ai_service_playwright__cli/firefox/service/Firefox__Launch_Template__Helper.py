# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Firefox__Launch_Template__Helper
# EC2 Launch Template CRUD for Firefox ASG stacks.
#
# create_or_update  — creates LT or adds a new version if name already exists
# list_templates    — returns all sg:purpose=firefox LTs in the region
# delete_template   — deletes a LT by name (all versions)
# ═══════════════════════════════════════════════════════════════════════════════

import base64
import gzip

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.firefox.service.Firefox__AWS__Client         import TAG_PURPOSE_KEY, TAG_PURPOSE_VALUE


class Firefox__Launch_Template__Helper(Type_Safe):

    def ec2_client(self, region: str):
        from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session  import Sg__Aws__Session
        from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store import Credentials__Store
        return Sg__Aws__Session(store=Credentials__Store()).boto3_client_from_context(
            service_name='ec2', region=region or '')

    def create_or_update(self, region: str, lt_name: str, ami_id: str,
                          instance_type: str, sg_id: str, user_data: str,
                          profile_name: str, instance_tags: list) -> dict:          # → {'lt_id', 'lt_version'}
        ec2   = self.ec2_client(region)
        ud_b64 = base64.b64encode(gzip.compress(user_data.encode('utf-8'))).decode('ascii')
        lt_data = dict(ImageId          = ami_id                              ,
                       InstanceType     = instance_type                       ,
                       SecurityGroupIds = [sg_id]                             ,
                       UserData         = ud_b64                              ,
                       IamInstanceProfile = {'Name': profile_name}            ,
                       TagSpecifications  = [{'ResourceType': 'instance',
                                              'Tags'        : instance_tags}] )
        try:
            resp = ec2.create_launch_template(
                LaunchTemplateName = lt_name  ,
                LaunchTemplateData = lt_data  ,
                TagSpecifications  = [{'ResourceType': 'launch-template',
                                       'Tags': [{'Key': TAG_PURPOSE_KEY, 'Value': TAG_PURPOSE_VALUE}]}])
            lt = resp['LaunchTemplate']
            return {'lt_id': lt['LaunchTemplateId'], 'lt_version': lt['LatestVersionNumber']}
        except Exception as exc:
            if 'AlreadyExistsException' not in str(exc):
                raise
            resp = ec2.create_launch_template_version(
                LaunchTemplateName = lt_name ,
                LaunchTemplateData = lt_data )
            v = resp['LaunchTemplateVersion']
            return {'lt_id': v['LaunchTemplateId'], 'lt_version': v['VersionNumber']}

    def list_templates(self, region: str) -> list:
        ec2  = self.ec2_client(region)
        resp = ec2.describe_launch_templates(
            Filters=[{'Name': f'tag:{TAG_PURPOSE_KEY}', 'Values': [TAG_PURPOSE_VALUE]}])
        return resp.get('LaunchTemplates', [])

    def delete_template(self, region: str, lt_name: str) -> bool:
        try:
            self.ec2_client(region).delete_launch_template(LaunchTemplateName=lt_name)
            return True
        except Exception:
            return False
