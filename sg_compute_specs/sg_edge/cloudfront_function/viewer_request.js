// ═══════════════════════════════════════════════════════════════════════════════
// SG/Edge — CloudFront Function (viewer-request)
// Runs at the CloudFront edge before the request reaches the proxy origin.
// CloudFront rewrites the Host header to the origin's domain, so we capture the
// original viewer host and the extracted slug into custom headers the OpenResty
// proxy reads (X-SG-Host, X-SG-Slug). The slug is the first DNS label of the
// viewer host (alice.cv.sgraph.ai -> alice). This is the CloudFront Functions
// JS runtime (ES5-ish, no ES6, no async) — keep it tiny and allocation-light.
// ═══════════════════════════════════════════════════════════════════════════════

function handler(event) {
    var request = event.request;
    var headers = request.headers;

    var host = (headers.host && headers.host.value) ? headers.host.value : '';
    var slug = host.split('.')[0] || '';

    headers['x-sg-host'] = { value: host };   // preserve the original viewer host
    headers['x-sg-slug'] = { value: slug };   // first label — the slug the proxy routes on

    return request;
}
