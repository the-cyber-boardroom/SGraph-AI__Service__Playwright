# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — EC2__Name__Resolver
# Resolves an <id-or-name> argument to a concrete instance ID.
#
# Accepts:
#   - bare instance IDs (i-XXXXXXXXXXXXXXXXX) → returned as-is
#   - Name tag values → fuzzy lookup; errors on 0 or >1 matches
#
# Ambiguity policy: raises ValueError listing all matching IDs so the caller
# can surface them to the user.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.ec2.service.EC2__AWS__Client import EC2__AWS__Client


class EC2__Name__Resolver(Type_Safe):

    ec2_client : EC2__AWS__Client

    def setup(self):                                                            # lazy default
        if self.ec2_client is None:
            self.ec2_client = EC2__AWS__Client()
        return self

    def resolve(self, target: str) -> str:                                     # Returns concrete instance ID or raises ValueError
        if target.startswith('i-'):
            return target                                                       # already an ID — trust it
        instances = self.ec2_client.list_instances(state='all')
        matches   = [(str(inst.instance_id), inst.name)
                     for inst in instances
                     if inst.name == target]
        if not matches:
            prefix_matches = [(str(inst.instance_id), inst.name)
                              for inst in instances
                              if inst.name.startswith(target)]
            if not prefix_matches:
                raise ValueError(f'No instance found matching name {target!r}')
            matches = prefix_matches
        if len(matches) > 1:
            ids = ', '.join(f'{m[0]} ({m[1]!r})' for m in matches)
            raise ValueError(f'Ambiguous name {target!r} — matches: {ids}')
        return matches[0][0]
