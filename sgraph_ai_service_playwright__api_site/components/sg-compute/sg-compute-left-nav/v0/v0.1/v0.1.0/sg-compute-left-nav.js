/**
 * sg-compute-left-nav — vertical icon-rail navigation for the admin dashboard.
 *
 * Items: Compute / Storage / Settings / Diagnostics.
 * Click fires sp-cli:nav.selected { view } on document.
 *
 * @module sg-compute-left-nav
 * @version 0.1.0
 */

import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

class SgComputeLeftNav extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sg-compute-left-nav' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._current = 'compute'
        this.shadowRoot.querySelectorAll('.nav-item').forEach(btn => {
            btn.addEventListener('click', () => this._select(btn.dataset.view))
        })
        this._update()
    }

    _select(view) {
        if (view === this._current) return
        this._current = view
        this._update()
        document.dispatchEvent(new CustomEvent('sp-cli:nav.selected', {
            detail:  { view },
            bubbles: true, composed: true,
        }))
    }

    _update() {
        this.shadowRoot.querySelectorAll('.nav-item').forEach(btn => {
            btn.classList.toggle('selected', btn.dataset.view === this._current)
            btn.setAttribute('aria-current', btn.dataset.view === this._current ? 'page' : 'false')
        })
    }
}

customElements.define('sg-compute-left-nav', SgComputeLeftNav)
