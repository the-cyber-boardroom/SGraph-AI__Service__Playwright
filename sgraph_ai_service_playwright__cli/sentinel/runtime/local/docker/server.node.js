// ═══════════════════════════════════════════════════════════════════════════
// SG/Sentinel — CF-env simulation HTTP listener (server.node.js)
// Minimal HTTP server: per POST it takes the captured request JSON (body) and
// shells `node sentinel_l1.js '<captured>'` — the SAME engine file, no divergence —
// returning the emitted signal JSON. This is harness-facing only; it is NOT part
// of the engine and never ships to CloudFront.
//
//   POST /        body = captured request (snake_case JSON)  -> 200 signal JSON
//   GET  /health                                             -> 200 'ok'
// ═══════════════════════════════════════════════════════════════════════════
var http = require('http');
var cp   = require('child_process');
var PORT = process.env.PORT || 8080;

http.createServer(function (req, res) {
  if (req.method === 'GET' && req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('ok');
    return;
  }
  if (req.method !== 'POST') {
    res.writeHead(405);
    res.end();
    return;
  }
  var body = '';
  req.on('data', function (chunk) { body += chunk; });
  req.on('end', function () {
    cp.execFile('node', ['/app/sentinel_l1.js', body], function (err, stdout, stderr) {
      if (err) {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: String(stderr || err) }));
        return;
      }
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(stdout);
    });
  });
}).listen(PORT, function () {
  console.log('sentinel l1 cf-env sim listening on ' + PORT);
});
