// ═══════════════════════════════════════════════════════════════════════════
// SG/Sentinel — CF-env simulation HTTP listener (server.node.js)
// Runs the SAME engine file (sentinel_l1.js, resolved next to this script) — no
// divergence. Two ways in:
//   • Any HTTP request (GET/POST/…)        → builds the captured from THE REQUEST
//     itself (method, path, query, Host, X-Forwarded-For, User-Agent) and returns
//     the L1 signal. So `curl http://host/etc/passwd` shows the verdict directly.
//   • POST with a captured JSON body (has "path") → uses it verbatim (the harness
//     path — deterministic request_id/received_at for parity).
//   • GET /health                          → 200 'ok'
// Harness-facing only; never ships to CloudFront.
// ═══════════════════════════════════════════════════════════════════════════
var http = require('http');
var cp   = require('child_process');
var path = require('path');
var url  = require('url');

var PORT   = process.env.PORT || 8080;
var ENGINE = path.join(__dirname, 'sentinel_l1.js');                       // resolve next to this file — robust to WORKDIR

function captured_from_request(req, pathname, querystring) {
  var h = req.headers || {};
  var xff = (h['x-forwarded-for'] || '').split(',')[0].trim();
  return {
    request_id   : 'sn-' + Date.now().toString(16),
    aws_request_id: '',
    method       : req.method,
    path         : pathname,
    querystring  : querystring || '',
    host         : h.host || '',
    source_ip    : xff || (req.socket && req.socket.remoteAddress) || '',
    user_agent   : h['user-agent'] || '',
    received_at  : new Date().toISOString().replace(/\.\d+Z$/, 'Z'),
    cache_status : 'miss'
  };
}

function run_engine(captured, res) {
  cp.execFile('node', [ENGINE, JSON.stringify(captured)], function (err, stdout, stderr) {
    if (err) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: String(stderr || err) }));
      return;
    }
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(stdout);
  });
}

http.createServer(function (req, res) {
  var parsed   = url.parse(req.url);
  var pathname = parsed.pathname || '/';
  var qs       = parsed.query || '';

  if (req.method === 'GET' && pathname === '/health') {
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('ok');
    return;
  }

  var body = '';
  req.on('data', function (chunk) { body += chunk; });
  req.on('end', function () {
    var captured = null;
    if (body) {
      try {
        var parsed_body = JSON.parse(body);
        if (parsed_body && typeof parsed_body.path === 'string') {        // a captured object from the harness
          captured = parsed_body;
        }
      } catch (e) { /* not JSON → treat as a normal request below */ }
    }
    run_engine(captured || captured_from_request(req, pathname, qs), res);
  });
}).listen(PORT, function () {
  console.log('sentinel l1 cf-env sim listening on ' + PORT + ' (engine: ' + ENGINE + ')');
});
