/**
 * sp-cli-region-picker — Region selector for the top bar.
 *
 * Attributes:
 *   value  — active region (default: eu-west-2)
 *
 * Events:
 *   sp-cli:region-changed  — { region }
 *
 * @module sp-cli-region-picker
 * @version 0.1.0
 */

import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

const REGIONS = ['eu-west-2']   // expand when multi-region support lands

class SpCliRegionPicker extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-region-picker' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    static get observedAttributes() { return ['value'] }

    onReady() {
        this._btn   = this.$('.region-btn')
        this._panel = this.$('.panel')
        this._label = this.$('.region-label')
        this._renderValue()
        this._buildList()

        this._btn.addEventListener('click', () => this._toggle())
        document.addEventListener('click', (e) => {
            if (!this.contains(e.target) && !this.shadowRoot.contains(e.target)) this._close()
        })
    }

    attributeChangedCallback(name, _old, val) {
        if (name === 'value' && this.isReady) this._renderValue()
    }

    _renderValue() {
        if (this._label) this._label.textContent = this.getAttribute('value') || 'eu-west-2'
    }

    _buildList() {
        const list = this.$('.region-list')
        if (!list) return
        list.innerHTML = ''
        const active = this.getAttribute('value') || 'eu-west-2'
        for (const r of REGIONS) {
            const item = document.createElement('button')
            item.className = 'region-item' + (r === active ? ' active' : '')
            item.textContent = r
            item.addEventListener('click', () => { this._select(r); this._close() })
            list.appendChild(item)
        }
    }

    _select(region) {
        this.setAttribute('value', region)
        this.emit('sp-cli:region-changed', { region })
    }

    _toggle() {
        this._panel.hidden = !this._panel.hidden
    }

    _close() { if (this._panel) this._panel.hidden = true }
}

customElements.define('sp-cli-region-picker', SpCliRegionPicker)
