// ── sg-stack-card — single stack display (compact | detail mode) ─────────── //
// Accepts `stack` property: { name, type, status, region, ssm_command? }    //
// Stop button dispatches sg-stop-stack: { name, type }                      //

const STATUS_COLOURS = {
    running  : '#6adf9a',
    ready    : '#6adf9a',
    pending  : '#f0e08a',
    stopped  : '#888',
    error    : '#f09090',
    unknown  : '#888',
};

const TEMPLATE = `
<style>
  :host { display: block; }

  .card {
    background: var(--color-surface, #181b24);
    border: 1px solid var(--color-border, #2a2d3a);
    border-radius: var(--border-radius, 8px);
    padding: var(--spacing-md, 16px);
  }

  .row { display: flex; align-items: center; gap: var(--spacing-sm, 8px); flex-wrap: wrap; }

  .dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
    background: var(--dot-color, #888);
  }

  .name  { font-weight: 600; color: var(--color-text, #e0e0e8); font-family: var(--font-family-mono, monospace); }
  .badge {
    font-size: 0.7rem; font-weight: 600;
    padding: 0.15rem 0.45rem;
    border-radius: 99px;
    background: #22253a;
    color: #8888aa;
    border: 1px solid #2a2d3a;
  }
  .region { font-size: var(--font-size-sm, 0.875rem); color: var(--color-text-muted, #8888aa); margin-left: auto; }

  .detail-section { margin-top: var(--spacing-sm, 8px); display: flex; flex-direction: column; gap: var(--spacing-xs, 4px); }
  .ssm-row { display: flex; align-items: center; gap: var(--spacing-xs, 4px); }
  .ssm-cmd {
    flex: 1;
    background: var(--color-bg, #0f1117);
    border: 1px solid var(--color-border, #2a2d3a);
    border-radius: var(--border-radius-sm, 6px);
    color: #a0c8a0;
    font-size: 0.78rem;
    font-family: var(--font-family-mono, monospace);
    padding: 0.3rem 0.5rem;
    white-space: pre-wrap;
    word-break: break-all;
  }

  button {
    padding: 0.3rem 0.75rem;
    border-radius: var(--border-radius-sm, 6px);
    border: 1px solid #6a1a1a;
    background: #3a0a0a;
    color: #f0a0a0;
    font-size: var(--font-size-sm, 0.875rem);
    cursor: pointer;
    transition: background var(--transition-fast, 150ms ease);
  }
  button:hover { background: #5a1a1a; }
  .copy-btn {
    background: var(--color-surface-alt, #22253a);
    border-color: var(--color-border, #2a2d3a);
    color: var(--color-text-muted, #8888aa);
  }
  .copy-btn:hover { color: var(--color-text, #e0e0e8); }
</style>
<div class="card">
  <div class="row">
    <span class="dot" id="status-dot"></span>
    <span class="name" id="name"></span>
    <span class="badge" id="type-badge"></span>
    <span class="region" id="region"></span>
  </div>
  <div class="detail-section" id="detail-section" hidden>
    <div class="ssm-row" id="ssm-row" hidden>
      <code class="ssm-cmd" id="ssm-cmd"></code>
      <button class="copy-btn" id="copy-btn" title="Copy SSM command">⎘</button>
    </div>
    <div>
      <button id="stop-btn">Stop</button>
    </div>
  </div>
</div>
`;

class SgStackCard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.shadowRoot.innerHTML = TEMPLATE;
        this._stack = null;
    }

    connectedCallback() {
        this.shadowRoot.getElementById('stop-btn').addEventListener('click', () => {
            if (!this._stack) return;
            this.dispatchEvent(new CustomEvent('sg-stop-stack', {
                bubbles: true, composed: true,
                detail : { name: this._stack.name, type: this._stack.type }
            }));
        });
        this.shadowRoot.getElementById('copy-btn').addEventListener('click', () => {
            const cmd = this.shadowRoot.getElementById('ssm-cmd').textContent;
            navigator.clipboard?.writeText(cmd);
        });
        this.render();
    }

    set stack(value) {
        this._stack = value;
        this.render();
    }

    get stack() { return this._stack; }

    static get observedAttributes() { return ['mode']; }
    attributeChangedCallback() { this.render(); }

    render() {
        if (!this._stack) return;
        const s    = this._stack;
        const mode = this.getAttribute('mode') || 'compact';

        const dot = this.shadowRoot.getElementById('status-dot');
        dot.style.setProperty('--dot-color', STATUS_COLOURS[s.status?.toLowerCase()] || '#888');

        this.shadowRoot.getElementById('name').textContent      = s.name   || '';
        this.shadowRoot.getElementById('type-badge').textContent = s.type  || '';
        this.shadowRoot.getElementById('region').textContent    = s.region || '';

        const detailSection = this.shadowRoot.getElementById('detail-section');
        if (mode === 'detail') {
            detailSection.removeAttribute('hidden');
            const ssmRow = this.shadowRoot.getElementById('ssm-row');
            if (s.ssm_command) {
                ssmRow.removeAttribute('hidden');
                this.shadowRoot.getElementById('ssm-cmd').textContent = s.ssm_command;
            } else {
                ssmRow.setAttribute('hidden', '');
            }
        } else {
            detailSection.setAttribute('hidden', '');
        }
    }
}

customElements.define('sg-stack-card', SgStackCard);
