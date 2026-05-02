import { SgComponent        } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import { getAllPluginToggles } from '../../../../../../shared/settings-bus.js'

const PLUGIN_ORDER = ['docker', 'podman', 'elastic', 'vnc', 'prometheus', 'opensearch', 'neko', 'firefox']

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

        document.addEventListener('sp-cli:settings.loaded', () => this._renderCards())
        document.addEventListener('sp-cli:plugin.toggled',  () => this._renderCards())

        this._renderCards()
    }

    _renderCards() {
        if (!this._grid) return
        this._grid.innerHTML = ''

        const toggles = getAllPluginToggles()
        const enabled = PLUGIN_ORDER.filter(name => toggles[name]?.enabled)

        this._emptyMsg.hidden = enabled.length > 0
        this._grid.hidden     = enabled.length === 0

        for (const name of enabled) {
            const card = document.createElement(`sp-cli-${name}-card`)
            this._grid.appendChild(card)
        }
    }
}

customElements.define('sp-cli-launcher-pane', SpCliLauncherPane)
