// ── sg-stack-grid — multi-mode grid container ────────────────────────────── //
// mode="admin-table"  : table of all active stacks (compact cards per row)  //
// mode="type-cards"   : catalog type cards with name, description, badge    //
// mode="user-cards"   : Start buttons per available type                    //
// mode="user-active"  : user's active stacks in detail card mode            //
// Dispatches sg-start-stack { type } when a Start button is clicked.        //

const TEMPLATE = `
<style>
  :host { display: block; }

  table { width: 100%; border-collapse: collapse; }
  th, td { padding: var(--spacing-sm, 8px) var(--spacing-md, 16px); text-align: left; border-bottom: 1px solid var(--color-border, #2a2d3a); }
  th { font-size: var(--font-size-sm, 0.875rem); color: var(--color-text-muted, #8888aa); font-weight: 500; text-transform: uppercase; letter-spacing: 0.03em; }
  td { color: var(--color-text, #e0e0e8); font-size: var(--font-size-sm, 0.875rem); }

  .cards-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: var(--spacing-md, 16px); }

  .type-card {
    background: var(--color-surface, #181b24);
    border: 1px solid var(--color-border, #2a2d3a);
    border-radius: var(--border-radius, 8px);
    padding: var(--spacing-md, 16px);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs, 4px);
  }

  .type-card .card-name { font-weight: 600; color: var(--color-text, #e0e0e8); }
  .type-card .card-desc { font-size: var(--font-size-sm, 0.875rem); color: var(--color-text-muted, #8888aa); flex: 1; }

  .avail-badge {
    align-self: flex-start;
    font-size: 0.7rem; font-weight: 600;
    padding: 0.15rem 0.45rem;
    border-radius: 99px;
  }
  .avail-badge.yes { background: #1e6642; color: #a0f0c0; }
  .avail-badge.no  { background: #22253a; color: #888; }

  .start-btn {
    margin-top: var(--spacing-xs, 4px);
    padding: 0.4rem 1rem;
    border-radius: var(--border-radius-sm, 6px);
    border: 1px solid #3a5aef;
    background: #2d4adf;
    color: #e0e0e8;
    font-size: var(--font-size-sm, 0.875rem);
    cursor: pointer;
    transition: background var(--transition-fast, 150ms ease);
    width: 100%;
  }
  .start-btn:hover:not(:disabled) { background: #3a5aef; }
  .start-btn:disabled { background: #22253a; border-color: #2a2d3a; color: #555; cursor: not-allowed; }

  .empty { color: var(--color-text-muted, #8888aa); font-size: var(--font-size-sm, 0.875rem); padding: var(--spacing-md, 16px) 0; }
</style>
<div id="root"></div>
`;

class SgStackGrid extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.shadowRoot.innerHTML = TEMPLATE;
        this._stacks  = [];
        this._catalog = [];
    }

    set stacks(value)  { this._stacks  = value || []; this.render(); }
    set catalog(value) { this._catalog = value || []; this.render(); }

    get stacks()  { return this._stacks; }
    get catalog() { return this._catalog; }

    static get observedAttributes() { return ['mode']; }
    attributeChangedCallback() { this.render(); }

    connectedCallback() { this.render(); }

    render() {
        const mode = this.getAttribute('mode') || 'admin-table';
        const root = this.shadowRoot.getElementById('root');
        root.innerHTML = '';

        if (mode === 'admin-table') {
            root.appendChild(this.renderAdminTable());
        } else if (mode === 'type-cards') {
            root.appendChild(this.renderTypeCards());
        } else if (mode === 'user-cards') {
            root.appendChild(this.renderUserCards());
        } else if (mode === 'user-active') {
            root.appendChild(this.renderUserActive());
        }
    }

    renderAdminTable() {
        if (!this._stacks.length) {
            const p = document.createElement('p');
            p.className = 'empty';
            p.textContent = 'No active stacks.';
            return p;
        }
        const table = document.createElement('table');
        table.innerHTML = '<thead><tr><th>Name</th><th>Type</th><th>Status</th><th>Region</th><th></th></tr></thead>';
        const tbody = document.createElement('tbody');
        for (const stack of this._stacks) {
            const tr = document.createElement('tr');
            tr.innerHTML = `
              <td>${stack.name || ''}</td>
              <td>${stack.type || ''}</td>
              <td>${stack.status || ''}</td>
              <td>${stack.region || ''}</td>
              <td></td>
            `;
            const cardCell = tr.querySelector('td:last-child');
            const card = document.createElement('sg-stack-card');
            card.setAttribute('mode', 'compact');
            card.stack = stack;
            card.addEventListener('sg-stop-stack', (e) => {
                this.dispatchEvent(new CustomEvent('sg-stop-stack', { bubbles: true, composed: true, detail: e.detail }));
            });
            cardCell.appendChild(card);
            tbody.appendChild(tr);
        }
        table.appendChild(tbody);
        return table;
    }

    renderTypeCards() {
        const grid = document.createElement('div');
        grid.className = 'cards-grid';
        if (!this._catalog.length) {
            const p = document.createElement('p');
            p.className = 'empty';
            p.textContent = 'No stack types available.';
            return p;
        }
        for (const t of this._catalog) {
            const card = document.createElement('div');
            card.className = 'type-card';
            const badge = t.available !== false ? '<span class="avail-badge yes">Available</span>' : '<span class="avail-badge no">Unavailable</span>';
            card.innerHTML = `
              <div class="card-name">${t.name || ''}</div>
              <div class="card-desc">${t.description || ''}</div>
              ${badge}
            `;
            grid.appendChild(card);
        }
        return grid;
    }

    renderUserCards() {
        const grid = document.createElement('div');
        grid.className = 'cards-grid';
        if (!this._catalog.length) {
            const p = document.createElement('p');
            p.className = 'empty';
            p.textContent = 'No stack types available.';
            return p;
        }
        for (const t of this._catalog) {
            const card = document.createElement('div');
            card.className = 'type-card';
            const disabled = t.available === false ? 'disabled' : '';
            card.innerHTML = `
              <div class="card-name">${t.name || ''}</div>
              <div class="card-desc">${t.description || ''}</div>
              <button class="start-btn" data-type="${t.name || ''}" ${disabled}>Start</button>
            `;
            const btn = card.querySelector('.start-btn');
            if (!disabled) {
                btn.addEventListener('click', () => {
                    this.dispatchEvent(new CustomEvent('sg-start-stack', {
                        bubbles: true, composed: true, detail: { type: t.name }
                    }));
                });
            }
            grid.appendChild(card);
        }
        return grid;
    }

    renderUserActive() {
        const wrap = document.createElement('div');
        wrap.style.display = 'flex';
        wrap.style.flexDirection = 'column';
        wrap.style.gap = 'var(--spacing-md, 16px)';
        if (!this._stacks.length) {
            const p = document.createElement('p');
            p.className = 'empty';
            p.textContent = 'No active stacks.';
            return p;
        }
        for (const stack of this._stacks) {
            const card = document.createElement('sg-stack-card');
            card.setAttribute('mode', 'detail');
            card.stack = stack;
            card.addEventListener('sg-stop-stack', (e) => {
                this.dispatchEvent(new CustomEvent('sg-stop-stack', { bubbles: true, composed: true, detail: e.detail }));
            });
            wrap.appendChild(card);
        }
        return wrap;
    }
}

customElements.define('sg-stack-grid', SgStackGrid);
