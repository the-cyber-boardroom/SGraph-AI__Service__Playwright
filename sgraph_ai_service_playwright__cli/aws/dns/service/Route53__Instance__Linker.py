# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Route53__Instance__Linker
# Resolves an EC2 instance reference (id, Name tag, or "latest SG-AI instance")
# to a public IP that can be used for an A-record mutation.
#
# EXCEPTION — boto3 EC2 direct use: no osbot-aws EC2 wrapper exists that
# covers the describe_instances paginator path used here. Follows the same
# narrow-exception pattern as Route53__AWS__Client and Elastic__AWS__Client.
# ═══════════════════════════════════════════════════════════════════════════════

import boto3                                                                      # EXCEPTION — see module header

from osbot_utils.type_safe.Type_Safe                                                 import Type_Safe


class Route53__Instance__Linker(Type_Safe):                                      # Resolves EC2 instance references to public IPs

    def ec2_client(self):                                                        # Single seam — tests override to return a fake client
        return boto3.client('ec2')

    def resolve_instance(self, instance_ref: str) -> dict:                       # Resolve by instance-id or by Name tag; returns first running match
        ec2 = self.ec2_client()
        if instance_ref.startswith('i-'):
            resp = ec2.describe_instances(InstanceIds=[instance_ref])
        else:
            resp = ec2.describe_instances(Filters=[
                {'Name': 'tag:Name'        , 'Values': [instance_ref]},
                {'Name': 'instance-state-name', 'Values': ['running'] },
            ])
        instances = [i for r in resp.get('Reservations', [])
                       for i in r.get('Instances', [])]
        if not instances:
            raise ValueError(f"No running instance found matching '{instance_ref}'")
        if len(instances) > 1 and not instance_ref.startswith('i-'):
            raise ValueError(f"Ambiguous: {len(instances)} instances match Name='{instance_ref}'. Use an instance-id.")
        return instances[0]

    def resolve_latest(self) -> dict:                                            # Returns most recently launched running SG-managed instance. Matches both the legacy `sg:*` tag prefix (elastic / playwright / vnc / podman) AND the new sg_compute platform tag `Purpose=ephemeral-ec2` (vault_app / ollama / open_design — see sg_compute/platforms/ec2/helpers/EC2__Tags__Builder.py).
        ec2  = self.ec2_client()
        resp = ec2.describe_instances(Filters=[
            {'Name': 'instance-state-name', 'Values': ['running']},
        ])
        instances = []
        for r in resp.get('Reservations', []):
            for i in r.get('Instances', []):
                tags          = i.get('Tags', [])
                has_sg_prefix = any(t.get('Key', '').startswith('sg:') for t in tags)
                is_ephemeral  = any(t.get('Key') == 'Purpose' and t.get('Value') == 'ephemeral-ec2' for t in tags)
                if has_sg_prefix or is_ephemeral:
                    instances.append(i)
        if not instances:
            raise ValueError('No running SG-managed instance found '
                              '(no instance with sg:* tag or Purpose=ephemeral-ec2 tag).')
        instances.sort(key=lambda i: i.get('LaunchTime', ''), reverse=True)
        return instances[0]

    def get_public_ip(self, instance: dict) -> str:                             # Returns PublicIpAddress or raises ValueError if the instance has none
        ip = instance.get('PublicIpAddress')
        if not ip:
            iid = instance.get('InstanceId', '?')
            raise ValueError(f"Instance {iid} has no public IP address.")
        return ip

    def get_name_tag(self, instance: dict) -> str:                              # Returns the Name tag value or falls back to the instance-id
        for tag in instance.get('Tags', []):
            if tag.get('Key') == 'Name':
                return tag.get('Value', '')
        return instance.get('InstanceId', '')
