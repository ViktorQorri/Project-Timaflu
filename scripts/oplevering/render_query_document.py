"""Render the completed query evidence document as a readable, printable PDF.

The original Markdown and screenshot images remain available alongside the PDF.
The PDF is generated only after all MySQL evidence has been collected.
"""
from pathlib import Path
import markdown
from playwright.sync_api import sync_playwright
import os

ROOT=Path(__file__).resolve().parents[2]
FOLDER=ROOT/"deliverables"
MD=FOLDER/"query-output-per-screen.md"
HTML=FOLDER/"query-output-per-screen.html"
PDF=FOLDER/"query-output-per-screen.pdf"
BROWSER=Path(os.environ.get("TIMAFLU_SCREENSHOT_CHROME",r"C:\Program Files\Google\Chrome\Application\chrome.exe"))
STYLE="""
@page { size: A4; margin: 12mm 12mm 14mm; }
body {font-family: 'Segoe UI',Arial,sans-serif; font-size: 9pt; line-height:1.4;
      color:#1c2833; margin:0;}
h1 { font-size:24pt; line-height:1.2; margin: 0 0 13mm; color:#0d3355;}
h2 {font-size:17pt; margin:15mm 0 5mm; color:#0d3355; break-before:page;}
h3 {font-size:14pt; color:#143f63; margin:6mm 0 4mm; break-before:page;}
h4 {font-size:11pt; color:#143f63; margin:5mm 0 2mm;}
h5 {font-size:10pt; margin:4mm 0 2mm; color:#182f47;}
p, li { margin:2mm 0; }
strong { font-weight:700; }
pre { background:#f1f4f7; color:#122a39; border-left: 2pt solid #d0dbe5;
      padding:2.5mm; font-size:7pt; font-family:Consolas,monospace;
      line-height:1.35; white-space:pre-wrap; overflow-wrap:anywhere;
      word-break:break-word; border-radius:1mm; }
code { font-family:Consolas,monospace;overflow-wrap:anywhere; }
p code { font-size:8pt;background:#f1f4f7; padding:0 1mm; }
img { display:block; max-width:100%; max-height:195mm; width:auto; height:auto;
      object-fit:contain; break-inside:avoid; margin:3mm auto 4mm; }
table { border-collapse:collapse; width:100%; font-size:8pt; }
td,th { border:0.3pt solid #c7d2db; padding:1.5mm; vertical-align:top;}
th {background:#eaf0f4;}
a { color:#15517a; text-decoration:none; }
@media screen {body {max-width:1000px;margin:30px auto;padding:0 32px;}}
"""

def render():
    src=MD.read_text(encoding="utf8")
    if src.count("![AD")!=28:
        raise RuntimeError("All 28 design images must be present before PDF creation")
    body=markdown.markdown(src,extensions=["fenced_code","tables","sane_lists","toc"])
    doc='<!doctype html><html lang="nl"><head><meta charset="utf-8"><title>Timaflu | Schermen en MySQL-querybewijs</title><style>'+STYLE+'</style></head><body>'+body+'</body></html>'
    HTML.write_text(doc,encoding="utf8")
    with sync_playwright() as pw:
        launch_options = {"headless": True, "args": ["--allow-file-access-from-files"]}
        if BROWSER.is_file():
            launch_options["executable_path"] = str(BROWSER)
        browser=pw.chromium.launch(**launch_options)
        try:
            page=browser.new_page(viewport={"width":1440,"height":900})
            page.goto(HTML.as_uri(),wait_until="load",timeout=120000)
            loaded=page.locator("img").count()
            if loaded !=28:
                raise RuntimeError(f"PDF source has {loaded} design images instead of 28.")
            bad=page.evaluate("Array.from(document.images).filter(i => !i.complete || i.naturalWidth===0).length")
            if bad:raise RuntimeError(f"{bad} missing image(s) in PDF source")
            page.pdf(path=str(PDF),format="A4",prefer_css_page_size=True,
                     print_background=True)
        finally:
            browser.close()
    if PDF.stat().st_size<30000:raise RuntimeError("Unexpectedly small PDF")
    print("PDF_BYTES",PDF.stat().st_size,"HTML_BYTES",HTML.stat().st_size)
if __name__=="__main__":render()
