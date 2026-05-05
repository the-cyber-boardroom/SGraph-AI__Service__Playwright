/**
 * sg-compute-active-sessions — shows the current browser session.
 *
 * Multi-user tracking lands with the per-instance API brief.
 *
 * @module sg-compute-active-sessions
 * @version 0.1.0
 */

import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

class SgComputeActiveSessions extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sg-compute-active-sessions' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._startedAt = Date.now()
        this._uptimeEl  = this.$('.session-uptime')
        setInterval(() => this._tick(), 30_000)
        this._tick()
    }

    _tick() {
        const s = Math.round((Date.now() - this._startedAt) / 1000)
        const m = Math.floor(s / 60)
        const h = Math.floor(m / 60)
        const label = h > 0 ? `${h}h ${m % 60}m` : m > 0 ? `${m}m` : `${s}s`
        if (this._uptimeEl) this._uptimeEl.textContent = label
    }
}

customElements.define('sg-compute-active-sessions', SgComputeActiveSessions)
