"""Case-screen browser checks: 28 pages at phone, tablet and desktop widths.

Run with Playwright and local Chrome on Floris test. No screenshot from mac.home.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
PAGES = sorted(ROOT.glob("AD??_*.html"))
assert len(PAGES) == 28

SCREENSHOT_PREFIXES = (
    "AD02_", "AD05_", "AD09_", "AD12_", "AD16_", "AD23_", "AD27_"
)
BROWSER_SIZES = ((390, 844), (768, 1024), (1440, 900))

checks = 0
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        headless=True,
        args=["--no-sandbox"],
    )
    try:
        for filename in PAGES:
            for width, height in BROWSER_SIZES:
                page = browser.new_page(
                    viewport={"width": width, "height": height},
                    locale="nl-NL",
                )
                errors = []
                page.on("pageerror", lambda exc: errors.append(str(exc)))
                page.goto(filename.resolve().as_uri(), wait_until="load")
                state = page.evaluate("""() => {
                    const tables = [...document.querySelectorAll('.screen-table-wrap, .invoice-lines-wrap')];
                    const controls = [...document.querySelectorAll('input, select, textarea, button')];
                    const h1 = document.querySelector('h1');
                    const scrollable = tables.filter(el => el.scrollWidth > el.clientWidth + 1);
                    const titleStyle = h1 ? getComputedStyle(h1) : null;
                    return {
                        width: innerWidth,
                        overflow: document.documentElement.scrollWidth > innerWidth + 1,
                        noControlsEnabled: controls.every(el => el.disabled),
                        cssLoaded: [...document.styleSheets].some(s => s.href?.includes('wireframes.css')),
                        main: !!document.querySelector('main'),
                        h1: !!h1?.textContent.trim(),
                        titleVisible: titleStyle?.visibility !== 'hidden' && titleStyle?.display !== 'none',
                        caseSources: document.querySelectorAll('a[href*="brightspace"]').length,
                        scenarios: document.querySelectorAll('.scenario').length,
                        resultTables: document.querySelectorAll('table').length,
                        scrollableTablesAccessible: scrollable.every(el => el.tabIndex >= 0),
                        mobileScrollHint: getComputedStyle(document.querySelector('.table-scroll-hint')).display !== 'none',
                        stateCount: document.querySelectorAll('.state-card').length,
                        narrowestStateLabel: Math.min(...[...document.querySelectorAll('.state-values dt')].map(el => el.getBoundingClientRect().width)),
                    };
                }""")
                assert not state["overflow"], (filename.name, width, state)
                assert state["noControlsEnabled"], (filename.name, width, "Active control")
                assert state["cssLoaded"] and state["main"] and state["h1"] and state["titleVisible"], (filename.name, width, state)
                assert state["caseSources"] > 0 and state["scenarios"] > 0 and state["resultTables"] > 0, (filename.name, width, state)
                assert state["scrollableTablesAccessible"], (filename.name, width, "Table not keyboard-scrollable")
                if width == 390:
                    assert state["mobileScrollHint"], (filename.name, width, "Mobile table hint missing")
                    if state["stateCount"]:
                        assert state["narrowestStateLabel"] >= 150, (filename.name, width, "State labels are squeezed", state)
                assert not errors, (filename.name, width, errors)
                if filename.stem.startswith(SCREENSHOT_PREFIXES) and width in (390, 1440):
                    page.screenshot(
                        path=str(ROOT / "previews" / f"{filename.stem}_{width}.png"),
                        full_page=True,
                    )
                checks += 1
                page.close()
    finally:
        browser.close()
print(
    f"PASS: {checks} Chrome viewport checks (28 x 390/768/1440 px): "
    "no document overflow, stylesheet and casuslinks loaded, all actions disabled, "
    "accessible table scroll, no browser errors"
)
