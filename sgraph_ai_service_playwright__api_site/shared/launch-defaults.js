// ── launch-defaults.js — canonical launch constants ────────────────────────── //
// Single source of truth. Both sg-compute-compute-view and sg-compute-launch-form
// import from here. Update here only — do not duplicate locally.

export const REGIONS = Object.freeze([
    'eu-west-2', 'us-east-1', 'ap-southeast-1', 'eu-west-1', 'us-west-2',
])

export const INSTANCE_TYPES = Object.freeze([
    't3.micro', 't3.small', 't3.medium', 't3.large', 't3.xlarge',
])

export const MAX_HOURS = Object.freeze([1, 2, 4, 8, 12, 24])

// Rough on-demand spot rates (USD/hr) — intentionally approximate
export const COST_TABLE = Object.freeze({
    't3.micro': 0.011, 't3.small': 0.023, 't3.medium': 0.047,
    't3.large': 0.094, 't3.xlarge': 0.188,
})
