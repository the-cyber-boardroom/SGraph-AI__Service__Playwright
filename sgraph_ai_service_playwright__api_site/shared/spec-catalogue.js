// ── spec-catalogue.js — page-lifetime cache for /api/specs ──────────────── //
// Call loadCatalogue() once on page load; subsequent calls return cached.    //

import { apiClient } from './api-client.js'

let _cached = null

export async function loadCatalogue() {
    if (_cached) return _cached
    const response = await apiClient.get('/api/specs')
    _cached = response  // { specs: [Schema__Spec__Manifest__Entry, ...] }
    document.dispatchEvent(new CustomEvent('sp-cli:catalogue.loaded', {
        detail:  { specs: _cached.specs || [] },
        bubbles: true, composed: true,
    }))
    return _cached
}

export function getCatalogue() {
    if (!_cached) throw new Error('catalogue not loaded; call loadCatalogue() first')
    return _cached
}

export function getSpec(spec_id) {
    return (getCatalogue().specs || []).find(s => s.spec_id === spec_id)
}
