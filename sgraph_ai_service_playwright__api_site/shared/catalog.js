// ── catalog.js — page-lifetime cache for /catalog/types ─────────────────── //
// Call loadCatalog() once on page load. Subsequent calls return the cache.   //

import { apiClient } from './api-client.js';

let cache = null;

export async function loadCatalog(forceRefresh = false) {
    if (cache !== null && !forceRefresh) {
        return cache;
    }
    cache = await apiClient.get('/catalog/types');
    return cache;
}

export function getCatalog() {
    return cache;
}
