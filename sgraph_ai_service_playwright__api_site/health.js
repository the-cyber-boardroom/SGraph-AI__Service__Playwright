// ── health.js — fetch health endpoints and render results ────────────────────

const HEALTH_PATHS = ['health/info', 'health/status', 'health/capabilities'];

async function fetchHealth(cfg) {
  const headers = cfg.keyValue ? { [cfg.keyName]: cfg.keyValue } : {};
  const results = {};
  await Promise.all(HEALTH_PATHS.map(async path => {
    try {
      const r = await fetch(`${baseUrl(cfg)}/${path}`, { headers });
      results[path] = { status: r.status, body: await r.json().catch(() => r.text()) };
    } catch (err) {
      results[path] = { error: err.message };
    }
  }));
  return results;
}

function isHealthy(results) {
  return HEALTH_PATHS.every(p => results[p] && results[p].status === 200);
}

function renderHealthCard(results) {
  const card   = document.getElementById('health-card');
  const badge  = document.getElementById('health-badge');
  const output = document.getElementById('health-output');
  const ok     = isHealthy(results);

  badge.textContent = ok ? 'healthy' : 'error';
  badge.className   = 'badge ' + (ok ? 'badge--ok' : 'badge--err');
  output.textContent = JSON.stringify(results, null, 2);
  card.hidden = false;
}
