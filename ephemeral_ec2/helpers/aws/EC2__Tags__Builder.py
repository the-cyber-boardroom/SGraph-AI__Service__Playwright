# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — EC2__Tags__Builder
# Builds the standard EC2 tag list for any ephemeral stack.
# Pure mapper — no AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                          import List

from osbot_utils.type_safe.Type_Safe import Type_Safe


TAG_PURPOSE_KEY   = 'Purpose'
TAG_PURPOSE_VALUE = 'ephemeral-ec2'
TAG_STACK_NAME    = 'StackName'
TAG_STACK_TYPE    = 'StackType'
TAG_CALLER_IP     = 'CallerIP'
TAG_CREATED_BY    = 'CreatedBy'


class EC2__Tags__Builder(Type_Safe):
    stack_type : str = 'ephemeral-ec2'

    def build(self, stack_name: str, caller_ip: str,
              creator   : str  = '',
              extra_tags : dict = None) -> List[dict]:
        tags = [
            {'Key': 'Name'          , 'Value': stack_name              },
            {'Key': TAG_PURPOSE_KEY , 'Value': TAG_PURPOSE_VALUE       },
            {'Key': TAG_STACK_NAME  , 'Value': stack_name              },
            {'Key': TAG_STACK_TYPE  , 'Value': self.stack_type         },
            {'Key': TAG_CALLER_IP   , 'Value': caller_ip               },
            {'Key': TAG_CREATED_BY  , 'Value': creator or 'unknown'    },
        ]
        for k, v in (extra_tags or {}).items():
            tags.append({'Key': k, 'Value': str(v)})
        return tags
