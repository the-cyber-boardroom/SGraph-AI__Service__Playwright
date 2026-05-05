/**
 * sg-compute-top-bar — Provisioning Console top bar.
 *
 * Attributes:
 *   page-title  — "Provisioning Console", "Admin Dashboard", etc.
 *   region      — defaults to eu-west-2
 *
 * Events:
 *   sp-cli:region-changed   — { region }
 *   sp-cli:brand-clicked
 *
 * @module sg-compute-top-bar
 * @version 0.1.0
 */

import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

class SgComputeTopBar extends SgComponent {

    static jsUrl = import.meta.url

    get resourceName() { return 'sg-compute-top-bar' }

    get sharedCssPaths() {
        return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css']
    }

    static get observedAttributes() { return ['page-title', 'region'] }

    onReady() {
        this._titleEl  = this.$('.page-title')
        this._regionEl = this.$('.region-picker')
        this._renderTitle()
        this._renderRegion()

        this.$('.brand-mark')?.addEventListener('click', () =>
            this.emit('sp-cli:brand-clicked')
        )

        this.$('.btn-diagnostics')?.addEventListener('click', () =>
            document.dispatchEvent(new CustomEvent('sp-cli:nav.selected', {
                detail: { view: 'diagnostics' }, bubbles: true, composed: true,
            }))
        )
    }

    attributeChangedCallback(name, _old, newVal) {
        if (!this.isReady) return
        if (name === 'page-title') this._renderTitle()
        if (name === 'region')     this._renderRegion()
    }

    _renderTitle() {
        if (this._titleEl) this._titleEl.textContent = this.getAttribute('page-title') || ''
    }

    _renderRegion() {
        if (this._regionEl) this._regionEl.textContent = this.getAttribute('region') || 'eu-west-2'
    }
}

customElements.define('sg-compute-top-bar', SgComputeTopBar)
