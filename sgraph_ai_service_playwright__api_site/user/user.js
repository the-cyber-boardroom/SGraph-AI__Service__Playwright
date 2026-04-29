// ── user.js — User Provisioning page controller ─────────────────────────── //
// Loads catalog once, refreshes user's non-STOPPED stacks every 15s.        //
// Handles sg-start-stack → opens create modal, sg-stop-stack, sg-auth-saved. //

import { apiClient  } from '../shared/api-client.js';
import { loadCatalog } from '../shared/catalog.js';

const TYPE_GRID    = () => document.getElementById('type-grid');
const ACTIVE_GRID  = () => document.getElementById('active-grid');
const CREATE_MODAL = () => document.getElementById('create-modal');

function toast(message, type = 'info') {
    document.dispatchEvent(new CustomEvent('sg-toast', { detail: { message, type } }));
}

function deletePathForStack(stack) {
    const t = (stack.type || '').toLowerCase();
    if (t.includes('docker'))  return `/docker/stack/${stack.name}`;
    if (t.includes('elastic')) return `/elastic/stack/${stack.name}`;
    return `/linux/stack/${stack.name}`;
}

async function refreshMyStacks() {
    try {
        const data   = await apiClient.get('/catalog/stacks');
        const all    = Array.isArray(data) ? data : (data.stacks || []);
        const active = all.filter(s => (s.status || '').toUpperCase() !== 'STOPPED');
        ACTIVE_GRID().stacks = active;
    } catch (err) {
        toast(`Failed to load your stacks: ${err.message}`, 'error');
    }
}

async function init() {
    try {
        const catalog = await loadCatalog();
        const types   = Array.isArray(catalog) ? catalog : (catalog.types || []);
        TYPE_GRID().catalog = types;
    } catch (err) {
        toast(`Failed to load catalog: ${err.message}`, 'error');
    }

    await refreshMyStacks();

    setInterval(refreshMyStacks, 15000);
}

document.addEventListener('DOMContentLoaded', () => {
    init();

    document.addEventListener('sg-start-stack', (e) => {
        const modal = CREATE_MODAL();
        modal.setAttribute('stack-type', e.detail.type);
        modal.openModal();
    });

    document.addEventListener('sg-stop-stack', async (e) => {
        const stack = e.detail;
        try {
            await apiClient.delete(deletePathForStack(stack));
            toast(`Stopped stack ${stack.name}`, 'success');
            await refreshMyStacks();
        } catch (err) {
            toast(`Failed to stop ${stack.name}: ${err.message}`, 'error');
        }
    });

    document.addEventListener('sg-auth-saved', async () => {
        await refreshMyStacks();
    });
});
