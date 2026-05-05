import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

class SgComputeStacksView extends SgComponent {
    static jsUrl = import.meta.url
    get resourceName()   { return 'sg-compute-stacks-view' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }
}

customElements.define('sg-compute-stacks-view', SgComputeStacksView)
