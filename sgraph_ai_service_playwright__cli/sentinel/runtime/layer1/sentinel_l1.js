// ═══════════════════════════════════════════════════════════════════════════
// SG/Sentinel Layer 1 — sentinel_l1.js
// Decide + signal ONLY. No I/O, never blocks, always returns the request.
// Runs on: CloudFront Functions (handler), Node CLI (guarded tail), Docker server.
//
// Single source. The empty BANNED_IPS array below is the inlining marker — the
// deployer (for CloudFront) and the local harness (for node/docker) replace the
// line `var BANNED_IPS = [];` with the list from rules.embedded.json before use.
// Constraints: CloudFront Functions 2.0 / ES5.1-ish. No require, no module,
// no Buffer/btoa, no top-level process. The header value is raw compact JSON.
// ═══════════════════════════════════════════════════════════════════════════
var ENGINE_VERSION  = '0.1.0';
var RULESET_VERSION = '0.1.0';
var BANNED_IPS = [];

function evaluate(c) {                       // c = captured request object (snake_case)
  var hit =
        rule_0007_malformed(c)        ||
        rule_0003_banned_ip(c)        ||
        rule_0012_path_never_valid(c) ||
        rule_0014_hidden_file(c)      ||
        rule_0018_wp_scan(c)          ||
        { verdict: 'allow', reason: 'no rule matched', rule_id: '0001', action: 'pass' };
  return {
    request_id: c.request_id, aws_request_id: c.aws_request_id || '',
    captured: c, verdict: hit.verdict, reason: hit.reason,
    rule_id: hit.rule_id, action: hit.action, layer: 'L1',
    engine_version: ENGINE_VERSION, ruleset_version: RULESET_VERSION
  };
}

function rule_0007_malformed(c){ if(!c.method||!c.path||c.path.charAt(0)!=='/') return {verdict:'block',reason:'malformed request',rule_id:'0007',action:'drop_403'}; }
function rule_0003_banned_ip(c){ if(BANNED_IPS.indexOf(c.source_ip)>=0) return {verdict:'block',reason:'banned ip',rule_id:'0003',action:'drop_403'}; }
function rule_0012_path_never_valid(c){ var p=c.path.toLowerCase(); if(p.indexOf('/etc/passwd')>=0||p.indexOf('..')>=0) return {verdict:'block',reason:'path never valid',rule_id:'0012',action:'drop_403'}; }
function rule_0014_hidden_file(c){ if(/^\/\.(env|git)(\/|$)/.test(c.path)) return {verdict:'block',reason:'hidden file probe',rule_id:'0014',action:'deflect_404'}; }
function rule_0018_wp_scan(c){ var p=c.path.toLowerCase(); if(p==='/wp-login.php'||p==='/xmlrpc.php'||p.indexOf('/wp-admin')===0) return {verdict:'block',reason:'wordpress scan on static site',rule_id:'0018',action:'deflect_404'}; }

function handler(event) {                     // CloudFront Functions entry (viewer-request)
  var r = event.request;
  var c = {
    request_id: 'sn-' + (event.context && event.context.requestId ? event.context.requestId : new Date().getTime().toString(16)),
    aws_request_id: (event.context && event.context.requestId) || '',
    method: r.method, path: r.uri, querystring: (r.querystring && r.querystring.value) || '',
    host: (r.headers.host && r.headers.host.value) || '',
    source_ip: (event.viewer && event.viewer.ip) || '',
    user_agent: (r.headers['user-agent'] && r.headers['user-agent'].value) || '',
    received_at: new Date().toISOString().replace(/\.\d+Z$/, 'Z'),
    cache_status: 'miss'
  };
  r.headers['x-sentinel-signal'] = { value: JSON.stringify(evaluate(c)) };
  return r;                                   // ALWAYS return the request; L1 never acts
}

// Node CLI tail — guarded so it never runs on CloudFront (no `process` there)
if (typeof process !== 'undefined' && process.argv && process.argv[2]) {
  console.log(JSON.stringify(evaluate(JSON.parse(process.argv[2]))));
}
