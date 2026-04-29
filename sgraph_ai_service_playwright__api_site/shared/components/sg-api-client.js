// ── sg-api-client — no-render connector component ───────────────────────── //
// Bridges sg-auth-required events to the sg-auth-panel via sg-show-auth.    //

class SgApiClient extends HTMLElement {
    connectedCallback() {
        document.addEventListener('sg-auth-required', () => {
            document.dispatchEvent(new CustomEvent('sg-show-auth', { bubbles: true }));
        });
    }
}

customElements.define('sg-api-client', SgApiClient);
