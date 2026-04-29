/**
 * sp-cli-compute-view — Compute view for the admin dashboard.
 *
 * PR-1: stub placeholder.
 * PR-4: becomes real with sp-cli-launcher-pane + sp-cli-stacks-pane.
 *
 * @module sp-cli-compute-view
 * @version 0.1.0
 */

import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

class SpCliComputeView extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-compute-view' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {}

    setData({ types, stacks } = {}) {
        // wired in PR-4 when launcher-pane and stacks-pane are embedded
    }
}

customElements.define('sp-cli-compute-view', SpCliComputeView)
