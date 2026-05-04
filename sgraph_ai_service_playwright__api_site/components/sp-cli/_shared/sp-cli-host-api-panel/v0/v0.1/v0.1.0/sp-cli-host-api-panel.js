import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

const _EC2_CSS = new URL('../../../../../../../shared/ec2-tokens.css', import.meta.url).href
const SWAGGER_CSS = 'https://unpkg.com/swagger-ui-dist@5/swagger-ui.css'
const SWAGGER_JS  = 'https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js'

class SpCliHostApiPanel extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sp-cli-host-api-panel' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css', _EC2_CSS] }

    onReady() {
        this._container   = this.$('.swagger-mount')
        this._unavailable = this.$('.unavailable')
        this._status      = this.$('.api-status')
        if (this._pendingStack) { this.open(this._pendingStack); this._pendingStack = null }
    }

    open(stack) {
        if (!this._container) { this._pendingStack = stack; return }
        this._hostUrl = stack.host_api_url || (stack.public_ip ? `http://${stack.public_ip}:19009` : '')
        this._apiKey  = stack.host_api_key || ''
        this._render()
    }

    async _render() {
        if (!this._hostUrl) {
            this._unavailable?.classList.remove('hidden')
            return
        }
        this._unavailable?.classList.add('hidden')
        this._setStatus('Loading API spec…')

        try {
            await this._loadSwaggerBundle()
            await this._loadSwaggerCss()
        } catch (err) {
            this._setStatus(`Failed to load Swagger UI: ${err.message}`)
            return
        }

        this._container.innerHTML = ''
        const key = this._apiKey

        try {
            window.SwaggerUIBundle({
                url:            `${this._hostUrl}/openapi.json`,
                domNode:        this._container,
                presets:        [window.SwaggerUIBundle.presets.apis],
                layout:         'BaseLayout',
                tryItOutEnabled: true,
                requestInterceptor: (req) => {
                    if (key) req.headers['X-API-Key'] = key
                    return req
                },
                onComplete: () => this._setStatus(key ? '🔑 Authenticated' : '⚠ No API key'),
            })
        } catch (err) {
            this._setStatus(`Swagger init failed: ${err.message}`)
        }
    }

    _setStatus(msg) {
        if (this._status) this._status.textContent = msg
    }

    _loadSwaggerBundle() {
        if (window.SwaggerUIBundle) return Promise.resolve()
        return new Promise((resolve, reject) => {
            const s = document.createElement('script')
            s.src = SWAGGER_JS
            s.onload  = resolve
            s.onerror = () => reject(new Error('Could not load swagger-ui-bundle.js'))
            document.head.appendChild(s)
        })
    }

    _loadSwaggerCss() {
        if (this.shadowRoot.querySelector('.swagger-css-link')) return Promise.resolve()
        return new Promise((resolve) => {
            const link = document.createElement('link')
            link.rel = 'stylesheet'
            link.href = SWAGGER_CSS
            link.className = 'swagger-css-link'
            link.onload = resolve
            link.onerror = resolve  // non-fatal — UI will render without styles
            this.shadowRoot.insertBefore(link, this.shadowRoot.firstChild)
        })
    }
}

customElements.define('sp-cli-host-api-panel', SpCliHostApiPanel)
