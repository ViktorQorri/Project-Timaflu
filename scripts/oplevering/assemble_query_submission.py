"""Create one complete school evidence document with 28 screens and real MySQL results."""
from pathlib import Path
import json
import re
from html import unescape
ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/"deliverables"
GET=WORK/"_query_get_evidence.md"
ACTIONS=WORK/"_mutation_audit.json"
OUTPUT=WORK/"query-output-per-screen.md"
SCREENS=ROOT/"Documentation/Architecture/screens"
tick=chr(96)
fence=tick*3
MAP={
"AD01":["/manufacturers","/manufacturers/1/edit","/manufacturers/1/prices"],
"AD02":["/reorder","/suppliers?product=Testmedicijn"],
"AD03":["/stock","/stock/minimums"],
"AD04":["/orders?q=Testmedicijn&quantity=1","/stock"],
"AD05":["/orders/new","/orders?q=Testmedicijn&quantity=1"],
"AD06":["/orders/status","/orders/1/status","/orders?order=1"],
"AD07":["/customers?q=TEST","/customers/1/edit"],
"AD08":["/order-picking","/deliveries?day=2026-10-22"],
"AD09":["/order-picking","/deliveries/1/label"],
"AD10":["/order-picking"],
"AD11":["/order-picking"],
"AD12":["/deliveries?day=2026-10-22"],
"AD13":["/deliveries?day=2026-10-22"],
"AD14":["/deliveries?day=2026-10-22"],
"AD15":["/deliveries?day=2026-10-22","/customers?q=TEST"],
"AD16":["/invoices/weekly?week_start=2026-10-19","/invoices/issued/1"],
"AD17":["/invoices?customer_id=1","/deliveries?day=2026-10-22"],
"AD18":["/invoices/outstanding","/invoices/1/reminders/1"],
"AD19":["/invoices?customer_id=1"],
"AD20":["/acquisition"],
"AD21":["/acquisition"],
"AD22":["/order-picking"],
"AD23":["/order-picking"],
"AD24":["/products/new","/products","/products/1/edit","/products/1/remove"],
"AD25":["/invoices?customer_id=1"],
"AD26":["/deliveries?day=2026-10-22"],
"AD27":["/deliveries?day=2026-10-22"],
"AD28":["/customers?q=TEST","/invoices?customer_id=1"],
}
PROCESS={
"Inkoop":["AD01","AD02","AD03","AD24"],
"Verkoop":["AD04","AD05","AD06","AD07","AD28"],
"Orderpicking":["AD08","AD09","AD10","AD11","AD22","AD23"],
"Distributie":["AD12","AD13","AD14","AD15","AD26","AD27"],
"Administratie":["AD16","AD17","AD18","AD19","AD25"],
"Acquisitie":["AD20","AD21"],
}
PROCESS_BY_ID={code:process for process,ids in PROCESS.items() for code in ids}
QUERY=re.compile(
r"(?ms)^### Query (\d+)\n"+re.escape(fence)+r"sql\n(.*?)\n"+re.escape(fence)
+r"\nParameters: "+re.escape(fence)+r"json\n(.*?)\n"+re.escape(fence)
+r"\nResultaat: (\d+) rij\(en\) \(maximaal 15 getoond\)\n"
+re.escape(fence)+r"json\n(.*?)\n"+re.escape(fence)
)
def j(x):return json.dumps(x,ensure_ascii=False,indent=2,default=str)
def block(lang,source):return ["",fence+lang,source,fence,""]
def get_sections(text):
    out={}
    for section in re.split(r"(?m)^## ",text)[1:]:
        route=re.search(r"(?m)^Scherm: (.+)$",section)
        if not route:continue
        q=[]
        for m in QUERY.finditer(section):
            q.append(dict(sql=m[2],params=json.loads(m[3]),count=int(m[4]),rows=json.loads(m[5])))
        if len(q)!=len(re.findall(r"(?m)^### Query ",section)):
            raise RuntimeError("Incomplete GET evidence for "+route[1])
        out[route[1]]=(section.splitlines()[0].strip(),q)
    return out
def create():
    raw=GET.read_text(encoding="utf8").replace("\r\n","\n")
    gets=get_sections(raw)
    actions=json.loads(ACTIONS.read_text(encoding="utf8"))
    designs=sorted(SCREENS.glob("AD??_*.html"))
    if len(designs)!=28 or len(MAP)!=28:raise RuntimeError("Expected 28 screen designs")
    if len(actions)!=37 or any(c["result"]!="passed" for c in actions):
        raise RuntimeError("The 37 POST cases must all pass before submission.")
    if len(gets)!=29 or sum(len(q) for _,q in gets.values())<45:
        raise RuntimeError("Incomplete GET coverage")
    if len(list((WORK/"query-screens").glob("AD??_*.png")))!=28:
        raise RuntimeError("28 screen image files required")
    write_count=sum(sum("affected_rows" in q for q in a["sql"]) for a in actions)
    report=[
      "# Timaflu: alle schermen, queries en echte MySQL-uitvoer","",
      "## Verantwoording","",
      f"Dit schooldocument bevat 28 HTML/CSS-schermontwerpen, {len(gets)} gemeten Flask-GET-schermverzoeken, "
      f"{sum(len(q) for _,q in gets.values())} werkelijk uitgevoerde GET-queries en "
      f"{len(actions)} werkende formulier- en robotacties met {write_count} SQL-schrijfbewerkingen.","",
      "De afbeeldingen tonen de statische schermontwerpen; dit zijn geen screenshots van de actieve Flask-frontend.",
      "SQL-statements, parameters, resultaten, gewijzigde rijen en verificatie-SELECTs komen uit een geïsoleerde MySQL-testdatabase.",
      "Schrijfacties zijn uitgevoerd en na hun verificatie per scenario teruggedraaid. De gebruikte gegevens zijn fictief.",
      "Bij tijdgebonden scenario's zijn de relevante testdatums gecontroleerd gesimuleerd: "
      "8 november 2026 voor de betalingsherinnering en 31 december 2026 voor de jaarafsluiting. "
      "Er zijn geen echte herinneringen verzonden of financiële mutaties uitgevoerd.",
      "Een lege resultatenlijst komt uitsluitend voor bij optionele situaties zonder voorbeeldrecord, "
      "zoals niet-ingedeelde leveringen of aanvullende bezorgkosten. Een lege lijst is geen positief bewijs "
      "voor het ophalen van aanwezige records; de betreffende bronquery en het nulresultaat blijven zichtbaar.",
      "Een INSERT/UPDATE/DELETE geeft in MySQL geen tabel met gegevens terug: daarom wordt de echte rowcount getoond "
      "en daarna het resultaat van een aparte verificatie-SELECT. Lege SELECT-resultaten blijven expliciet zichtbaar.",
      "De 28 ontwerpen zijn aan de gerelateerde actieve pagina's en hun queries gekoppeld. De originele 29 GET-registraties "
      "staan achteraan volledig en in testvolgorde.","",
      "## Schermontwerpen met querybewijs","",
    ]
    for design in designs:
        ad=design.name[:4]
        if ad not in MAP or ad not in PROCESS_BY_ID:raise RuntimeError("Unmapped design: "+ad)
        title_html=design.read_text(encoding="utf8")
        head=re.search(r"<h1\b[^>]*>(.*?)</h1>",title_html,re.I|re.S)
        title=re.sub(r"\s+"," ",unescape(re.sub(r"<[^>]+>"," ",head[1]))).strip() if head else design.stem[5:].replace("_"," ")
        image=design.stem+".png"
        if not (WORK/"query-screens"/image).is_file():raise RuntimeError("Missing screenshot "+image)
        report.extend([f"### {ad}: {title}","",
                       f"Bedrijfsproces: **{PROCESS_BY_ID[ad]}**. Ontwerpbestand: {tick}{design.name}{tick}.","",
                       f"![{ad} schermontwerp](query-screens/{image})","",
                       "De afbeelding is het statische ontwerp en dient om de queries aan de schermvelden te koppelen.","",
                       "#### Relevante leesqueries met echte output",""])
        qnum=0
        for url in MAP[ad]:
            if url not in gets:raise RuntimeError(f"{ad} has no evidence for {url}")
            name,qs=gets[url]
            report += [f"**Werkende pagina:** {name} ({tick}{url}{tick}).",""]
            for q in qs:
                qnum+=1
                report += [f"##### Leesquery {qnum}",""]
                report += block("sql",q["sql"])
                report += ["Parameters:"]+block("json",j(q["params"]))
                report += [f"**MySQL-resultaat:** {q['count']} rij(en), {len(q['rows'])} weergegeven."]
                report += block("json",j(q["rows"]))
            if not qs:report += ["Geen SQL nodig voor dit specifieke GET-verzoek.",""]
        if not qnum:raise RuntimeError(ad+" has zero relevant read queries")
        related=[a for a in actions if a["ad"]==ad]
        report+=["#### Relevante schrijf- of formulieracties",""]
        if not related:
            report+=["Dit ontwerp toont hier een raadplegingsstap. Voor dit ontwerp is geen aparte mutatie uitgevoerd.",""]
        for case in related:
            report+= [f"##### {case['name']}","",
                      "Werkelijke HTTP-verzoeken: "+", ".join(f"{tick}POST {x['url']}{tick} (HTTP {x['status']})" for x in case["steps"])+".","",
                      "De databasewijziging is binnen een testtransactie gecontroleerd en daarna teruggedraaid.",""]
            for k,q in enumerate(case["sql"],1):
                report += [f"**Uitgevoerd SQL-statement {k}**"]
                report += block("sql",q["sql"])
                report += ["Parameters:"]+block("json",j(q["params"]))
                if "affected_rows" in q:
                    report += [f"**MySQL-uitvoer:** {q['affected_rows']} gewijzigde rij(en)."]
                    if q.get("last_insert_id"):
                        report += [f"Door MySQL toegewezen test-ID: {q['last_insert_id']}."]
                    report += [""]
                else:
                    report += [f"**MySQL-uitvoer:** {q['row_count']} gevonden rij(en), {len(q['rows'])} getoond."]
                    report += block("json",j(q["rows"]))
            verify=case["verification"]
            report += ["**Verificatie na de schrijfbewerking:**"]+block("sql",verify["sql"])
            report += [f"**Resultaat verificatie:** {verify['row_count']} rij(en)."]+block("json",j(verify["rows"]))
    report += ["## Volledig register van de daadwerkelijk opgevraagde Flask-schermen","",
               "Dit register bevat alle afzonderlijke GET-verzoeken in de oorspronkelijke auditvolgorde.",""]
    # Preserve one canonical set of 'Scherm:' and '### Query' entries for the ZIP validator.
    report += raw.splitlines()[2:]
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text("\n".join(report).strip()+"\n",encoding="utf8")
    print("DESIGNS=28","GET_SCREENS="+str(len(gets)),"GET_QUERIES="+str(sum(len(q) for _,q in gets.values())),
          "POST_SCENARIOS="+str(len(actions)),"SQL_WRITES="+str(write_count),"BYTES="+str(OUTPUT.stat().st_size))
if __name__=="__main__":create()
