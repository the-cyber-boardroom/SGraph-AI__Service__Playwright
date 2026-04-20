// ── storage.js — localStorage persistence for connection config ──────────────

const STORAGE_KEY = 'sg_playwright_config';

function saveConfig(cfg) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg)); } catch (_) {}
}

function loadConfig() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch (_) { return {}; }
}

function getConfig() {
  const cfg = loadConfig();
  return {
    ip      : cfg.ip       || '',
    port    : cfg.port     || 8000,
    keyName : cfg.keyName  || 'X-API-Key',
    keyValue: cfg.keyValue || '',
  };
}

function readForm() {
  return {
    ip      : document.getElementById('ip').value.trim(),
    port    : parseInt(document.getElementById('port').value, 10) || 8000,
    keyName : document.getElementById('key-name').value.trim() || 'X-API-Key',
    keyValue: document.getElementById('key-value').value.trim(),
  };
}

function populateForm(cfg) {
  document.getElementById('ip').value        = cfg.ip;
  document.getElementById('port').value      = cfg.port;
  document.getElementById('key-name').value  = cfg.keyName;
  document.getElementById('key-value').value = cfg.keyValue;
}

function baseUrl(cfg) {
  return `http://${cfg.ip}:${cfg.port}`;
}
