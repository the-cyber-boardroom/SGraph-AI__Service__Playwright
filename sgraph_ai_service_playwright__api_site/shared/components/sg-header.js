// ── sg-header — top bar with title slot and settings button ─────────────── //
// Settings button click dispatches sg-show-auth on document.                //

const TEMPLATE = `
<style>
  :host { display: block; background: var(--color-surface, #181b24); border-bottom: 1px solid var(--color-border, #2a2d3a); }

  header {
    max-width: 1200px;
    margin: 0 auto;
    padding: var(--spacing-md, 16px) var(--spacing-lg, 24px);
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  h1 {
    font-size: var(--font-size-lg, 1.125rem);
    font-weight: 700;
    color: var(--color-text, #e0e0e8);
    margin: 0;
  }

  button {
    background: transparent;
    border: 1px solid var(--color-border, #2a2d3a);
    border-radius: var(--border-radius-sm, 6px);
    color: var(--color-text-muted, #8888aa);
    cursor: pointer;
    font-size: 1.1rem;
    padding: 0.3rem 0.5rem;
    line-height: 1;
    transition: color var(--transition-fast, 150ms ease), border-color var(--transition-fast, 150ms ease);
  }
  button:hover { color: var(--color-text, #e0e0e8); border-color: var(--color-accent, #5b7cf6); }
</style>
<header>
  <h1 id="title-slot"></h1>
  <button id="settings-btn" title="API connection settings">⚙</button>
</header>
`;

class SgHeader extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.shadowRoot.innerHTML = TEMPLATE;
    }

    connectedCallback() {
        this.shadowRoot.getElementById('title-slot').textContent = this.getAttribute('title') || '';
        this.shadowRoot.getElementById('settings-btn').addEventListener('click', () => {
            document.dispatchEvent(new CustomEvent('sg-show-auth', { bubbles: true }));
        });
    }

    static get observedAttributes() { return ['title']; }

    attributeChangedCallback(name, _old, value) {
        if (name === 'title') {
            const el = this.shadowRoot.getElementById('title-slot');
            if (el) el.textContent = value || '';
        }
    }
}

customElements.define('sg-header', SgHeader);
