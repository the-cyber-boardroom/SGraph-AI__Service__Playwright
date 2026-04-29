// ── sg-create-modal — 3-state stack creation modal ─────────────────────── //
// States: form → progress → ready                                            //
// Accepts stack-type attribute. Uses apiClient + startPoll internally.      //

import { apiClient } from '../api-client.js';
import { startPoll  } from '../poll.js';

const TEMPLATE = `
<style>
  :host { display: none; position: fixed; inset: 0; z-index: 1000; align-items: center; justify-content: center; background: rgba(0,0,0,0.6); }
  :host([open]) { display: flex; }

  .modal {
    background: var(--color-surface, #181b24);
    border: 1px solid var(--color-border, #2a2d3a);
    border-radius: var(--border-radius, 8px);
    padding: var(--spacing-lg, 24px);
    width: min(480px, 90vw);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md, 16px);
  }

  h2 { color: var(--color-text, #e0e0e8); font-size: var(--font-size-lg, 1.125rem); margin: 0; }

  label { display: block; font-size: var(--font-size-sm, 0.875rem); color: var(--color-text-muted, #8888aa); margin-bottom: var(--spacing-xs, 4px); text-transform: uppercase; letter-spacing: 0.03em; }

  input {
    width: 100%;
    background: var(--color-bg, #0f1117);
    border: 1px solid var(--color-border, #2a2d3a);
    border-radius: var(--border-radius-sm, 6px);
    color: var(--color-text, #e0e0e8);
    font-size: var(--font-size-base, 1rem);
    font-family: var(--font-family-mono, monospace);
    padding: 0.5rem 0.75rem;
    box-sizing: border-box;
    transition: border-color var(--transition-fast, 150ms ease);
  }
  input:focus { outline: none; border-color: var(--color-accent, #5b7cf6); }

  .btn-row { display: flex; gap: var(--spacing-sm, 8px); }

  button {
    padding: 0.45rem 1rem;
    border-radius: var(--border-radius-sm, 6px);
    border: 1px solid var(--color-border, #2a2d3a);
    background: var(--color-surface-alt, #22253a);
    color: var(--color-text, #e0e0e8);
    font-size: var(--font-size-sm, 0.875rem);
    cursor: pointer;
    transition: background var(--transition-fast, 150ms ease);
  }
  button.primary { background: #2d4adf; border-color: #3a5aef; }
  button:hover { opacity: 0.85; }

  .progress-bar-wrap { background: var(--color-bg, #0f1117); border-radius: 99px; height: 6px; overflow: hidden; }
  .progress-bar { height: 100%; background: var(--color-accent, #5b7cf6); width: 0; transition: width 0.5s ease; animation: pulse-bar 1.5s ease-in-out infinite; }
  @keyframes pulse-bar { 0%,100% { opacity: 1; } 50% { opacity: 0.6; } }

  .log-area {
    background: var(--color-bg, #0f1117);
    border: 1px solid var(--color-border, #2a2d3a);
    border-radius: var(--border-radius-sm, 6px);
    padding: var(--spacing-sm, 8px);
    font-size: 0.78rem;
    font-family: var(--font-family-mono, monospace);
    color: #a0c8a0;
    max-height: 180px;
    overflow-y: auto;
    white-space: pre-wrap;
  }

  .ssm-copy { display: flex; gap: var(--spacing-xs, 4px); }
  .ssm-display { flex: 1; background: var(--color-bg, #0f1117); border: 1px solid var(--color-border, #2a2d3a); border-radius: var(--border-radius-sm, 6px); padding: 0.4rem 0.6rem; font-size: 0.78rem; font-family: var(--font-family-mono, monospace); color: #a0c8a0; word-break: break-all; }
  .copy-btn { background: var(--color-surface-alt, #22253a); border-color: var(--color-border, #2a2d3a); color: var(--color-text-muted, #8888aa); }

  [hidden] { display: none !important; }
</style>
<div class="modal">
  <h2 id="modal-title">Create Stack</h2>

  <!-- form state -->
  <div id="state-form">
    <label>Stack Name (optional)</label>
    <input id="name-input" type="text" placeholder="auto-generated if blank" spellcheck="false">
    <div class="btn-row" style="margin-top: var(--spacing-sm, 8px)">
      <button class="primary" id="create-btn">Create</button>
      <button id="cancel-btn">Cancel</button>
    </div>
  </div>

  <!-- progress state -->
  <div id="state-progress" hidden>
    <div class="progress-bar-wrap"><div class="progress-bar" id="progress-bar" style="width:30%"></div></div>
    <div class="log-area" id="log-area">Provisioning…\n</div>
  </div>

  <!-- ready state -->
  <div id="state-ready" hidden>
    <p style="color: var(--color-success-text, #a0f0c0)">Stack is ready.</p>
    <div id="ssm-section" hidden>
      <label>SSM Connect Command</label>
      <div class="ssm-copy">
        <div class="ssm-display" id="ssm-display"></div>
        <button class="copy-btn" id="copy-ssm-btn" title="Copy">⎘</button>
      </div>
    </div>
    <div class="btn-row" style="margin-top: var(--spacing-sm, 8px)">
      <button id="close-ready-btn">Close</button>
    </div>
  </div>
</div>
`;

class SgCreateModal extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.shadowRoot.innerHTML = TEMPLATE;
        this._stopPoll = null;
    }

    connectedCallback() {
        this.shadowRoot.getElementById('create-btn').addEventListener('click', () => this.submit());
        this.shadowRoot.getElementById('cancel-btn').addEventListener('click', () => this.closeModal());
        this.shadowRoot.getElementById('close-ready-btn').addEventListener('click', () => this.closeModal());
        this.shadowRoot.getElementById('copy-ssm-btn').addEventListener('click', () => {
            const text = this.shadowRoot.getElementById('ssm-display').textContent;
            navigator.clipboard?.writeText(text);
        });
    }

    openModal() {
        this.setAttribute('open', '');
        this.setState('form');
    }

    closeModal() {
        if (this._stopPoll) { this._stopPoll(); this._stopPoll = null; }
        this.removeAttribute('open');
        this.shadowRoot.getElementById('name-input').value = '';
        this.shadowRoot.getElementById('log-area').textContent = 'Provisioning…\n';
    }

    setState(name) {
        ['form', 'progress', 'ready'].forEach(s => {
            const el = this.shadowRoot.getElementById(`state-${s}`);
            if (s === name) el.removeAttribute('hidden'); else el.setAttribute('hidden', '');
        });
    }

    log(message) {
        const area = this.shadowRoot.getElementById('log-area');
        area.textContent += message + '\n';
        area.scrollTop = area.scrollHeight;
    }

    async submit() {
        const stackType = this.getAttribute('stack-type') || '';
        const name      = this.shadowRoot.getElementById('name-input').value.trim();
        this.setState('progress');

        let created;
        try {
            const body = name ? { stack_name: name } : {};
            created = await apiClient.post(`/${stackType}/stack`, body);
        } catch (err) {
            this.log(`Error: ${err.message}`);
            return;
        }

        const stackName = created.stack_name || created.name || name;
        this.log(`Stack ${stackName} created. Waiting for READY…`);

        this._stopPoll = startPoll(
            () => apiClient.get(`/${stackType}/stack/${stackName}/health`),
            ({ status, data, error }) => {
                if (error) { this.log(`Poll error: ${error.message}`); return; }
                if (data)  { this.log(`Status: ${JSON.stringify(data.status ?? status)}`); }
                if (status === 'READY' || data?.all_ok === true) {
                    this._stopPoll = null;
                    this.showReady(data, created);
                }
            },
            { timeout: 600000, stopOn: ['READY', 'ERROR'] }
        );
    }

    showReady(healthData, created) {
        const ssm = created?.ssm_command || healthData?.ssm_command || '';
        if (ssm) {
            this.shadowRoot.getElementById('ssm-section').removeAttribute('hidden');
            this.shadowRoot.getElementById('ssm-display').textContent = ssm;
        }
        this.setState('ready');
    }
}

customElements.define('sg-create-modal', SgCreateModal);
