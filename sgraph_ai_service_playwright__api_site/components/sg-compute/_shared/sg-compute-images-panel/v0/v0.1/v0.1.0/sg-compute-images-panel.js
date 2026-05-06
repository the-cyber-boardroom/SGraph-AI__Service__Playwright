import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

const _EC2_CSS = new URL('../../../../../../../shared/ec2-tokens.css', import.meta.url).href

class SgComputeImagesPanel extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sg-compute-images-panel' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css', _EC2_CSS] }

    onReady() {
        this._banner    = this.$('.no-key-banner')
        this._list      = this.$('.img-list')
        this._s3Form    = this.$('.s3-form')
        this._s3Bucket  = this.$('.s3-bucket')
        this._s3Key     = this.$('.s3-key')
        this._s3Status  = this.$('.s3-status')
        this._status    = this.$('.img-status')

        this.$('.btn-refresh')?.addEventListener('click', () => this._load())
        this.$('.btn-s3-load')?.addEventListener('click', () => this._loadFromS3())

        if (this._pendingStack) { this.open(this._pendingStack); this._pendingStack = null }
    }

    open(stack) {
        if (!this._list) { this._pendingStack = stack; return }
        this._stack  = stack
        this._url    = stack.host_api_url || (stack.public_ip ? `http://${stack.public_ip}:19009` : '')
        this._key    = stack.host_api_key || ''

        if (!this._url) {
            this._showBanner('Node URL not available — node may still be starting.')
            return
        }
        if (!this._key) {
            this._showBanner('No API key — calls require authentication. (Resolved once Bug 4 backend fix lands.)')
        } else {
            this._hideBanner()
        }
        this._load()
    }

    async _load() {
        if (!this._url) return
        this._setStatus('Loading…')
        this._list.innerHTML = ''
        try {
            const resp = await this._fetch('GET', '/images')
            this._render(resp.images || [])
            this._setStatus('')
        } catch (err) {
            this._setStatus(`Error: ${err.message}`)
        }
    }

    _render(images) {
        this._list.innerHTML = ''
        if (!images.length) {
            const empty = document.createElement('div')
            empty.className = 'img-empty'
            empty.textContent = 'No images found on this node.'
            this._list.appendChild(empty)
            return
        }
        for (const img of images) {
            this._list.appendChild(this._makeRow(img))
        }
    }

    _makeRow(img) {
        const row = document.createElement('div')
        row.className = 'img-row'

        const tags = (img.tags || []).filter(t => t && !t.includes('<none>'))
        const primaryTag = tags[0] || img.id || '—'

        const nameEl = document.createElement('div')
        nameEl.className = 'img-name'
        nameEl.textContent = primaryTag
        if (tags.length > 1) nameEl.title = tags.join('\n')

        const idEl = document.createElement('div')
        idEl.className = 'img-id'
        idEl.textContent = img.id || '—'

        const sizeEl = document.createElement('div')
        sizeEl.className = 'img-size'
        sizeEl.textContent = img.size_mb ? `${img.size_mb} MB` : '—'

        const del = document.createElement('button')
        del.className = 'img-btn del'
        del.title = 'Remove image'
        del.textContent = '✕'
        del.addEventListener('click', async () => {
            if (!confirm(`Remove image ${primaryTag}?`)) return
            del.disabled = true
            try {
                await this._fetch('DELETE', `/images/delete/${encodeURIComponent(primaryTag)}`)
                row.remove()
                if (!this._list.querySelector('.img-row')) this._load()
            } catch (err) {
                this._setStatus(`Delete failed: ${err.message}`)
                del.disabled = false
            }
        })

        row.appendChild(nameEl)
        row.appendChild(idEl)
        row.appendChild(sizeEl)
        row.appendChild(del)
        return row
    }

    async _loadFromS3() {
        const bucket = this._s3Bucket?.value.trim()
        const key    = this._s3Key?.value.trim()
        if (!bucket || !key) { this._s3Status.textContent = 'Bucket and key are required.'; return }
        this._s3Status.textContent = 'Loading from S3…'
        this.$('.btn-s3-load').disabled = true
        try {
            const resp = await this._fetch('POST', '/images/load/from/s3', { bucket, key })
            if (resp.loaded) {
                this._s3Status.textContent = `✓ Loaded: ${resp.output || 'success'}`
                this._s3Bucket.value = ''
                this._s3Key.value    = ''
                this._load()
            } else {
                this._s3Status.textContent = `✗ Failed: ${resp.error || 'unknown error'}`
            }
        } catch (err) {
            this._s3Status.textContent = `✗ Error: ${err.message}`
        } finally {
            this.$('.btn-s3-load').disabled = false
        }
    }

    async _fetch(method, path, body) {
        const headers = { 'Content-Type': 'application/json' }
        if (this._key) headers['X-API-Key'] = this._key
        const opts = { method, headers }
        if (body) opts.body = JSON.stringify(body)
        const resp = await fetch(`${this._url}${path}`, opts)
        if (!resp.ok) {
            const text = await resp.text().catch(() => '')
            throw new Error(`${resp.status} ${resp.statusText}${text ? ': ' + text : ''}`)
        }
        return resp.json()
    }

    _setStatus(msg) { if (this._status) this._status.textContent = msg }
    _showBanner(msg) { if (this._banner) { this._banner.textContent = msg; this._banner.hidden = false } }
    _hideBanner()    { if (this._banner) this._banner.hidden = true }
}

customElements.define('sg-compute-images-panel', SgComputeImagesPanel)
