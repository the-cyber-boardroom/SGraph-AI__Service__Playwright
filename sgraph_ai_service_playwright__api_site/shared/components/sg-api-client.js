// ── sg-api-client — no-render connector component ───────────────────────── //
// Bridges sg-auth-required events to the sg-auth-panel via sg-show-auth.    //
// Also auto-opens the panel on first load when no API URL is stored.        //

import { apiClient } from '../api-client.js';

class SgApiClient extends HTMLElement {
    connectedCallback() {
        document.addEventListener('sg-auth-required', () => {
            document.dispatchEvent(new CustomEvent('sg-show-auth', { bubbles: true }));
        });

        if (!apiClient.apiUrl) {                                                    // No URL configured yet — open the connection panel immediately
            requestAnimationFrame(() =>
                document.dispatchEvent(new CustomEvent('sg-show-auth', { bubbles: true }))
            );
        }
    }
}

customElements.define('sg-api-client', SgApiClient);
