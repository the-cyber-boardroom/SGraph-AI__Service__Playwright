import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'

const REGIONS        = ['eu-west-2', 'us-east-1', 'ap-southeast-1', 'eu-west-1', 'us-west-2']
const INSTANCE_TYPES = ['t3.micro', 't3.small', 't3.medium', 't3.large', 't3.xlarge']
const MAX_HOURS      = [1, 2, 4, 8, 12, 24]

const WORDS = [
    'alpha','bravo','charlie','delta','echo','foxtrot','golf','hotel',
    'india','juliet','kilo','lima','mike','nova','oscar','papa',
    'quebec','romeo','sierra','tango','uniform','victor','whiskey','xray',
    'yankee','zulu','amber','birch','cedar','drift','ember','frost',
    'grove','haven','iris','jade','kite','lunar','maple','north',
    'orbit','pine','quartz','river','solar','terra','ultra','vega',
    'wave','xenon','yield','zenith',
]

function _randomName(typeId) {
    const word = WORDS[Math.floor(Math.random() * WORDS.length)]
    const num  = String(Math.floor(Math.random() * 9000) + 1000)
    return `${typeId}-${word}-${num}`
}

class SgComputeLaunchForm extends SgComponent {

    static jsUrl = import.meta.url
    get resourceName()   { return 'sg-compute-launch-form' }
    get sharedCssPaths() { return ['https://dev.tools.sgraph.ai/components/tokens/v1/v1.0/v1.0.0/sg-tokens.css'] }

    onReady() {
        this._nameInput     = this.$('.field-name')
        this._regionSel     = this.$('.field-region')
        this._instanceSel   = this.$('.field-instance')
        this._hoursSel      = this.$('.field-hours')
        this._advToggle     = this.$('.adv-toggle')
        this._advBody       = this.$('.adv-body')
        this._openCheckbox  = this.$('.field-open')

        this._populateSelect(this._regionSel,   REGIONS,        r => r)
        this._populateSelect(this._instanceSel, INSTANCE_TYPES, t => t)
        this._populateSelect(this._hoursSel,    MAX_HOURS,      h => `${h} hour${h > 1 ? 's' : ''}`)

        this._advToggle?.addEventListener('click', () => {
            const open = this._advBody?.hidden === false
            if (this._advBody) this._advBody.hidden = open
            if (this._advToggle) this._advToggle.textContent = open ? '▶ Advanced' : '▼ Advanced'
        })

        if (this._pendingPopulate) {
            const { entry, defaults } = this._pendingPopulate
            this._pendingPopulate = null
            this.populate(entry, defaults)
        }
    }

    populate(entry, defaults = {}) {
        if (!this._nameInput) { this._pendingPopulate = { entry, defaults }; return }
        const region   = defaults.region        || entry?.default_region        || REGIONS[0]
        const instType = defaults.instance_type || entry?.default_instance_type || 't3.medium'
        const hours    = defaults.max_hours     || entry?.default_max_hours     || 4

        if (this._regionSel)   this._regionSel.value   = region
        if (this._instanceSel) this._instanceSel.value = instType
        if (this._hoursSel)    this._hoursSel.value     = String(hours)
        if (this._nameInput)   this._nameInput.value    = entry?.type_id ? _randomName(entry.type_id) : ''
    }

    getValues() {
        return {
            stack_name:    this._nameInput?.value.trim()  || null,
            region:        this._regionSel?.value         || REGIONS[0],
            instance_type: this._instanceSel?.value       || 't3.medium',
            max_hours:     parseInt(this._hoursSel?.value || '4', 10),
            public_ingress: this._openCheckbox?.checked   ?? false,
        }
    }

    reset() {
        if (this._nameInput)   this._nameInput.value   = ''
        if (this._regionSel)   this._regionSel.value   = REGIONS[0]
        if (this._instanceSel) this._instanceSel.value = 't3.medium'
        if (this._hoursSel)    this._hoursSel.value    = '4'
        if (this._openCheckbox) this._openCheckbox.checked = false
    }

    setDisabled(disabled) {
        [this._nameInput, this._regionSel, this._instanceSel, this._hoursSel, this._openCheckbox]
            .forEach(el => { if (el) el.disabled = disabled })
    }

    _populateSelect(sel, items, labelFn) {
        if (!sel) return
        sel.innerHTML = ''
        for (const item of items) {
            const opt = document.createElement('option')
            opt.value = String(item)
            opt.textContent = labelFn(item)
            sel.appendChild(opt)
        }
    }
}

customElements.define('sg-compute-launch-form', SgComputeLaunchForm)
