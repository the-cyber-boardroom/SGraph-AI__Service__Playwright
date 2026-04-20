// ── cookie.js — navigate to the service's built-in cookie-form endpoint ─────
//
// The auth cookie must be set on the SERVICE's origin (http://ip:port),
// not on this page's origin.  The service ships /auth/set-cookie-form which
// renders an HTML form that POSTs to /auth/set-auth-cookie and sets the
// cookie on the correct origin.  We just redirect the browser there with
// the key name/value pre-filled via query-string so the user only has to
// click "Set cookie" once on that page.

function openCookieForm(cfg) {
  if (!cfg.ip) {
    showMsg('Enter the IP / host first.', true);
    return;
  }
  const url = new URL(`${baseUrl(cfg)}/auth/set-cookie-form`);
  if (cfg.keyName)  url.searchParams.set('key_name',  cfg.keyName);
  if (cfg.keyValue) url.searchParams.set('key_value', cfg.keyValue);
  window.open(url.toString(), '_blank');
}
