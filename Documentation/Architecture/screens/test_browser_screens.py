"""Headless Chrome checks: 28 designs x 3 responsive widths."""
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parent
pages = sorted(root.glob("AD??_*.html"))
assert len(pages) == 28
count = 0
with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        headless=True, args=["--no-sandbox"])
    try:
        for filename in pages:
            for width, height in [(390, 844), (768, 1024), (1440, 900)]:
                page = browser.new_page(viewport={"width": width, "height": height})
                page.goto(filename.resolve().as_uri())
                result = page.evaluate("""() => ({
                  overflow: document.documentElement.scrollWidth > innerWidth + 1,
                  fields: document.querySelectorAll('input, select, textarea').length,
                  disabled: [...document.querySelectorAll('input, select, textarea, button')].every(e => e.disabled),
                  scenarios: document.querySelectorAll('.scenario').length,
                  style: !![...document.styleSheets].find(s => s.href && s.href.includes('wireframes.css'))
                })""")
                assert not result["overflow"], (filename.name, width, result)
                assert result["disabled"] and result["scenarios"] > 0 and result["style"], (filename.name, width, result)
                if filename.stem.startswith(("AD02_", "AD05_", "AD12_", "AD16_", "AD23_", "AD27_")) and width in (390, 1440):
                    page.screenshot(path=str(root / "previews" / f"{filename.stem}_{width}.png"), full_page=True)
                count += 1
                page.close()
    finally:
        browser.close()
print(f"PASS: {count} Chrome viewport checks (28 x 390/768/1440 px), no document overflow")
