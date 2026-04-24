# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — SP__CLI__Lambda__Policy
# Builds the four inline IAM policy documents attached to the SP CLI Lambda
# execution role. Each document is tightly scoped:
#
#   • ec2_management — run/terminate instances, describe everything needed for
#                      preflight, create+authorize security groups, tag resources
#   • iam_passrole   — PassRole scoped to arn:aws:iam::{account}:role/playwright-ec2
#                      with iam:PassedToService=ec2.amazonaws.com (matches the
#                      narrow policy sp ensure-passrole attaches to the CLI user)
#   • ecr_read       — pull ECR image metadata + auth tokens for preflight
#   • sts_helpers    — GetCallerIdentity + DecodeAuthorizationMessage (the latter
#                      is used by the auto-decode error pretty-printer)
#
# Class exposes the four policies via document_*() methods so tests can assert
# the IAM Action list verbatim without a live AWS account.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__AWS__Account_Id     import Safe_Str__AWS__Account_Id


EC2_ROLE_NAME          = 'playwright-ec2'                                           # The EC2 instance role the CLI lambda needs to PassRole onto
EC2_SERVICE_PRINCIPAL  = 'ec2.amazonaws.com'


class SP__CLI__Lambda__Policy(Type_Safe):
    aws_account : Safe_Str__AWS__Account_Id                                         # Required — PassRole must be ARN-scoped, not "*"

    def document_ec2_management(self) -> dict:
        return {'Version'  : '2012-10-17',
                'Statement': [{'Sid'     : 'Ec2Describe',
                               'Effect'  : 'Allow',
                               'Action'  : ['ec2:DescribeInstances'        ,
                                            'ec2:DescribeInstanceStatus'   ,
                                            'ec2:DescribeImages'           ,
                                            'ec2:DescribeSecurityGroups'   ,
                                            'ec2:DescribeVpcs'             ,
                                            'ec2:DescribeSubnets'          ,
                                            'ec2:DescribeKeyPairs'         ,
                                            'ec2:DescribeInstanceTypes'    ],
                               'Resource': '*'                                                      },
                              {'Sid'     : 'Ec2RunAndTerminate',
                               'Effect'  : 'Allow',
                               'Action'  : ['ec2:RunInstances'             ,
                                            'ec2:TerminateInstances'       ,
                                            'ec2:StartInstances'           ,
                                            'ec2:StopInstances'            ,
                                            'ec2:CreateTags'               ],
                               'Resource': '*'                                                      },
                              {'Sid'     : 'Ec2SecurityGroupManagement',
                               'Effect'  : 'Allow',
                               'Action'  : ['ec2:CreateSecurityGroup'            ,
                                            'ec2:AuthorizeSecurityGroupIngress'  ,
                                            'ec2:AuthorizeSecurityGroupEgress'   ,
                                            'ec2:RevokeSecurityGroupIngress'     ,
                                            'ec2:RevokeSecurityGroupEgress'      ,
                                            'ec2:DeleteSecurityGroup'            ],
                               'Resource': '*'                                                      }]}

    def document_iam_passrole(self) -> dict:
        role_arn = f'arn:aws:iam::{self.aws_account}:role/{EC2_ROLE_NAME}'
        profile_arn = f'arn:aws:iam::{self.aws_account}:instance-profile/{EC2_ROLE_NAME}'
        return {'Version'  : '2012-10-17',
                'Statement': [{'Sid'       : 'PassPlaywrightEc2Role',
                               'Effect'    : 'Allow',
                               'Action'    : 'iam:PassRole',
                               'Resource'  : role_arn,
                               'Condition' : {'StringEquals': {'iam:PassedToService': EC2_SERVICE_PRINCIPAL}}
                              },
                              {'Sid'     : 'InstanceProfileManagement',
                               'Effect'  : 'Allow',
                               'Action'  : ['iam:GetRole'                      ,
                                            'iam:GetInstanceProfile'           ,
                                            'iam:CreateInstanceProfile'        ,
                                            'iam:AddRoleToInstanceProfile'     ,
                                            'iam:RemoveRoleFromInstanceProfile',
                                            'iam:DeleteInstanceProfile'        ],
                               'Resource': [role_arn, profile_arn]
                              }]}

    def document_ecr_read(self) -> dict:
        return {'Version'  : '2012-10-17',
                'Statement': [{'Sid'     : 'EcrRead',
                               'Effect'  : 'Allow',
                               'Action'  : ['ecr:GetAuthorizationToken'     ,
                                            'ecr:BatchGetImage'             ,
                                            'ecr:BatchCheckLayerAvailability',
                                            'ecr:DescribeImages'            ,
                                            'ecr:DescribeRepositories'      ,
                                            'ecr:GetDownloadUrlForLayer'    ,
                                            'ecr:ListImages'                ],
                               'Resource': '*'                                                      }]}

    def document_sts_helpers(self) -> dict:
        return {'Version'  : '2012-10-17',
                'Statement': [{'Sid'     : 'StsHelpers',
                               'Effect'  : 'Allow',
                               'Action'  : ['sts:GetCallerIdentity'             ,
                                            'sts:DecodeAuthorizationMessage'    ],
                               'Resource': '*'                                                      }]}

    def document_observability(self) -> dict:                                       # Covers the three AWS observability services Observability__Service talks to. READ + DELETE only — creates/updates are deferred until those mutation paths land.
        return {'Version'  : '2012-10-17',
                'Statement': [{'Sid'     : 'AmpReadDelete',                         # Amazon Managed Service for Prometheus uses the aps: namespace
                               'Effect'  : 'Allow',
                               'Action'  : ['aps:ListWorkspaces'                    ,
                                            'aps:DescribeWorkspace'                 ,
                                            'aps:DeleteWorkspace'                   ],
                               'Resource': '*'                                                      },
                              {'Sid'     : 'OpenSearchDescribe',                    # Domain-list / describe is account-wide; can't be ARN-scoped
                               'Effect'  : 'Allow',
                               'Action'  : ['es:ListDomainNames'                    ,
                                            'es:DescribeDomain'                     ,
                                            'es:DescribeDomains'                    ,
                                            'es:DeleteDomain'                       ],
                               'Resource': '*'                                                      },
                              {'Sid'     : 'OpenSearchHttpRead',                    # SigV4-signed HTTP GET on /{index}/_count — required for Observability__AWS__Client.opensearch_document_count
                               'Effect'  : 'Allow',
                               'Action'  : ['es:ESHttpGet'                          ],
                               'Resource': '*'                                                      },
                              {'Sid'     : 'GrafanaReadDelete',
                               'Effect'  : 'Allow',
                               'Action'  : ['grafana:ListWorkspaces'                ,
                                            'grafana:DescribeWorkspace'             ,
                                            'grafana:DeleteWorkspace'               ],
                               'Resource': '*'                                                      }]}

    def assume_role_document(self) -> dict:                                         # Trust policy — Lambda service can assume this role
        return {'Version'  : '2012-10-17',
                'Statement': [{'Effect'   : 'Allow',
                               'Principal': {'Service': 'lambda.amazonaws.com'},
                               'Action'   : 'sts:AssumeRole'                                       }]}
