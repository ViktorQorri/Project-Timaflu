"""Browser and data-coverage acceptance test for the Timaflu HTML/CSS frontend.

Requires a disposable local MySQL 8.4 instance prepared with
audit_ui_queries.py and an optional separately installed Playwright test runner.
It does not add JavaScript or a frontend library to Timaflu.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
import logging
import os
from pathlib import Path
from threading import Thread
import sys
from unittest.mock import patch
from urllib.parse import urlsplit

from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code/database"))
sys.path.insert(0, str(ROOT / "code/backend"))
from app import create_app
from audit_ui_queries import SCREENS


def check() -> None:
    if (os.getenv("TIMAFLU_TEST_ALLOW_RESET") != "isolated"
            or os.getenv("TIMAFLU_TEST_MYSQL_HOST") != "127.0.0.1"):
        raise SystemExit("Run only against the disposable localhost MySQL fixture.")
    from playwright.sync_api import sync_playwright

    app = create_app()
    app.config.update(
        TESTING=True,
        SECRET_KEY="temporary-local-browser-acceptance",
        DB_HOST="127.0.0.1",
        DB_PORT=int(os.environ["TIMAFLU_TEST_MYSQL_PORT"]),
        DB_NAME="timaflu_casus_test_94",
        DB_USER=os.getenv("TIMAFLU_TEST_MYSQL_USER", "root"),
        DB_PASSWORD=os.environ["TIMAFLU_TEST_MYSQL_PASSWORD"],
        TIMAFLU_ADDRESS="TESTGEGEVENS: fictief afzenderadres",
    )
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    server = make_server("127.0.0.1", 0, app, threaded=True)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    problems = []
    warnings = []
    checked = 0
    widths = (360, 390, 768, 1440)
    stats = {}
    try:
        with sync_playwright() as playwright:
            channel = os.getenv("TIMAFLU_BROWSER_CHANNEL", "chrome")
            browser = playwright.chromium.launch(channel=channel, headless=True)
            try:
                for width in widths:
                    context = browser.new_context(
                        viewport={"width": width, "height": 900}
                    )
                    # Only external fonts are skipped. All local stylesheets
                    # are loaded and checked against the running Flask server.
                    def route_external(route):
                        hostname = urlsplit(route.request.url).hostname
                        if hostname in ("127.0.0.1", "localhost"):
                            route.continue_()
                        else:
                            route.abort()
                    context.route("**/*", route_external)
                    page = context.new_page()
                    assets = []
                    page.on(
                        "response",
                        lambda response: assets.append((response.status,response.url))
                        if (urlsplit(response.url).hostname == "127.0.0.1"
                            and response.status >= 400)
                        else None,
                    )
                    for url, label in SCREENS:
                        asset_before = len(assets)
                        try:
                            # The invoice in the isolated fixture dates from 31 Oct;
                            # a first reminder can only be shown 7-13 days later.
                            # Preserve the actual production due-date rule.
                            if url == "/invoices/1/reminders/1":
                                with patch("routes.administration.date") as clock:
                                    clock.today.return_value = date(2026, 11, 8)
                                    response = page.goto(origin + url, wait_until="load")
                            else:
                                response = page.goto(origin + url, wait_until="load")
                            result = page.evaluate("""() => {
                                const doc=document.documentElement;
                                const visible = e => e && getComputedStyle(e).display !== 'none'
                                  && getComputedStyle(e).visibility !== 'hidden';
                                const ids=[...document.querySelectorAll('[id]')]
                                  .map(e=>e.id).filter(Boolean);
                                const scripts=document.querySelectorAll('script').length;
                                const inlineHandlers=[...document.querySelectorAll('*')]
                                  .filter(e=>[...e.attributes].some(a=>/^on[a-z]+$/i.test(a.name)
                                    || a.value.toLowerCase().startsWith('javascript:'))).length;
                                const localCSS=[...document.querySelectorAll('link[rel=stylesheet]')]
                                  .filter(e=>e.href.includes('/static/')).length;
                                const loadedCSS=[...document.styleSheets]
                                  .filter(e=>e.href&&e.href.includes('/static/')).length;
                                const forms=[...document.querySelectorAll('form')].map(f=>({
                                  action:new URL(f.getAttribute('action')||location.pathname,location.href).href,
                                  method:f.method
                                }));
                                return {
                                  viewport:innerWidth,docwidth:doc.scrollWidth,
                                  scripts,inlineHandlers,localCSS,loadedCSS,forms,
                                  lang:doc.lang,viewportMeta:!!document.querySelector('meta[name=viewport]'),
                                  headings:document.querySelectorAll('h1').length,
                                  mains:document.querySelectorAll('main').length,
                                  duplicateIds:[...new Set(ids.filter((id,i)=>ids.indexOf(id)!==i))],
                                  mobileNav:visible(document.querySelector('details.mobile-navigation summary')),
                                  pickingTables:[...document.querySelectorAll('.picking-bins__table')]
                                    .map(e=>({display:getComputedStyle(e).display,
                                      rows:e.querySelectorAll('tbody tr').length})),
                                  scheduleTables:[...document.querySelectorAll('.delivery-page__schedule table')]
                                    .map(e=>({display:getComputedStyle(e).display,
                                      rows:e.querySelectorAll('tbody tr').length})),
                                  pickingBins:document.querySelectorAll(
                                    '.picking-bins__table tbody tr').length,
                                  firstForms:document.querySelectorAll(
                                    'form[action$="/deliveries/first-attempt"]').length,
                                  secondForms:document.querySelectorAll(
                                    'form[action$="/deliveries/second-attempt"]').length,
                                  orderPickingButtons:document.querySelectorAll(
                                    'form[action*="/order-picking/orders/"] button').length,
                                };
                            }""")
                            checked += 1
                            if response.status != 200:
                                problems.append((width,url,"HTTP",response.status))
                            if result["docwidth"] > width + 2:
                                problems.append((width,url,"document overflow",
                                                 result["docwidth"]))
                            if result["scripts"] or result["inlineHandlers"]:
                                problems.append((width,url,"JavaScript in page"))
                            if result["localCSS"] < 3 or result["loadedCSS"] < 3:
                                problems.append((width,url,"missing local CSS"))
                            if result["lang"] != "nl" or not result["viewportMeta"] or result["mains"] != 1:
                                problems.append((width,url,"document semantics"))
                            if result["headings"] != 1:
                                problems.append((width,url,"h1 count",
                                                 result["headings"]))
                            if result["duplicateIds"]:
                                warnings.append((width,url,"duplicate ids",result["duplicateIds"]))
                            for form in result["forms"]:
                                try:
                                    from werkzeug.routing import RequestRedirect
                                    target = urlsplit(form["action"])
                                    adapter=app.url_map.bind("localhost")
                                    adapter.match(target.path,method=form["method"].upper())
                                except RequestRedirect:
                                    pass
                                except Exception:
                                    problems.append((width,url,"broken form action",
                                                     form["method"],target.path))
                            if url == "/order-picking":
                                stats[(width,"picking")] = result
                                if result["orderPickingButtons"] == 0:
                                    problems.append((width,url,"no executable picking action in fixture"))
                                if result["pickingBins"] < 3:
                                    problems.append((width,url,"too few scanned bins in fixture"))
                                if len(result["pickingTables"]) != 2:
                                    problems.append((width,url,"missing picking tables"))
                                if width <= 720 and any(row["display"]!="block"
                                                        for row in result["pickingTables"]):
                                    problems.append((width,url,"picking cards not responsive"))
                            if url == "/deliveries?day=2026-10-22":
                                stats[(width,"delivery")] = result
                                if not result["firstForms"] or not result["secondForms"]:
                                    problems.append((width,url,"missing delivery-attempt actions"))
                                if not result["scheduleTables"] or result["scheduleTables"][0]["rows"] < 3:
                                    problems.append((width,url,"not enough delivery schedule data"))
                                if width <= 720 and any(row["display"]!="block"
                                                        for row in result["scheduleTables"]):
                                    problems.append((width,url,"delivery cards not responsive"))
                            if len(assets) > asset_before:
                                problems.append((width,url,"missing local assets",
                                                 assets[asset_before:]))
                        except Exception as exc:
                            problems.append((width,url,"browser exception",str(exc)))
                    if width <= 720:
                        page.goto(origin + "/",wait_until="load")
                        nav=page.locator("details.mobile-navigation")
                        summary=nav.locator("summary")
                        if not summary.is_visible():
                            problems.append((width,"/","mobile menu not visible"))
                        else:
                            summary.click()
                            if not nav.evaluate("(el)=>el.open") or not nav.locator("a").first.is_visible():
                                problems.append((width,"/","mobile navigation not usable"))
                    else:
                        page.goto(origin+"/",wait_until="load")
                        if not page.locator("nav.desktop-navigation").is_visible():
                            problems.append((width,"/","desktop menu not visible"))
                    context.close()
                    print(f"Viewport {width}: {len(SCREENS)} screens checked",flush=True)
                    if width == widths[-1]:
                        print(f"Immediate result: {checked} page checks; {len(problems)} failures; {len(warnings)} warnings",flush=True)
                        for issue in problems[:35]:
                            print("FAILED:",issue,flush=True)
                        for warning in warnings[:12]:
                            print("WARNING:",warning,flush=True)
            finally:
                browser.close()
    finally:
        stopper = Thread(target=server.shutdown, daemon=True)
        stopper.start()
        stopper.join(timeout=4)
        worker.join(timeout=4)
    print(f"Browser screens checked: {checked}; issues={len(problems)}; warnings={len(warnings)}")
    for key, result in stats.items():
        print(key, {k:result[k] for k in
                     ("docwidth","pickingTables","scheduleTables","firstForms",
                      "secondForms","orderPickingButtons","pickingBins")})
    for issue in problems[:30]:
        print("FAILED:",issue)
    for warning in warnings[:12]:
        print("WARNING:",warning)
    if problems:
        raise SystemExit(2)


if __name__ == "__main__":
    check()
