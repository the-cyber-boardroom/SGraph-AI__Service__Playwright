# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Routes__Test_Pages (console iteration-2, item 5)
#
#   GET /test-pages/{name}  → deterministic, self-contained HTML fixture pages
#                             served BY this service, same-origin reachable.
#
# Decision #5 (operator): the self-contained console examples (the S-series in the
# GET / console) target these pages instead of public sites, so they are
# reproducible and run against the service's own server-side browser without any
# external network egress. Each page is STATIC + DETERMINISTIC: stable element ids
# and a fixed render so an automated workflow can assert against them.
#
# Auth: each concrete /test-pages/{name} path is appended to AUTH__EXCLUDED_PATHS in
# Fast_API__Playwright__Service.setup() (the same mechanism that excludes
# /auth/set-cookie-form), so the server-side browser can fetch them without an API
# key. The middleware matches request.url.path exactly, so the names are enumerated
# (TEST_PAGE_NAMES) rather than relying on a path-prefix match.
#
# Pure delegation — no business logic, no page.* calls, no service injection. This
# class only maps the URL to a static HTML string (Routes__Index HTMLResponse
# pattern).
# ═══════════════════════════════════════════════════════════════════════════════

import html

from fastapi                                                                        import Request
from fastapi.responses                                                              import HTMLResponse
from osbot_fast_api.api.decorators.route_path                                       import route_path
from osbot_fast_api.api.routes.Fast_API__Routes                                     import Fast_API__Routes
from osbot_fast_api.api.schemas.safe_str.Safe_Str__Fast_API__Route__Prefix          import Safe_Str__Fast_API__Route__Prefix


# ── Fixture names — single source of truth for both the route and the auth-exclude list ──
TEST_PAGE_NAMES        = ['simple', 'form', 'dynamic', 'links', 'slow']
ROUTES_PATHS__TEST_PAGES = [f'/test-pages/{name}' for name in TEST_PAGE_NAMES]


# ── simple: static heading + paragraphs (screenshot / inspect target) ──
TEST_PAGE__SIMPLE = r'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Simple Test Page</title>
<style>body{font-family:system-ui,sans-serif;max-width:720px;margin:40px auto;padding:0 16px;color:#222;}
h1{color:#1a56db;}</style></head>
<body>
  <h1 id="title">Simple Test Page</h1>
  <p id="intro">This is a deterministic fixture served by the SG Playwright Service.</p>
  <p id="body-1">Paragraph one — stable text for selector capture and screenshot diffing.</p>
  <p id="body-2">Paragraph two — no scripts, no external requests, renders instantly.</p>
  <footer id="footer">sg-playwright /test-pages/simple</footer>
</body></html>'''


# ── form: login form with STABLE ids/names; #result appears after submit ──
TEST_PAGE__FORM = r'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Form Test Page</title>
<style>body{font-family:system-ui,sans-serif;max-width:480px;margin:40px auto;padding:0 16px;color:#222;}
label{display:block;margin:10px 0 4px;font-size:.9rem;}input{width:100%;padding:8px;box-sizing:border-box;}
button{margin-top:14px;padding:8px 18px;}#result{margin-top:18px;}</style></head>
<body>
  <h1 id="title">Login</h1>
  <form id="login-form" onsubmit="return submitForm(event)">
    <label for="username">Username</label>
    <input id="username" name="username" type="text" autocomplete="off">
    <label for="password">Password</label>
    <input id="password" name="password" type="password" autocomplete="off">
    <button id="submit" type="submit">Sign in</button>
  </form>
  <div id="result"></div>
  <script>
    // Deterministic: on submit, inject a stable #result node (no network).
    function submitForm(e){
      e.preventDefault();
      var u = document.getElementById('username').value;
      var r = document.getElementById('result');
      r.innerHTML = '<p id="welcome">Welcome, ' + (u ? u.replace(/[<>&]/g,'') : 'guest') + '!</p>';
      return false;
    }
  </script>
</body></html>'''


# ── dynamic: JS injects #ready after ~1s (wait_for selector target) ──
TEST_PAGE__DYNAMIC = r'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Dynamic Test Page</title>
<style>body{font-family:system-ui,sans-serif;max-width:600px;margin:40px auto;padding:0 16px;color:#222;}
#ready{color:#0a7d2c;font-weight:600;}</style></head>
<body>
  <h1 id="title">Dynamic Test Page</h1>
  <p id="status">Loading… a #ready node appears after ~1 second.</p>
  <div id="late"></div>
  <script>
    // Deterministic delay so wait_for(selector:'#ready') has something to wait on.
    setTimeout(function(){
      var d = document.getElementById('late');
      d.innerHTML = '<p id="ready">Ready! The deferred content has loaded.</p>';
    }, 1000);
  </script>
</body></html>'''


# ── links: several anchored sections (navigate/scroll/selector capture target) ──
TEST_PAGE__LINKS = r'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Links Test Page</title>
<style>body{font-family:system-ui,sans-serif;max-width:720px;margin:0 auto;padding:0 16px;color:#222;}
nav{position:sticky;top:0;background:#fff;padding:12px 0;border-bottom:1px solid #ddd;}
nav a{margin-right:14px;}section{min-height:90vh;padding-top:20px;}
h2{color:#1a56db;}</style></head>
<body>
  <nav id="nav">
    <a id="link-alpha" href="#alpha">Alpha</a>
    <a id="link-beta" href="#beta">Beta</a>
    <a id="link-gamma" href="#gamma">Gamma</a>
  </nav>
  <section id="alpha"><h2 id="h-alpha">Alpha section</h2><p>Top anchored section.</p></section>
  <section id="beta"><h2 id="h-beta">Beta section</h2><p>Middle anchored section — scroll target.</p></section>
  <section id="gamma"><h2 id="h-gamma">Gamma section</h2><p id="bottom">Bottom anchored section.</p></section>
</body></html>'''


# ── slow: renders its visible content after a short delay ──
TEST_PAGE__SLOW = r'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Slow Test Page</title>
<style>body{font-family:system-ui,sans-serif;max-width:600px;margin:40px auto;padding:0 16px;color:#222;}
#content{color:#444;}</style></head>
<body>
  <h1 id="title">Slow Test Page</h1>
  <div id="content"></div>
  <script>
    // Visible content arrives after a short delay (settle / wait target).
    setTimeout(function(){
      document.getElementById('content').innerHTML =
        '<p id="loaded">Content rendered after a short delay.</p>';
    }, 600);
  </script>
</body></html>'''


TEST_PAGES = {'simple' : TEST_PAGE__SIMPLE ,
              'form'    : TEST_PAGE__FORM   ,
              'dynamic' : TEST_PAGE__DYNAMIC,
              'links'   : TEST_PAGE__LINKS  ,
              'slow'    : TEST_PAGE__SLOW   }


class Routes__Test_Pages(Fast_API__Routes):
    tag : str = 'test-pages'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prefix = Safe_Str__Fast_API__Route__Prefix('/')                        # Mount at root so @route_path gives the full /test-pages/{name} path

    @route_path('/test-pages/{name}')
    def page(self, name: str, request: Request) -> HTMLResponse:                    # Pure delegation: name → static fixture HTML
        page_html = TEST_PAGES.get(name)
        if page_html is None:
            safe_name = html.escape(name)                                           # Reflected name is escaped — never interpolate raw request input into HTML
            return HTMLResponse(content=f'<!DOCTYPE html><html><body><h1 id="not-found">Unknown test page: {safe_name}</h1></body></html>', status_code=404)
        return HTMLResponse(content=page_html)

    def setup_routes(self):
        self.add_route_get(self.page)
