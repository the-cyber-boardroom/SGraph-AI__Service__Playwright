// ── sg-auth-panel — connection drawer Web Component ─────────────────────── //
// Opens/closes via the `open` attribute. Listens for sg-show-auth.           //

import { apiClient } from '../api-client.js';

const TEMPLATE = `
<style>
  :host { display: none; position: fixed; inset: 0; z-index: 1000; align-items: flex-start; justify-content: flex-end; background: rgba(0,0,0,0.5); }
  :host([open]) { display: flex; }

  .drawer {
    background: var(--color-surface, #181b24);
    border-left: 1px solid var(--color-border, #2a2d3a);
    width: min(400px, 100vw);
    height: 100%;
    padding: var(--spacing-lg, 24px);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md, 16px);
    overflow-y: auto;
  }

  h2 { color: var(--color-text, #e0e0e8); font-size: var(--font-size-lg, 1.125rem); margin: 0; }

  label {
    display: block;
    font-size: var(--font-size-sm, 0.875rem);
    color: var(--color-text-muted, #8888aa);
    margin-bottom: var(--spacing-xs, 4px);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

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

  .btn-row { display: flex; gap: var(--spacing-sm, 8px); margin-top: var(--spacing-sm, 8px); }

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
  button:hover   { opacity: 0.85; }
</style>
<div class="drawer">
  <h2>API Connection</h2>
  <div>
    <label>API URL</label>
    <input id="url-input" type="text" placeholder="https://api.example.com" spellcheck="false">
  </div>
  <div>
    <label>API Key</label>
    <input id="key-input" type="password" placeholder="paste key here" spellcheck="false" autocomplete="off">
  </div>
  <div class="btn-row">
    <button class="primary" id="save-btn">Save</button>
    <button id="close-btn">Close</button>
  </div>
</div>
`;

class SgAuthPanel extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.shadowRoot.innerHTML = TEMPLATE;
    }

    connectedCallback() {
        this.shadowRoot.getElementById('save-btn').addEventListener('click', () => this.save());
        this.shadowRoot.getElementById('close-btn').addEventListener('click', () => this.close());

        document.addEventListener('sg-show-auth', () => this.open());

        this.shadowRoot.getElementById('url-input').value = apiClient.apiUrl;
        this.shadowRoot.getElementById('key-input').value = apiClient.apiKey;
    }

    open() {
        this.setAttribute('open', '');
    }

    close() {
        this.removeAttribute('open');
    }

    save() {
        const url = this.shadowRoot.getElementById('url-input').value.trim();
        const key = this.shadowRoot.getElementById('key-input').value.trim();
        apiClient.save(url, key);
        document.dispatchEvent(new CustomEvent('sg-auth-saved', { bubbles: true, detail: { url, key } }));
        this.close();
    }
}

customElements.define('sg-auth-panel', SgAuthPanel);
