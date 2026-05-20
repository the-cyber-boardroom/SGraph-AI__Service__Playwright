# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: Cli__SG_Edge__Proxy
# Typer app for `sg edge proxy` — proxy-asset helpers (pure, no AWS).
#
#   nginx-conf    print the bundled OpenResty nginx.conf
#   user-data     render the EC2 cloud-init user-data script
#   cf-function   print the CloudFront viewer-request JS
# ═══════════════════════════════════════════════════════════════════════════════

import typer

app = typer.Typer(name='proxy', help='Proxy-asset helpers (pure, no AWS).', no_args_is_help=True)


@app.command(name='nginx-conf', help='Print the bundled OpenResty nginx.conf.')
def nginx_conf():
    from sg_compute_specs.sg_edge.service.SG_Edge__Proxy__User_Data import SG_Edge__Proxy__User_Data
    print(SG_Edge__Proxy__User_Data().nginx_conf())


@app.command(name='user-data', help='Render the EC2 cloud-init user-data script.')
def user_data(version: str = typer.Option('dev', '--version', '-v', help='EDGE_VERSION label embedded in the script')):
    from sg_compute_specs.sg_edge.service.SG_Edge__Proxy__User_Data import SG_Edge__Proxy__User_Data
    print(SG_Edge__Proxy__User_Data(version=version).render())


@app.command(name='cf-function', help='Print the CloudFront viewer-request JS.')
def cf_function():
    from sg_compute_specs.sg_edge.service.SG_Edge__CloudFront__Function import SG_Edge__CloudFront__Function
    print(SG_Edge__CloudFront__Function().source())
