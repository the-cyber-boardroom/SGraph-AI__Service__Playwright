/**
 * sp-cli-settings-view — Settings view stub.
 *
 * PR-1: stub placeholder.
 * PR-3: becomes real with feature toggles + settings-bus.
 *
 * @module sp-cli-settings-view
 * @version 0.1.0
 */

import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

class SpCliSettingsView extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-settings-view' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {}
}

customElements.define('sp-cli-settings-view', SpCliSettingsView)
