import { SgComponent        } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import { getAllPluginToggles } from '../../../../../../shared/settings-bus.js'
import { getCatalogue        } from '../../../../../../shared/spec-catalogue.js'

class SpCliLauncherPane extends SgComponent {
    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-launcher-pane' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._grid     = this.$('.card-grid')
        this._emptyMsg = this.$('.empty-msg')

        this.$('.btn-collapse')?.addEventListener('click', () => {
            this.classList.toggle('collapsed')
        })

        document.addEventListener('sp-cli:settings.loaded',   () => this._renderCards())
        document.addEventListener('sp-cli:plugin.toggled',    () => this._renderCards())
        document.addEventListener('sp-cli:catalogue.loaded',  () => this._renderCards())

        this._renderCards()
    }

    _renderCards() {
        if (!this._grid) return
        this._grid.innerHTML = ''

        let specs
        try { specs = getCatalogue().specs || [] } catch (_) { return }

        const toggles = getAllPluginToggles()
        const enabled = specs.filter(s => !s.soon && (toggles[s.spec_id]?.enabled ?? true))

        this._emptyMsg.hidden = enabled.length > 0
        this._grid.hidden     = enabled.length === 0

        for (const spec of enabled) {
            const card = document.createElement(`sp-cli-${spec.spec_id}-card`)
            this._grid.appendChild(card)
        }
    }
}

customElements.define('sp-cli-launcher-pane', SpCliLauncherPane)
