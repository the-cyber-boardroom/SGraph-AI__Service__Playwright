# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/ec2 — EC2__Pricing__Client
# On-demand pricing queries for EC2 instance types.
#
# AWS Pricing API is only available in us-east-1 regardless of the caller's
# configured region. This client always pins us-east-1 for pricing calls.
# ═══════════════════════════════════════════════════════════════════════════════

import json

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.ec2.primitives.Safe_Str__EC2__Instance__Type import Safe_Str__EC2__Instance__Type
from sgraph_ai_service_playwright__cli.aws.ec2.schemas.Schema__EC2__Pricing              import Schema__EC2__Pricing


class EC2__Pricing__Client(Type_Safe):

    def client(self):                                                           # Pricing API lives exclusively in us-east-1
        from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session import Sg__Aws__Session
        return Sg__Aws__Session.from_context().boto3_client_from_context('pricing', region='us-east-1')

    def get_price(self, instance_type: str, region: str = 'us-east-1',
                  os: str = 'Linux') -> Schema__EC2__Pricing:
        pricing_client = self.client()
        region_name    = self._region_long_name(region)
        filters = [
            {'Type': 'TERM_MATCH', 'Field': 'instanceType',    'Value': instance_type},
            {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': os},
            {'Type': 'TERM_MATCH', 'Field': 'location',        'Value': region_name},
            {'Type': 'TERM_MATCH', 'Field': 'tenancy',         'Value': 'Shared'},
            {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw',  'Value': 'NA'},
            {'Type': 'TERM_MATCH', 'Field': 'capacitystatus',  'Value': 'Used'},
        ]
        try:
            resp  = pricing_client.get_products(ServiceCode='AmazonEC2', Filters=filters, MaxResults=5)
            items = resp.get('PriceList', [])
            if not items:
                return self._empty_pricing(instance_type, region, os)
            price_doc = json.loads(items[0])
            price_per_hour = self._extract_price(price_doc)
            price_per_second = ''
            if price_per_hour:
                try:
                    pph = float(price_per_hour)
                    price_per_second = f'{pph / 3600:.12f}'.rstrip('0')
                except ValueError:
                    pass
            itype_safe = Safe_Str__EC2__Instance__Type(instance_type) if instance_type else Safe_Str__EC2__Instance__Type('')
            return Schema__EC2__Pricing(
                instance_type    = itype_safe,
                region           = region,
                price_per_hour   = price_per_hour,
                price_per_second = price_per_second,
                os               = os,
            )
        except Exception:
            return self._empty_pricing(instance_type, region, os)

    def _empty_pricing(self, instance_type: str, region: str, os: str) -> Schema__EC2__Pricing:
        itype_safe = Safe_Str__EC2__Instance__Type(instance_type) if instance_type else Safe_Str__EC2__Instance__Type('')
        return Schema__EC2__Pricing(
            instance_type    = itype_safe,
            region           = region,
            price_per_hour   = '',
            price_per_second = '',
            os               = os,
        )

    def _extract_price(self, price_doc: dict) -> str:                          # Walks the nested pricing JSON to find the USD on-demand price per hour
        terms = price_doc.get('terms', {}).get('OnDemand', {})
        for _, term in terms.items():
            for _, dim in term.get('priceDimensions', {}).items():
                price_per_unit = dim.get('pricePerUnit', {})
                usd = price_per_unit.get('USD', '')
                if usd and usd != '0.0000000000':
                    return usd
        return ''

    def _region_long_name(self, region: str) -> str:                           # Maps short AWS region IDs to the long names the Pricing API requires
        mapping = {
            'us-east-1'      : 'US East (N. Virginia)',
            'us-east-2'      : 'US East (Ohio)',
            'us-west-1'      : 'US West (N. California)',
            'us-west-2'      : 'US West (Oregon)',
            'eu-west-1'      : 'Europe (Ireland)',
            'eu-west-2'      : 'Europe (London)',
            'eu-west-3'      : 'Europe (Paris)',
            'eu-central-1'   : 'Europe (Frankfurt)',
            'eu-north-1'     : 'Europe (Stockholm)',
            'ap-southeast-1' : 'Asia Pacific (Singapore)',
            'ap-southeast-2' : 'Asia Pacific (Sydney)',
            'ap-northeast-1' : 'Asia Pacific (Tokyo)',
            'ap-northeast-2' : 'Asia Pacific (Seoul)',
            'ap-south-1'     : 'Asia Pacific (Mumbai)',
            'sa-east-1'      : 'South America (São Paulo)',
            'ca-central-1'   : 'Canada (Central)',
        }
        return mapping.get(region, 'US East (N. Virginia)')
