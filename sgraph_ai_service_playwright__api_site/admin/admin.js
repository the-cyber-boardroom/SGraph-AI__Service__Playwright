// ── admin.js — Admin Dashboard page controller ──────────────────────────── //
// Loads catalog once, refreshes active stacks on load + every 30s.          //
// Handles sg-stop-stack, sg-auth-saved.                                     //

import { apiClient  } from '../shared/api-client.js';
import { loadCatalog } from '../shared/catalog.js';

const TYPE_GRID   = () => document.getElementById('type-grid');
const ACTIVE_GRID = () => document.getElementById('active-grid');

function toast(message, type = 'info') {
    document.dispatchEvent(new CustomEvent('sg-toast', { detail: { message, type } }));
}

function deletePathForStack(stack) {
    const t = (stack.type || '').toLowerCase();
    if (t.includes('docker'))  return `/docker/stack/${stack.name}`;
    if (t.includes('elastic')) return `/elastic/stack/${stack.name}`;
    return `/linux/stack/${stack.name}`;               // fallback to linux
}

async function refreshActiveStacks() {
    try {
        const data = await apiClient.get('/catalog/stacks');
        const stacks = Array.isArray(data) ? data : (data.stacks || []);
        ACTIVE_GRID().stacks = stacks;
    } catch (err) {
        toast(`Failed to load active stacks: ${err.message}`, 'error');
    }
}

async function init() {
    try {
        const catalog = await loadCatalog();
        TYPE_GRID().catalog = catalog.entries || [];
    } catch (err) {
        toast(`Failed to load catalog: ${err.message}`, 'error');
    }

    await refreshActiveStacks();

    setInterval(refreshActiveStacks, 30000);
}

document.addEventListener('DOMContentLoaded', () => {
    init();

    document.addEventListener('sg-stop-stack', async (e) => {
        const stack = e.detail;
        try {
            await apiClient.delete(deletePathForStack(stack));
            toast(`Stopped stack ${stack.name}`, 'success');
            await refreshActiveStacks();
        } catch (err) {
            toast(`Failed to stop ${stack.name}: ${err.message}`, 'error');
        }
    });

    document.addEventListener('sg-auth-saved', async () => {
        try {
            const catalog = await loadCatalog();
            TYPE_GRID().catalog = catalog.entries || [];
        } catch (err) {
            toast(`Failed to reload catalog: ${err.message}`, 'error');
        }
        await refreshActiveStacks();
    });
});
