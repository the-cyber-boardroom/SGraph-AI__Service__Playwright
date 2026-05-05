// Single source of truth for node-state vocabulary.
// Mirrors Enum__Node__State on the backend.

export const NODE_STATE = {
    BOOTING:     'BOOTING',
    READY:       'READY',
    TERMINATING: 'TERMINATING',
    TERMINATED:  'TERMINATED',
    FAILED:      'FAILED',
}

// Tolerant of legacy values during transition window.
export function isRunning(state) {
    return state === NODE_STATE.READY || state === 'ready' || state === 'running'
}

// Returns CSS class — 'state-ready', 'state-booting', 'state-failed', etc.
export function stateClass(state) {
    const norm = (state || 'unknown').toLowerCase()
    if (norm === 'running') return 'state-ready'   // legacy alias
    return `state-${norm}`
}

// Returns operator-friendly label — 'Ready', 'Booting', etc.
export function stateLabel(state) {
    const norm = (state || 'unknown').toLowerCase()
    if (norm === 'running') return 'Ready'          // legacy alias
    return norm.replace(/^./, c => c.toUpperCase())
}

// Maps a node state to the good/bad/warn dot-pill colour class used by ec2-tokens.css.
export function nodePillClass(state) {
    if (isRunning(state)) return 'good'
    const lower = (state || '').toLowerCase()
    if (lower === 'stopped' || lower === 'terminated' || lower === 'failed') return 'bad'
    return 'warn'
}

// Maps a Docker/Podman container status to a dot-pill colour class.
// Container status vocabulary is distinct from node state — 'running' here is Docker's own term.
export function podPillClass(status) {
    const s = (status || '').toLowerCase()
    if (s === 'running')                return 'good'
    if (s === 'exited' || s === 'dead') return 'bad'
    return 'warn'
}
