import { SgComponent } from 'https://dev.tools.sgraph.ai/components/base/v1/v1.0/v1.0.0/sg-component.js'
import '/ui/components/sp-cli/_shared/sg-compute-ami-picker/v0/v0.1/v0.1.0/sg-compute-ami-picker.js'
import { REGIONS, INSTANCE_TYPES, MAX_HOURS } from '/ui/shared/launch-defaults.js'

const MODE_FRESH    = 'fresh'
const MODE_BAKE_AMI = 'bake-ami'
const MODE_FROM_AMI = 'from-ami'

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
        this._formRoot      = this.$('.launch-form')
        this._nameInput     = this.$('.field-name')
        this._regionSel     = this.$('.field-region')
        this._instanceSel   = this.$('.field-instance')
        this._hoursSel      = this.$('.field-hours')
        this._advToggle     = this.$('.adv-toggle')
        this._advBody       = this.$('.adv-body')
        this._openCheckbox  = this.$('.field-open')
        this._amiPicker     = this.$('.field-ami-picker')
        this._amiNameInput  = this.$('.field-ami-name')
        this._amiError      = this.$('.ami-required-error')
        this._callerIpInput = this.$('.field-caller-ip')
        this._modeInputs    = this.$$('.field-mode')

        this._currentMode   = MODE_FRESH
        this._specId        = null

        this._seedCallerIp()

        this._populateSelect(this._regionSel,   REGIONS,        r => r)
        this._populateSelect(this._instanceSel, INSTANCE_TYPES, t => t)
        this._populateSelect(this._hoursSel,    MAX_HOURS,      h => `${h} hour${h > 1 ? 's' : ''}`)

        this._modeInputs?.forEach(radio => {
            radio.addEventListener('change', () => {
                if (radio.checked) this._setMode(radio.value)
            })
        })

        this._advToggle?.addEventListener('click', () => {
            const open = this._advBody?.hidden === false
            if (this._advBody)  this._advBody.hidden     = open
            if (this._advToggle) {
                this._advToggle.textContent  = open ? '▶ Advanced' : '▼ Advanced'
                this._advToggle.setAttribute('aria-expanded', String(!open))
            }
        })

        if (this._pendingPopulate) {
            const { entry, defaults } = this._pendingPopulate
            this._pendingPopulate = null
            this.populate(entry, defaults)
        }
    }

    _setMode(mode) {
        this._currentMode = mode
        if (!this._formRoot) return
        this._formRoot.classList.remove('mode-bake-ami', 'mode-from-ami')
        if (mode === MODE_BAKE_AMI) this._formRoot.classList.add('mode-bake-ami')
        if (mode === MODE_FROM_AMI) this._formRoot.classList.add('mode-from-ami')
        if (this._amiError) this._amiError.hidden = true
        if (this._amiPicker && this._specId) this._amiPicker.setSpecId(this._specId)
    }

    populate(entry, defaults = {}) {
        if (!this._nameInput) { this._pendingPopulate = { entry, defaults }; return }
        this._specId = entry?.spec_id || null

        const region   = defaults.region        || entry?.default_region        || REGIONS[0]
        const instType = defaults.instance_type || entry?.default_instance_type || 't3.medium'
        const hours    = defaults.max_hours     || entry?.default_max_hours     || 4

        if (this._regionSel)   this._regionSel.value   = region
        if (this._instanceSel) this._instanceSel.value = instType
        if (this._hoursSel)    this._hoursSel.value     = String(hours)
        if (this._nameInput)   this._nameInput.value    = entry?.type_id ? _randomName(entry.type_id) : ''

        this._resetMode()
        if (this._amiPicker && this._specId) this._amiPicker.setSpecId(this._specId)
    }

    getValues() {
        const amiId = this._amiPicker?.getSelectedAmiId?.() || ''
        return {
            node_name:      this._nameInput?.value.trim()     || null,
            region:         this._regionSel?.value            || REGIONS[0],
            instance_type:  this._instanceSel?.value          || 't3.medium',
            max_hours:      parseInt(this._hoursSel?.value || '4', 10),
            public_ingress: this._openCheckbox?.checked       ?? false,
            caller_ip:      this._callerIpInput?.value.trim() || '',
            creation_mode:  this._currentMode,
            ami_id:         amiId,
            ami_name:       this._amiNameInput?.value.trim()  || '',
        }
    }

    validate() {
        if (this._currentMode === MODE_FROM_AMI) {
            const amiId = this._amiPicker?.getSelectedAmiId?.() || ''
            if (!amiId) {
                if (this._amiError) this._amiError.hidden = false
                return false
            }
        }
        if (this._amiError) this._amiError.hidden = true
        return true
    }

    reset() {
        if (this._nameInput)   this._nameInput.value   = ''
        if (this._regionSel)   this._regionSel.value   = REGIONS[0]
        if (this._instanceSel) this._instanceSel.value = 't3.medium'
        if (this._hoursSel)    this._hoursSel.value    = '4'
        if (this._openCheckbox) this._openCheckbox.checked = false
        if (this._amiNameInput) this._amiNameInput.value = ''
        if (this._amiError)    this._amiError.hidden   = true
        this._resetMode()
        this._seedCallerIp()
    }

    _seedCallerIp() {
        if (!this._callerIpInput) return
        const host = window.location.hostname
        if (host === 'localhost' || host === '127.0.0.1' || host === '0.0.0.0') {
            this._callerIpInput.value = '127.0.0.1'
        }
        // On remote hosts: leave empty — user must enter their public IP.
        // Preferred fix: backend GET /catalog/caller-ip (see backend brief BV__caller-ip-endpoint.md).
    }

    setDisabled(disabled) {
        [this._nameInput, this._regionSel, this._instanceSel, this._hoursSel,
         this._openCheckbox, this._amiNameInput, this._callerIpInput].forEach(el => { if (el) el.disabled = disabled })
        this._modeInputs?.forEach(r => { r.disabled = disabled })
        this._amiPicker?.setDisabled?.(disabled)
    }

    _resetMode() {
        this._currentMode = MODE_FRESH
        if (this._formRoot) {
            this._formRoot.classList.remove('mode-bake-ami', 'mode-from-ami')
        }
        this._modeInputs?.forEach(r => { r.checked = (r.value === MODE_FRESH) })
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

    $$(selector) {
        return this.shadowRoot ? [...this.shadowRoot.querySelectorAll(selector)] : []
    }
}

customElements.define('sg-compute-launch-form', SgComputeLaunchForm)
