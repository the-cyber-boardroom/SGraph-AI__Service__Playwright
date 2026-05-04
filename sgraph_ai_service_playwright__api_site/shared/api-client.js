// ── ApiClient — module-level singleton for all HTTP calls ────────────────── //
// Reads/writes apiUrl and apiKey from localStorage.                           //
// On 401, dispatches sg-auth-required so the auth panel can intercept.       //

const STORAGE_KEY_URL = 'sg_api_url';
const STORAGE_KEY_KEY = 'sg_api_key';

class ApiClient {
    constructor() {
        this.apiUrl = localStorage.getItem(STORAGE_KEY_URL) || window.location.origin;
        this.apiKey = localStorage.getItem(STORAGE_KEY_KEY) || '';
    }

    save(url, key) {
        this.apiUrl = url;
        this.apiKey = key;
        localStorage.setItem(STORAGE_KEY_URL, url);
        localStorage.setItem(STORAGE_KEY_KEY, key);
    }

    async request(method, path, body) {
        const url     = this.apiUrl.replace(/\/$/, '') + path;
        const headers = { 'Content-Type': 'application/json' };
        if (this.apiKey) {
            headers['X-API-Key'] = this.apiKey;
        }
        const init = { method, headers };
        if (body !== undefined) {
            init.body = JSON.stringify(body);
        }
        const response = await fetch(url, init);
        if (response.status === 401) {
            document.dispatchEvent(new CustomEvent('sg-auth-required', { bubbles: true }));
            throw new Error('Unauthenticated — API key required');
        }
        if (!response.ok) {
            const text = await response.text();
            throw new Error(`HTTP ${response.status}: ${text}`);
        }
        return response.json();
    }

    async get(path)         { return this.request('GET',    path);        }
    async post(path, body)  { return this.request('POST',   path, body);  }
    async delete(path)      { return this.request('DELETE', path);        }
}

export const apiClient = new ApiClient();
