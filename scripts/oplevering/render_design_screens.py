"""Render the 28 approved Timaflu HTML screen designs for the query deliverable.

Only used during evidence generation. The website itself remains HTML/CSS.
Requires: pip install playwright, and a local Chromium-compatible browser.
"""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
DESIGNS=ROOT/"Documentation/Architecture/screens"
TARGET=ROOT/"deliverables/query-screens"
BROWSER=Path(os.environ.get("TIMAFLU_SCREENSHOT_CHROME",r"C:\Program Files\Google\Chrome\Application\chrome.exe"))

def render():
    designs=sorted(DESIGNS.glob("AD??_*.html"))
    if len(designs)!=28:
        raise RuntimeError(f"Expected 28 approved screen designs, found {len(designs)}")
    TARGET.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as client:
        launch_options = {"headless": True, "args": ["--allow-file-access-from-files"]}
        if BROWSER.is_file():
            launch_options["executable_path"] = str(BROWSER)
        browser=client.chromium.launch(**launch_options)
        try:
            page=browser.new_page(viewport={"width":1440,"height":920},device_scale_factor=1)
            for design in designs:
                page.goto(design.as_uri(),wait_until="load",timeout=30000)
                body=page.locator("body")
                text=body.inner_text(timeout=15000).strip()
                if len(text)<50:
                    raise RuntimeError(f"Blank design: {design.name}")
                page.screenshot(path=str(TARGET/(design.stem+".png")),full_page=True,
                                animations="disabled",timeout=30000)
        finally:
            browser.close()
    files=list(TARGET.glob("AD??_*.png"))
    if len(files)!=28 or any(p.stat().st_size<5000 for p in files):
        raise RuntimeError(f"Missing/empty screen screenshots: {len(files)}")
    print(f"RENDERED_DESIGN_SCREENS={len(files)}", "BYTES=",sum(p.stat().st_size for p in files))
if __name__=="__main__":
    render()
