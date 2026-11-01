"""Optional browser acceptance test for the real Timaflu Flask screens.

Requires a disposable localhost MySQL fixture created by audit_ui_queries.py,
Google Chrome and separately installed Playwright for the test runner.
The frontend itself remains HTML/CSS without JavaScript or frontend libraries.
Never connects to production or modifies an actual customer account.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from threading import Thread
import logging
import os
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "code/backend"))
sys.path.insert(0, str(ROOT / "code/database"))

from app import create_app
from audit_ui_queries import SCREENS


def check(rounds: int, channel: str):
    if (os.getenv("TIMAFLU_TEST_ALLOW_RESET") != "isolated"
            or os.getenv("TIMAFLU_TEST_MYSQL_HOST") != "127.0.0.1"):
        raise RuntimeError("Only the disposable local MySQL test is permitted.")

    from playwright.sync_api import sync_playwright
    from werkzeug.serving import make_server

    app = create_app()
    app.config.update(
        TESTING=True, SECRET_KEY="only-disposable-local-testing",
        DB_HOST="127.0.0.1",
        DB_PORT=int(os.environ["TIMAFLU_TEST_MYSQL_PORT"]),
        DB_NAME="timaflu_casus_test_94",
        DB_USER=os.environ.get("TIMAFLU_TEST_MYSQL_USER", "root"),
        DB_PASSWORD=os.environ["TIMAFLU_TEST_MYSQL_PASSWORD"],
        TIMAFLU_ADDRESS="TESTGEGEVENS: Fictieve Afzenderstraat 9, Breda",
    )
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    server = make_server("127.0.0.1", 0, app, threaded=True)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    failures = []
    checked = 0
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel=channel, headless=True)
            try:
                for round_number in range(1, rounds + 1):
                    for width in (390, 768, 1440):
                        context = browser.new_context(
                            viewport={"width": width, "height": 900}
                        )
                        try:
                            page = context.new_page()
                            def static_response(response):
                                if (response.status >= 400 and
                                        f":{server.server_port}/static/" in response.url):
                                    failures.append((round_number, width,
                                                     response.url, response.status))
                            page.on("response", static_response)
                            for url, _heading in SCREENS:
                                response = page.goto(
                                    f"http://127.0.0.1:{server.server_port}{url}",
                                    wait_until="load", timeout=10000,
                                )
                                dimensions = page.evaluate("""() => ({
                                  width: window.innerWidth,
                                  documentWidth: document.documentElement.scrollWidth,
                                  scriptCount: document.querySelectorAll('script').length,
                                })""")
                                checked += 1
                                if (response.status != 200
                                        or dimensions["scriptCount"] != 0
                                        or dimensions["documentWidth"] >
                                           dimensions["width"] + 2):
                                    failures.append((round_number, width, url,
                                                     response.status, dimensions))
                        finally:
                            context.close()
                    print(f"Chrome round {round_number}/{rounds}: passed all "
                          f"{len(SCREENS)} screen URLs at 3 viewport widths "
                          if not failures else f"Chrome round {round_number}: issues",
                          flush=True)
            finally:
                browser.close()
    finally:
        server.shutdown()
        worker.join(timeout=5)

    if failures:
        for failure in failures[:25]:
            print("FAILED", failure)
        raise SystemExit(f"Failed {len(failures)} checks of {checked} visits")
    print(f"PASS: {checked} actual Flask/Chrome screen checks, "
          "all assets available, no scripts and no horizontal overflow")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--channel", default="chrome")
    arguments = parser.parse_args()
    if arguments.rounds < 1 or arguments.rounds > 10:
        raise SystemExit("Choose between 1 and 10 repeat rounds")
    check(arguments.rounds, arguments.channel)
