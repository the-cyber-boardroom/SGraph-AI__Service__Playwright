/**
 * sp-cli-catalog-pane — Stack type catalog for the admin dashboard.
 *
 * PR-3: coming-soon placeholder. PR-5 wires real type cards.
 *
 * @module sp-cli-catalog-pane
 * @version 0.1.0
 */

import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

class SpCliCatalogPane extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-catalog-pane' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {}
}

customElements.define('sp-cli-catalog-pane', SpCliCatalogPane)
