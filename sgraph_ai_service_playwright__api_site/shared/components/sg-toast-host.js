// ── sg-toast-host — fixed bottom-right notification host ─────────────────── //
// Listens for sg-toast CustomEvent: { message, type, duration? }             //

const TEMPLATE = `
<style>
  :host {
    position: fixed;
    bottom: var(--spacing-lg, 24px);
    right: var(--spacing-lg, 24px);
    z-index: 2000;
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm, 8px);
    pointer-events: none;
  }

  .toast {
    background: var(--color-surface, #181b24);
    border: 1px solid var(--color-border, #2a2d3a);
    border-radius: var(--border-radius, 8px);
    padding: var(--spacing-sm, 8px) var(--spacing-md, 16px);
    color: var(--color-text, #e0e0e8);
    font-size: var(--font-size-sm, 0.875rem);
    max-width: 320px;
    pointer-events: auto;
    animation: slide-in 200ms ease;
  }

  .toast.success { border-color: var(--color-success, #1e6642); color: var(--color-success-text, #a0f0c0); }
  .toast.error   { border-color: var(--color-danger, #6a1a1a); color: var(--color-danger-text, #f0a0a0); }
  .toast.info    { border-color: var(--color-accent, #5b7cf6); }

  @keyframes slide-in {
    from { opacity: 0; transform: translateX(20px); }
    to   { opacity: 1; transform: translateX(0); }
  }
</style>
`;

class SgToastHost extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.shadowRoot.innerHTML = TEMPLATE;
    }

    connectedCallback() {
        document.addEventListener('sg-toast', (e) => this.show(e.detail));
    }

    show({ message, type = 'info', duration = 4000 }) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        this.shadowRoot.appendChild(toast);
        setTimeout(() => {
            if (toast.parentNode) toast.parentNode.removeChild(toast);
        }, duration);
    }
}

customElements.define('sg-toast-host', SgToastHost);
