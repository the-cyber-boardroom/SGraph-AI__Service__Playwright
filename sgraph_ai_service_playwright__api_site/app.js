// ── app.js — wires form, buttons, and panels together ────────────────────────

function showMsg(text, isErr = false) {
  const el = document.getElementById('save-msg');
  el.textContent = text;
  el.className   = 'msg' + (isErr ? ' msg--err' : '');
  clearTimeout(el._t);
  el._t = setTimeout(() => { el.textContent = ''; el.className = 'msg'; }, 4000);
}

function buildLinks(cfg) {
  const base  = baseUrl(cfg);
  const items = [
    { label: 'health/info',         href: `${base}/health/info`         },
    { label: 'health/status',       href: `${base}/health/status`       },
    { label: 'health/capabilities', href: `${base}/health/capabilities` },
    { label: 'openapi.json',        href: `${base}/openapi.json`        },
    { label: 'docs (Swagger)',       href: `${base}/docs`               },
    { label: 'admin/info',          href: `${base}/admin/info`          },
    { label: 'admin/boot-log',      href: `${base}/admin/boot-log`      },
    { label: 'set auth cookie',     href: `${base}/auth/set-cookie-form`},
  ];
  const list = document.getElementById('links-list');
  list.innerHTML = '';
  items.forEach(({ label, href }) => {
    const li = document.createElement('li');
    li.innerHTML = `<a href="${href}" target="_blank" rel="noopener">
      <span class="link-label">${label}</span>
      <span>${href}</span>
    </a>`;
    list.appendChild(li);
  });
  document.getElementById('links-card').hidden = false;
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  populateForm(getConfig());

  // show/hide key value
  const keyInput = document.getElementById('key-value');
  document.getElementById('toggle-key').addEventListener('click', () => {
    keyInput.type = keyInput.type === 'password' ? 'text' : 'password';
  });

  // Save
  document.getElementById('btn-save').addEventListener('click', () => {
    const cfg = readForm();
    if (!cfg.ip) { showMsg('Enter an IP / host.', true); return; }
    saveConfig(cfg);
    buildLinks(cfg);
    showMsg('Saved.');
  });

  // Check health
  document.getElementById('btn-health').addEventListener('click', async () => {
    const cfg = readForm();
    if (!cfg.ip) { showMsg('Enter an IP / host.', true); return; }
    showMsg('Checking...');
    const results = await fetchHealth(cfg);
    renderHealthCard(results);
    showMsg(isHealthy(results) ? 'All endpoints healthy.' : 'One or more endpoints failed.', !isHealthy(results));
  });

  // Set cookie
  document.getElementById('btn-cookie').addEventListener('click', () => {
    const cfg = readForm();
    openCookieForm(cfg);
  });

  // If we have a saved IP, render links immediately
  const saved = getConfig();
  if (saved.ip) buildLinks(saved);
});
