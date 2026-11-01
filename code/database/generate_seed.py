"""Generate seed.sql: a large, consistent demo data set for every Timaflu screen.

Dates are written relative to the day seed.sql runs (@m is Monday of the current
week, @t is today), so the delivery schedule, weekly invoices, payment reminders
and acquisition follow-ups stay current. Invoice amounts are computed with the
application's own Invoice class, the same way WeeklyInvoiceRepository does.

Run from the repository root: python code/database/generate_seed.py
"""
import random
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code" / "backend"))
from domain.business import Invoice, euro  # noqa: E402

OUT = Path(__file__).resolve().parent / "seed.sql"
HISTORY_WEEKS = 64
ROBOT_LIVE_WEEKS = 1
rng = random.Random(20261101)


# ---------------------------------------------------------------------------
# SQL helpers
# ---------------------------------------------------------------------------

class Raw(str):
    """SQL that is written as is, such as an expression."""


class Day:
    """A date relative to a SQL variable: @m, @t, @vw (previous working day) or @nw."""

    RANK = {"@m": 0, "@vw": 1, "@t": 2, "@nw": 3, "@nw2": 4}

    def __init__(self, base, offset=0):
        self.base, self.offset = base, offset

    def plus(self, days):
        return Day(self.base, self.offset + days)

    def key(self):
        if self.base == "@m":
            return (0, self.offset)
        return (1, self.RANK[self.base], self.offset)

    def sql(self):
        if self.offset == 0:
            return self.base
        sign = "+" if self.offset > 0 else "-"
        return f"{self.base} {sign} INTERVAL {abs(self.offset)} DAY"


def at(day, hhmm):
    return Raw(f"TIMESTAMP({day.sql()}, '{hhmm}:00')")


def q(value):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, Day):
        return value.sql()
    if isinstance(value, Raw):
        return str(value)
    if isinstance(value, (int, Decimal)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


class Script:
    def __init__(self):
        self.parts = []

    def line(self, text=""):
        self.parts.append(text + "\n")

    def section(self, title, *notes):
        self.line()
        self.line("-- =========================================")
        self.line(f"-- {title}")
        for note in notes:
            self.line(f"-- {note}")
        self.line("-- =========================================")
        self.line()

    def insert(self, table, columns, rows, chunk=250):
        for start in range(0, len(rows), chunk):
            body = ",\n".join(
                "    (" + ", ".join(q(v) for v in row) + ")"
                for row in rows[start:start + chunk]
            )
            self.line(f"INSERT INTO {table} ({', '.join(columns)})\nVALUES\n{body};")

    def text(self):
        return "".join(self.parts)


def money(value):
    return euro(Decimal(str(value)))


def hhmm(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


# ---------------------------------------------------------------------------
# Master data
# ---------------------------------------------------------------------------

# Three courier regions, as in the case. Town, area code, postcode prefix.
TOWNS = {
    "Noord": [("Arnhem", "026", "68"), ("Ede", "0318", "67"), ("Wageningen", "0317", "67"),
              ("Zevenaar", "0316", "69"), ("Velp", "026", "68")],
    "Midden": [("Nijmegen", "024", "65"), ("Wijchen", "024", "66"), ("Beuningen", "024", "66"),
               ("Druten", "0487", "66"), ("Tiel", "0344", "40")],
    "Zuid": [("Oss", "0412", "53"), ("Uden", "0413", "54"), ("Cuijk", "0485", "54"),
             ("Boxmeer", "0485", "58"), ("Gennep", "0485", "65")],
}
STREETS = [
    "Dorpsstraat", "Kerkstraat", "Molenweg", "Stationsplein", "Marktplein", "Julianastraat",
    "Wilhelminalaan", "Beatrixplein", "Lindenlaan", "Eikenlaan", "Parkweg", "Schoolstraat",
    "Hoofdstraat", "Bergweg", "Raadhuisplein", "Oranjestraat", "Nieuwstraat", "Kastanjelaan",
    "Tulpstraat", "Rozenhof", "Zuiderpark", "Noorderplein", "Brinkweg", "Veldstraat",
    "Burgemeester Smitlaan", "Prins Hendrikstraat", "Van Goghlaan", "Graaf Ottoweg",
    "Heuvelweg", "Esdoornstraat", "Populierenlaan", "Gildeplein", "Waterstraat", "Vijverlaan",
]
PHARMACY_NAMES = [
    "De Linde", "Het Anker", "De Brink", "Zuiderhof", "De Vlinder", "Het Kruispunt", "De Eik",
    "De Molen", "Het Baken", "De Hoven", "Oranjehof", "De Akker", "Lindeplein", "De Poort",
    "Marktzicht", "Rivierenhof", "De Kastanje", "Het Hofje", "De Wieken", "Esdoorn", "De Meander",
    "Waalkade", "Rijnzicht", "De Veste", "Het Veld", "Kloosterhof", "De Beuk", "Maaszicht",
    "De Bongerd", "Het Kompas", "De Ster", "Zonnehof", "De Hazelaar", "Het Plein", "De Wilg",
    "Berghof", "De Eendracht", "Het Gilde", "De Klaproos", "Vijverhof", "De Lindehof",
    "Het Station", "De Boogaard", "Parkzicht", "De Dreef", "Het Spoor", "De Morgenster",
    "De Vaart", "De Laar", "Hoogstraat", "De Ridder", "De Zevensprong", "De Toren", "Kerkplein",
    "Het Ven", "De Gaard", "Het Klooster", "De Horst", "Het Kasteel", "De Wetering",
]
INITIALS = "ABCDEFGHIJKLMNPRSTVW"
SURNAMES = [
    "de Vries", "Jansen", "van den Berg", "Bakker", "Visser", "Smit", "Meijer", "de Boer",
    "Mulder", "de Groot", "Bos", "Vos", "Peters", "Hendriks", "van Leeuwen", "Dekker",
    "Brouwer", "de Wit", "Dijkstra", "Smits", "de Graaf", "van der Meer", "Kok", "Jacobs",
    "Vermeulen", "van Dijk", "Willems", "Hoekstra", "Koster", "Verhoeven", "Prins", "Postma",
    "Kuipers", "Yilmaz", "El Amrani", "Pinas", "Nguyen", "Kaya", "Wouters", "Claassen",
]

# Aisle, product name, active ingredients, packaging, retail packs, price per
# wholesale pack, short description, minimum order quantity, popularity (1-5).
PRODUCTS = [
    ("A", "Paracetamol 500 mg tabletten", [("paracetamol", "500 mg")], "doos", 50, "38.50", "Pijnstiller en koortsverlager", 3, 5),
    ("A", "Paracetamol 1000 mg tabletten", [("paracetamol", "1000 mg")], "doos", 30, "41.80", "Pijnstiller en koortsverlager", 3, 4),
    ("A", "Paracetamol 120 mg zetpillen", [("paracetamol", "120 mg")], "doos", 20, "36.40", "Koortsverlager voor kinderen", 2, 2),
    ("A", "Ibuprofen 400 mg tabletten", [("ibuprofen", "400 mg")], "doos", 40, "44.60", "Ontstekingsremmende pijnstiller", 3, 5),
    ("A", "Ibuprofen 600 mg tabletten", [("ibuprofen", "600 mg")], "doos", 30, "48.90", "Ontstekingsremmende pijnstiller", 2, 3),
    ("A", "Naproxen 500 mg tabletten", [("naproxen", "500 mg")], "doos", 30, "52.30", "Ontstekingsremmende pijnstiller", 2, 2),
    ("A", "Diclofenac 50 mg maagsapresistente tabletten", [("diclofenacnatrium", "50 mg")], "doos", 30, "39.70", "Ontstekingsremmende pijnstiller", 2, 3),
    ("A", "Tramadol 50 mg capsules", [("tramadolhydrochloride", "50 mg")], "doos", 20, "64.20", "Opioïde pijnstiller", 2, 2),
    ("A", "Oxycodon 5 mg tabletten", [("oxycodonhydrochloride", "5 mg")], "doos", 10, "86.00", "Sterke opioïde pijnstiller", 1, 1),
    ("A", "Morfine 10 mg tabletten met gereguleerde afgifte", [("morfinesulfaat", "10 mg")], "doos", 10, "98.50", "Sterke opioïde pijnstiller", 1, 1),
    ("A", "Codeïne 10 mg tabletten", [("codeïnefosfaat", "10 mg")], "doos", 20, "54.00", "Hoestprikkeldemper", 2, 1),
    ("A", "Paracetamol/codeïne 500/10 mg tabletten", [("paracetamol", "500 mg"), ("codeïnefosfaat", "10 mg")], "doos", 20, "49.40", "Pijnstiller, combinatiepreparaat", 2, 2),
    ("B", "Amoxicilline 500 mg capsules", [("amoxicilline", "500 mg")], "doos", 30, "79.00", "Antibioticum", 2, 4),
    ("B", "Amoxicilline/clavulaanzuur 500/125 mg tabletten", [("amoxicilline", "500 mg"), ("clavulaanzuur", "125 mg")], "doos", 20, "104.00", "Antibioticum, combinatiepreparaat", 2, 3),
    ("B", "Azitromycine 500 mg tabletten", [("azitromycine", "500 mg")], "doos", 20, "92.00", "Antibioticum", 1, 2),
    ("B", "Doxycycline 100 mg tabletten", [("doxycycline", "100 mg")], "doos", 30, "58.50", "Antibioticum", 2, 3),
    ("B", "Feneticilline 500 mg capsules", [("feneticilline", "500 mg")], "doos", 30, "63.00", "Antibioticum", 2, 2),
    ("B", "Ciprofloxacine 500 mg tabletten", [("ciprofloxacine", "500 mg")], "doos", 20, "84.80", "Antibioticum", 1, 2),
    ("B", "Nitrofurantoïne 100 mg capsules met gereguleerde afgifte", [("nitrofurantoïne", "100 mg")], "doos", 30, "51.60", "Middel bij blaasontsteking", 2, 3),
    ("B", "Claritromycine 500 mg tabletten", [("claritromycine", "500 mg")], "doos", 20, "88.00", "Antibioticum", 1, 1),
    ("B", "Metronidazol 500 mg tabletten", [("metronidazol", "500 mg")], "doos", 20, "47.20", "Antibioticum", 1, 1),
    ("B", "Aciclovir 400 mg tabletten", [("aciclovir", "400 mg")], "doos", 20, "76.40", "Virusremmer", 1, 1),
    ("B", "Valaciclovir 500 mg tabletten", [("valaciclovir", "500 mg")], "doos", 20, "118.00", "Virusremmer", 1, 1),
    ("B", "Fluconazol 150 mg capsules", [("fluconazol", "150 mg")], "doos", 30, "39.90", "Middel tegen schimmelinfecties", 2, 2),
    ("C", "Amlodipine 5 mg tabletten", [("amlodipine", "5 mg")], "doos", 60, "29.40", "Bloeddrukverlager", 3, 5),
    ("C", "Metoprolol 50 mg tabletten met gereguleerde afgifte", [("metoprololsuccinaat", "47,5 mg")], "doos", 60, "34.80", "Betablokker", 3, 4),
    ("C", "Bisoprolol 5 mg tabletten", [("bisoprololfumaraat", "5 mg")], "doos", 60, "27.60", "Betablokker", 3, 3),
    ("C", "Lisinopril 10 mg tabletten", [("lisinopril", "10 mg")], "doos", 60, "26.90", "Bloeddrukverlager", 3, 3),
    ("C", "Enalapril 10 mg tabletten", [("enalaprilmaleaat", "10 mg")], "doos", 60, "25.70", "Bloeddrukverlager", 3, 2),
    ("C", "Losartan 50 mg tabletten", [("losartankalium", "50 mg")], "doos", 60, "31.20", "Bloeddrukverlager", 3, 4),
    ("C", "Valsartan 80 mg tabletten", [("valsartan", "80 mg")], "doos", 60, "36.50", "Bloeddrukverlager", 2, 2),
    ("C", "Hydrochloorthiazide 12,5 mg tabletten", [("hydrochloorthiazide", "12,5 mg")], "doos", 60, "19.80", "Plasmiddel", 3, 3),
    ("C", "Furosemide 40 mg tabletten", [("furosemide", "40 mg")], "doos", 60, "21.60", "Plasmiddel", 3, 3),
    ("C", "Spironolacton 25 mg tabletten", [("spironolacton", "25 mg")], "doos", 60, "30.10", "Plasmiddel", 2, 2),
    ("C", "Simvastatine 40 mg tabletten", [("simvastatine", "40 mg")], "doos", 60, "30.90", "Cholesterolverlager", 3, 5),
    ("C", "Atorvastatine 20 mg tabletten", [("atorvastatine", "20 mg")], "doos", 60, "37.30", "Cholesterolverlager", 3, 4),
    ("C", "Rosuvastatine 10 mg tabletten", [("rosuvastatine", "10 mg")], "doos", 60, "42.80", "Cholesterolverlager", 2, 3),
    ("C", "Acetylsalicylzuur 80 mg dispergeerbare tabletten", [("acetylsalicylzuur", "80 mg")], "doos", 90, "23.40", "Bloedplaatjesremmer", 3, 5),
    ("C", "Clopidogrel 75 mg tabletten", [("clopidogrel", "75 mg")], "doos", 30, "51.00", "Bloedplaatjesremmer", 2, 2),
    ("C", "Apixaban 5 mg tabletten", [("apixaban", "5 mg")], "doos", 20, "225.00", "Antistollingsmiddel", 1, 2),
    ("C", "Rivaroxaban 20 mg tabletten", [("rivaroxaban", "20 mg")], "doos", 20, "248.00", "Antistollingsmiddel", 1, 1),
    ("C", "Acenocoumarol 1 mg tabletten", [("acenocoumarol", "1 mg")], "doos", 50, "24.50", "Antistollingsmiddel", 2, 2),
    ("C", "Ezetimibe 10 mg tabletten", [("ezetimibe", "10 mg")], "doos", 30, "46.40", "Cholesterolverlager", 1, 1),
    ("D", "Metformine 500 mg tabletten", [("metforminehydrochloride", "500 mg")], "doos", 60, "23.90", "Bloedsuikerverlager", 3, 5),
    ("D", "Metformine 850 mg tabletten", [("metforminehydrochloride", "850 mg")], "doos", 60, "27.20", "Bloedsuikerverlager", 3, 4),
    ("D", "Gliclazide 80 mg tabletten", [("gliclazide", "80 mg")], "doos", 60, "26.40", "Bloedsuikerverlager", 2, 2),
    ("D", "Sitagliptine 100 mg tabletten", [("sitagliptine", "100 mg")], "doos", 20, "164.00", "Bloedsuikerverlager", 1, 2),
    ("D", "Insuline glargine 100 E/ml voorgevulde pen", [("insuline glargine", "100 E/ml")], "koelverpakking", 5, "289.00", "Langwerkende insuline", 1, 3),
    ("D", "Insuline aspart 100 E/ml voorgevulde pen", [("insuline aspart", "100 E/ml")], "koelverpakking", 5, "264.00", "Snelwerkende insuline", 1, 2),
    ("D", "Insuline lispro 100 E/ml patronen", [("insuline lispro", "100 E/ml")], "koelverpakking", 5, "246.00", "Snelwerkende insuline", 1, 1),
    ("D", "Glucagon 1 mg poeder voor injectievloeistof", [("glucagon", "1 mg")], "koelverpakking", 5, "174.00", "Middel bij ernstige hypoglykemie", 1, 1),
    ("D", "Levothyroxine 50 microgram tabletten", [("levothyroxinenatrium", "50 microgram")], "doos", 60, "18.80", "Schildklierhormoon", 3, 4),
    ("D", "Levothyroxine 100 microgram tabletten", [("levothyroxinenatrium", "100 microgram")], "doos", 60, "20.60", "Schildklierhormoon", 3, 3),
    ("D", "Prednisolon 5 mg tabletten", [("prednisolon", "5 mg")], "doos", 50, "21.10", "Corticosteroïde", 2, 3),
    ("D", "Alendroninezuur 70 mg tabletten", [("alendroninezuur", "70 mg")], "doos", 20, "34.70", "Middel tegen botontkalking", 2, 2),
    ("D", "Calciumcarbonaat/colecalciferol 1,25 g/800 IE kauwtabletten", [("calciumcarbonaat", "1,25 g"), ("colecalciferol", "800 IE")], "doos", 30, "31.50", "Calcium met vitamine D", 2, 3),
    ("E", "Salbutamol 100 microgram/dosis aerosol", [("salbutamol", "100 microgram/dosis")], "doos", 20, "54.00", "Luchtwegverwijder", 2, 4),
    ("E", "Fluticason/salmeterol 250/50 microgram inhalatiepoeder", [("fluticasonpropionaat", "250 microgram"), ("salmeterol", "50 microgram")], "doos", 10, "208.00", "Ontstekingsremmer en luchtwegverwijder", 1, 2),
    ("E", "Budesonide/formoterol 200/6 microgram inhalatiepoeder", [("budesonide", "200 microgram"), ("formoterolfumaraat", "6 microgram")], "doos", 10, "196.00", "Ontstekingsremmer en luchtwegverwijder", 1, 2),
    ("E", "Tiotropium 18 microgram inhalatiecapsules", [("tiotropium", "18 microgram")], "doos", 10, "224.00", "Luchtwegverwijder", 1, 1),
    ("E", "Beclometason 100 microgram/dosis aerosol", [("beclometasondipropionaat", "100 microgram/dosis")], "doos", 10, "88.00", "Ontstekingsremmer voor de luchtwegen", 1, 2),
    ("E", "Montelukast 10 mg tabletten", [("montelukast", "10 mg")], "doos", 30, "41.80", "Middel bij astma", 2, 2),
    ("E", "Cetirizine 10 mg tabletten", [("cetirizinedihydrochloride", "10 mg")], "doos", 30, "16.90", "Antihistaminicum", 3, 4),
    ("E", "Loratadine 10 mg tabletten", [("loratadine", "10 mg")], "doos", 30, "15.60", "Antihistaminicum", 3, 3),
    ("E", "Desloratadine 5 mg tabletten", [("desloratadine", "5 mg")], "doos", 30, "28.40", "Antihistaminicum", 2, 2),
    ("E", "Xylometazoline 1 mg/ml neusspray", [("xylometazolinehydrochloride", "1 mg/ml")], "doos", 24, "24.30", "Neusslijmvliesontzwellend middel", 3, 3),
    ("E", "Fluticason 50 microgram/dosis neusspray", [("fluticasonpropionaat", "50 microgram/dosis")], "doos", 12, "44.60", "Ontstekingsremmer voor de neus", 2, 2),
    ("E", "Adrenaline 0,3 mg auto-injector", [("adrenaline", "0,3 mg")], "doos", 5, "372.00", "Noodmedicatie bij anafylaxie", 1, 1),
    ("F", "Sertraline 50 mg tabletten", [("sertraline", "50 mg")], "doos", 30, "32.80", "Antidepressivum", 2, 3),
    ("F", "Citalopram 20 mg tabletten", [("citalopram", "20 mg")], "doos", 30, "28.90", "Antidepressivum", 2, 3),
    ("F", "Paroxetine 20 mg tabletten", [("paroxetine", "20 mg")], "doos", 30, "30.20", "Antidepressivum", 2, 2),
    ("F", "Oxazepam 10 mg tabletten", [("oxazepam", "10 mg")], "doos", 50, "19.40", "Kalmerend middel", 3, 3),
    ("F", "Temazepam 10 mg capsules", [("temazepam", "10 mg")], "doos", 30, "23.80", "Slaapmiddel", 2, 2),
    ("F", "Diazepam 5 mg tabletten", [("diazepam", "5 mg")], "doos", 50, "17.90", "Kalmerend middel", 2, 2),
    ("F", "Quetiapine 25 mg tabletten", [("quetiapine", "25 mg")], "doos", 30, "37.70", "Antipsychoticum", 2, 2),
    ("F", "Levetiracetam 500 mg tabletten", [("levetiracetam", "500 mg")], "doos", 30, "78.00", "Anti-epilepticum", 1, 1),
    ("F", "Lamotrigine 100 mg tabletten", [("lamotrigine", "100 mg")], "doos", 30, "57.30", "Anti-epilepticum", 1, 1),
    ("F", "Methylfenidaat 10 mg tabletten", [("methylfenidaathydrochloride", "10 mg")], "doos", 30, "64.00", "Middel bij ADHD", 2, 2),
    ("F", "Sumatriptan 50 mg tabletten", [("sumatriptan", "50 mg")], "doos", 12, "48.00", "Middel bij migraine", 2, 1),
    ("G", "Omeprazol 20 mg maagsapresistente capsules", [("omeprazol", "20 mg")], "doos", 56, "26.80", "Maagzuurremmer", 3, 5),
    ("G", "Pantoprazol 40 mg maagsapresistente tabletten", [("pantoprazol", "40 mg")], "doos", 56, "29.60", "Maagzuurremmer", 3, 4),
    ("G", "Esomeprazol 40 mg maagsapresistente tabletten", [("esomeprazol", "40 mg")], "doos", 28, "39.10", "Maagzuurremmer", 2, 2),
    ("G", "Macrogol/elektrolyten poeder voor drank", [("macrogol 3350", "13,1 g"), ("natriumchloride", "351 mg")], "doos", 30, "35.40", "Laxeermiddel", 2, 3),
    ("G", "Loperamide 2 mg capsules", [("loperamidehydrochloride", "2 mg")], "doos", 20, "14.80", "Middel tegen diarree", 3, 3),
    ("G", "Domperidon 10 mg tabletten", [("domperidon", "10 mg")], "doos", 30, "25.20", "Middel tegen misselijkheid", 2, 2),
    ("G", "Ondansetron 4 mg smelttabletten", [("ondansetron", "4 mg")], "doos", 10, "57.50", "Middel tegen misselijkheid", 1, 1),
    ("G", "Mesalazine 500 mg maagsapresistente tabletten", [("mesalazine", "500 mg")], "doos", 30, "102.00", "Ontstekingsremmer voor de darm", 1, 1),
    ("G", "Lactulose 670 mg/ml stroop", [("lactulose", "670 mg/ml")], "doos", 12, "31.70", "Laxeermiddel", 2, 2),
    ("H", "Hydrocortison 1% crème", [("hydrocortisonacetaat", "10 mg/g")], "doos", 24, "21.30", "Mild corticosteroïd voor de huid", 2, 3),
    ("H", "Triamcinolonacetonide 0,1% crème", [("triamcinolonacetonide", "1 mg/g")], "doos", 24, "24.90", "Corticosteroïd voor de huid", 2, 2),
    ("H", "Fusidinezuur 20 mg/g crème", [("fusidinezuur", "20 mg/g")], "doos", 24, "34.60", "Antibioticum voor de huid", 2, 2),
    ("H", "Miconazol 20 mg/g crème", [("miconazolnitraat", "20 mg/g")], "doos", 24, "18.40", "Middel tegen schimmelinfecties van de huid", 2, 2),
    ("H", "Tamsulosine 0,4 mg capsules met gereguleerde afgifte", [("tamsulosinehydrochloride", "0,4 mg")], "doos", 30, "35.20", "Middel bij prostaatklachten", 2, 3),
    ("H", "Finasteride 5 mg tabletten", [("finasteride", "5 mg")], "doos", 30, "40.80", "Middel bij prostaatvergroting", 2, 1),
    ("H", "Allopurinol 100 mg tabletten", [("allopurinol", "100 mg")], "doos", 50, "19.70", "Middel bij jicht", 2, 2),
    ("H", "Colchicine 0,5 mg tabletten", [("colchicine", "0,5 mg")], "doos", 30, "32.90", "Middel bij jichtaanvallen", 2, 1),
    ("H", "Foliumzuur 0,5 mg tabletten", [("foliumzuur", "0,5 mg")], "doos", 90, "10.60", "Vitamine B11", 3, 2),
    ("H", "Ferrofumaraat 200 mg tabletten", [("ferrofumaraat", "200 mg")], "doos", 50, "15.40", "IJzerpreparaat", 2, 2),
    ("H", "Hydroxocobalamine 1 mg/ml injectievloeistof", [("hydroxocobalamine", "1 mg/ml")], "doos", 10, "41.00", "Vitamine B12", 2, 1),
    # Taken off the assortment; the rows remain for old orders and invoices.
    ("G", "Ranitidine 150 mg tabletten", [("ranitidine", "150 mg")], "doos", 30, "22.40", "Maagzuurremmer", 3, 3),
    ("C", "Isosorbidemononitraat 30 mg tabletten met gereguleerde afgifte", [("isosorbidemononitraat", "30 mg")], "doos", 30, "28.70", "Middel bij angina pectoris", 2, 1),
]
REMOVED_PRODUCTS = {"Ranitidine 150 mg tabletten",
                    "Isosorbidemononitraat 30 mg tabletten met gereguleerde afgifte"}
# Every manufacturer stopped supplying these: no offers, off the internal reorder list.
NOT_REORDERABLE = {"Codeïne 10 mg tabletten", "Glucagon 1 mg poeder voor injectievloeistof"}
# Out of stock: telephone orders for these become backorders.
OUT_OF_STOCK = {"Amoxicilline/clavulaanzuur 500/125 mg tabletten", "Methylfenidaat 10 mg tabletten"}
# Retail pack contents by dosage form, for the long description. First match wins.
UNITS = [("tablet", "tabletten"), ("capsule", "capsules"), ("zetpil", "zetpillen"),
         ("crème", "tubes"), ("neusspray", "flacons"), ("aerosol", "inhalatoren"),
         ("inhalatiepoeder", "inhalatoren"), ("pen", "voorgevulde pennen"), ("patronen", "patronen"),
         ("stroop", "flessen"), ("poeder voor drank", "sachets"),
         ("poeder voor injectievloeistof", "injectiesets"), ("injectievloeistof", "ampullen"),
         ("auto-injector", "auto-injectoren")]
# Popular products that also have a shelf in a second aisle, so two robots can pick them.
SECOND_AISLE = {"Paracetamol 500 mg tabletten": "H", "Omeprazol 20 mg maagsapresistente capsules": "A",
                "Amlodipine 5 mg tabletten": "D"}

SUPPLIERS = [
    ("Farmadis Nederland BV", "Industrieweg 40, 3606 AS Maarssen", "030", "farmadis", "ABCDEFGH"),
    ("Medivio Pharma BV", "Transportweg 7, 2742 RH Waddinxveen", "0182", "medivio", "ABC"),
    ("Noord Farma Distributie", "Zernikepark 3, 9747 AN Groningen", "050", "noordfarma", "CDE"),
    ("Apotheca Generics BV", "Columbusweg 12, 5928 LA Venlo", "077", "apotheca", "ACDFG"),
    ("Benelux Medical Supplies", "Havenweg 21, 4782 SM Moerdijk", "0168", "bms", "BEH"),
    ("Pharmaline Europe BV", "Bijsterhuizen 2410, 6604 LM Wijchen", "024", "pharmaline", "ABDG"),
    ("Coolchain Pharma BV", "Kelvinring 8, 2952 BG Alblasserdam", "078", "coolchain", "DE"),
    ("GenericaNL BV", "Lange Dreef 15, 4131 NJ Vianen", "0347", "genericanl", "ACFGH"),
    ("Mediport Logistics BV", "Fokkerweg 300, 1438 AN Oude Meer", "020", "mediport", "BCEF"),
    ("Rhenus Farma BV", "Nieuwe Kade 4, 6827 AA Arnhem", "026", "rhenusfarma", "AFH"),
    ("Delta Health Products", "Moezelweg 160, 3198 LS Rotterdam", "010", "deltahealth", "BDEG"),
    ("Veluwe Pharma Groothandel", "Nijverheidsweg 18, 3771 ME Barneveld", "0342", "veluwepharma", "CH"),
]


def phone(area):
    digits = 10 - len(area)
    return f"{area}-{rng.randint(10 ** (digits - 1) * 2, 10 ** digits - 1)}"


def person():
    return f"{rng.choice(INITIALS)}. {rng.choice(SURNAMES)}"


def street_address(town, prefix):
    postcode = f"{prefix}{rng.randint(10, 99)} {rng.choice('ABCDEGHJKLMNPRST')}{rng.choice('ABCDEGHJKLMNPRSTVWXZ')}"
    return f"{rng.choice(STREETS)} {rng.randint(1, 180)}, {postcode} {town}"


class Ids:
    def __init__(self):
        self.counters = defaultdict(int)

    def next(self, table):
        self.counters[table] += 1
        return self.counters[table]


ids = Ids()
addresses = []


def new_address(text):
    address_id = ids.next("adres")
    addresses.append((address_id, text))
    return address_id


# ---------------------------------------------------------------------------
# Products, warehouse, suppliers
# ---------------------------------------------------------------------------

class Product:
    pass


products = []
aisle_counter = defaultdict(int)
for index, (aisle, name, substances, packaging, packs, price, short, minimum, popularity) in enumerate(PRODUCTS):
    p = Product()
    p.id = index + 1
    p.aisle, p.name, p.substances = aisle, name, substances
    p.packaging, p.packs, p.price = packaging, packs, Decimal(price)
    p.short, p.min_order, p.popularity = short, minimum, popularity
    aisle_counter[aisle] += 1
    p.number = f"TF-{ord(aisle) - 64}{aisle_counter[aisle]:03d}"
    p.order_code = f"{substances[0][0][:3].upper()}-{p.id:03d}"
    unit = next(unit for form, unit in UNITS if form in name)
    p.long = (f"{packaging.capitalize()} met {packs} verpakkingen {name.split(' ', 1)[0].lower()}"
              f" ({unit}). Bewaren volgens de bijsluiter.")
    if packaging == "koelverpakking":
        p.long += " Koel bewaren tussen 2 en 8 graden Celsius."
    p.in_assortment = name not in REMOVED_PRODUCTS
    p.reorderable = name not in NOT_REORDERABLE and p.in_assortment
    # Prices rose 4% half a year ago for every fourth product.
    p.old_price = money(p.price / Decimal("1.04")) if p.id % 4 == 0 else p.price
    products.append(p)
by_name = {p.name: p for p in products}
sellable = [p for p in products if p.in_assortment]

suppliers = []
for index, (name, address, area, domain, aisles) in enumerate(SUPPLIERS, 1):
    suppliers.append({
        "id": index, "name": name, "address_id": new_address(address),
        "contact": person(), "phone": phone(area),
        "web": f"https://www.{domain}.example", "aisles": aisles,
    })

offers = []
for p in products:
    if not p.reorderable:
        continue
    candidates = [s for s in suppliers if p.aisle in s["aisles"]]
    for supplier in rng.sample(candidates, min(len(candidates), rng.randint(1, 4))):
        offers.append((supplier["id"], p.id, money(p.price * Decimal(str(rng.uniform(0.55, 0.78))))))
offered_by = defaultdict(list)
for supplier_id, product_id, price in offers:
    offered_by[supplier_id].append(product_id)


# ---------------------------------------------------------------------------
# Customers and couriers
# ---------------------------------------------------------------------------

COURIERS = [
    (1, "J. Smit", "Regio Noord", False, True),
    (2, "F. El Amrani", "Regio Midden", False, True),
    # Out on today's round, so not available for a new assignment.
    (3, "K. Mulder", "Regio Zuid", False, False),
    (4, "Spoedkoerier Express Gelderland", None, True, True),
    (5, "Spoedkoerier Maas en Waal", None, True, True),
]
REGION_COURIER = {"Noord": 1, "Midden": 2, "Zuid": 3}


class Customer:
    pass


customers = []
names = rng.sample(PHARMACY_NAMES, len(PHARMACY_NAMES))
towns = [(region, town) for region, entries in TOWNS.items() for town in entries]
# (tier, number of customers). Tier decides order frequency and size.
PROFILE = [(15, 12), (10, 19), (5, 20), ("new", 4)]
for tier, count in PROFILE:
    for _ in range(count):
        c = Customer()
        c.id = ids.next("klant")
        region, (town, area, prefix) = towns[(c.id * 7) % len(towns)]
        c.region, c.town = region, town
        stad = rng.random() < 0.12
        c.name = f"Stadsapotheek {town}" if stad and not any(
            x.name == f"Stadsapotheek {town}" for x in customers) else f"Apotheek {names.pop()}"
        c.phone, c.contact = phone(area), person()
        c.delivery_text = street_address(town, prefix)
        c.delivery_id = new_address(c.delivery_text)
        if rng.random() < 0.35:
            c.billing_text = f"Postbus {rng.randint(10, 9999)}, {prefix}{rng.randint(10, 99)} AA {town}"
            c.billing_id = new_address(c.billing_text)
        else:
            c.billing_text, c.billing_id = c.delivery_text, c.delivery_id
        c.old_delivery_id = None
        c.active, c.one_time_promised = True, False
        c.start_k, c.end_k = HISTORY_WEEKS - rng.randint(0, 3), 1
        c.phase = rng.randint(0, 4)
        if tier == "new":
            c.tier, c.freq, c.lines = 5, 2, (2, 4)
            c.one_time_promised = True
        elif tier == 15:
            c.tier, c.freq, c.lines = 15, 1, (3, 7)
        elif tier == 10:
            c.tier, c.freq, c.lines = 10, 2, (3, 6)
        else:
            c.tier, c.freq, c.lines = 5, rng.randint(3, 5), (2, 4)
        c.size = {15: 1.0, 10: 0.95, 5: 0.75}[c.tier]
        weights = [p.popularity ** 2 for p in sellable]
        c.basket = list(dict.fromkeys(rng.choices(sellable, weights, k=rng.randint(10, 22))))
        c.basket += [by_name[n] for n in REMOVED_PRODUCTS if rng.random() < 0.4]
        customers.append(c)

big = [c for c in customers if c.tier == 15]
medium = [c for c in customers if c.tier == 10]
small = [c for c in customers if c.tier == 5 and not c.one_time_promised]
new = [c for c in customers if c.one_time_promised]
# Converted prospects joined later. The third places its first order today,
# the last one has not ordered yet.
for c, start in zip(new, (40, 20, None, None)):
    c.start_k = start
first_timer = new[2]
# Two pharmacies closed: deactivated, history kept.
small[0].active, small[0].end_k = False, 30
small[1].active, small[1].end_k = False, 12
# Debt collection: unpaid invoices of weeks 9 and 10, no orders since.
collection_customer = small[2]
collection_customer.end_k = 9
# A payment plan for one invoice; the customer keeps ordering.
plan_customer = medium[3]
# Moved: orders before week 30 used the old delivery address.
for c in (big[2], medium[5]):
    c.old_delivery_id = new_address(street_address(c.town, dict(
        (t, p) for r in TOWNS.values() for t, _, p in r)[c.town]))


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

class Order:
    pass


orders = []
rides = {}
ride_rows = []
deliveries = []
attempts = []


def ride(courier_id, day, urgent=False):
    """Regular rounds are shared per courier and day; every rush order gets its own ride."""
    key = (courier_id, day.base, day.offset)
    if urgent or key not in rides:
        ride_id = ids.next("rit")
        ride_rows.append((ride_id, courier_id, day))
        if not urgent:
            rides[key] = ride_id
        return ride_id
    return rides[key]


def order_lines(c, old_prices, count=None, exclude=()):
    pool = [p for p in c.basket if p.in_assortment or old_prices]
    pool = [p for p in pool if p.name not in exclude]
    count = count or rng.randint(*c.lines)
    chosen = rng.sample(pool, min(count, len(pool)))
    lines = []
    for p in sorted(chosen, key=lambda x: x.id):
        factor = rng.choices([1, 2, 3, 4], [50, 30, 14, 6])[0]
        quantity = max(p.min_order, round(p.min_order * factor * c.size)) if p.price < 150 else 1
        lines.append({"product": p, "qty": quantity, "price": p.old_price if old_prices else p.price,
                      "short": None})
    return lines


def new_order(c, ordered_at, wanted, part, urgent, status, lines, delivery_address=None):
    o = Order()
    o.customer, o.ordered_at, o.wanted, o.part = c, ordered_at, wanted, part
    o.urgent, o.status, o.lines = urgent, status, lines
    o.address_id = delivery_address or c.delivery_id
    o.boxes, o.extra_cost, o.extra_note = 0, Decimal("0.00"), None
    o.reservations, o.suborders = {}, []
    o.delivery = None
    o.sort = (ordered_at[0].key(), ordered_at[1])
    orders.append(o)
    return o


def boxes_for(lines):
    return max(1, round(sum(line["qty"] for line in lines) / 25))


def deliver(o, day, minutes, courier_id=None, urgent=False, results=("afgeleverd",), retry=None):
    """Create the delivery with its attempts. Results None means not visited yet."""
    courier_id = courier_id or REGION_COURIER[o.customer.region]
    ride_id = ride(courier_id, day, urgent)
    o.delivery = {"id": None, "day": day, "attempts": [], "lines": [], "invoice": None}
    times = [minutes] + ([retry] if len(results) > 1 else [])
    for number, (result, start) in enumerate(zip(results, times), 1):
        # As in the application: a scheduled first visit has no signature yet,
        # a scheduled return visit is stored as not signed.
        signed = result == "afgeleverd" if result else (False if number == 2 else None)
        o.delivery["attempts"].append((number, ride_id, hhmm(start), result, signed))
    if results[-1] == "afgeleverd":
        o.delivery["lines"] = [(line["product"], line["qty"]) for line in o.lines]
    deliveries.append(o)


def slot(part):
    return rng.randint(510, 705) if part == "ochtend" else rng.randint(750, 1005)


def suborders(o, done=True, open_aisles=(), bins=True, bin_missing=()):
    """Split the order by aisle, like RobotOrderRepository.generate()."""
    per_aisle = defaultdict(list)
    for line in o.lines:
        if line["short"]:
            continue
        per_aisle[line["product"].aisle].append((line["product"], line["qty"]))
    for aisle in sorted(per_aisle):
        finished = done and aisle not in open_aisles
        has_bin = bins and aisle not in bin_missing
        o.suborders.append({"aisle": aisle, "lines": per_aisle[aisle], "done": finished,
                            "bins": (2 if rng.random() < 0.15 else 1) if has_bin else 0})
        if not finished:
            for p, qty in per_aisle[aisle]:
                o.reservations[p] = o.reservations.get(p, 0) + qty


# History: weeks 64..1 before the current week, on working days.
for c in customers:
    if c.start_k is None:
        continue
    for k in range(c.start_k, c.end_k - 1, -1):
        if k == c.start_k:
            count = 1
        elif c.freq == 1:
            count = 0 if rng.random() < 0.05 else 1 + (rng.random() < 0.3)
        elif (k + c.phase) % c.freq == 0:
            count = 0 if rng.random() < 0.1 else 1
        else:
            count = 1 if rng.random() < 0.06 else 0
        # The invoices that went to a payment plan and to debt collection.
        if (c is plan_customer and k == 7) or (c is collection_customer and k in (9, 10)):
            count = max(count, 1)
        for weekday in sorted(rng.sample(range(5), count)):
            day = Day("@m", -7 * k + weekday)
            urgent = rng.random() < 0.03 and k > 1
            part = "ochtend" if rng.random() < 0.6 else "middag"
            if urgent:
                start = rng.randint(480, 840)
                ordered = (day, hhmm(start))
                planned = start + rng.randint(60, 170)
                part = "ochtend" if planned < 720 else "middag"
            else:
                back = (3 if weekday == 0 else 1) + (2 if rng.random() < 0.15 else 0)
                ordered = (day.plus(-back), hhmm(rng.randint(480, 955)))
                planned = slot(part)
            address = c.old_delivery_id if c.old_delivery_id and k > 30 else None
            o = new_order(c, ordered, day, part, urgent,
                          "gefactureerd" if k > 1 else "afgeleverd",
                          order_lines(c, old_prices=k > 26), address)
            o.week = k
            o.boxes = boxes_for(o.lines)
            if k <= ROBOT_LIVE_WEEKS:
                suborders(o)
            if urgent:
                courier = rng.choice((4, 5)) if rng.random() < 0.4 else None
                deliver(o, day, planned, courier, urgent=True)
            elif rng.random() < 0.04:
                deliver(o, day, planned, results=("niet aanwezig", "afgeleverd"),
                        retry=min(planned + rng.randint(120, 240), 1060))
            else:
                deliver(o, day, planned)

# The current week. @t is today, @vw the previous and @nw the next working day.
T, VW, NW, NW2 = Day("@t"), Day("@vw"), Day("@nw"), Day("@nw2")
pipeline_customers = [c for c in customers if c.active and c is not collection_customer
                      and c.start_k is not None]
pipeline_weights = [{15: 3, 10: 2, 5: 1}[c.tier] for c in pipeline_customers]


def pipe(status, wanted, part=None, urgent=False, ordered=None, exclude=OUT_OF_STOCK, lines=None):
    c = rng.choices(pipeline_customers, pipeline_weights)[0]
    part = part or ("ochtend" if rng.random() < 0.6 else "middag")
    ordered = ordered or (VW, hhmm(rng.randint(480, 955)))
    return new_order(c, ordered, wanted, part, urgent, status,
                     lines or order_lines(c, old_prices=False, exclude=exclude))


# Two failed visits last Friday; sales agreed a new day with extra costs.
o = pipe("verstuurd", NW, ordered=(Day("@m", -4), "11:20"))
o.week, o.boxes = 1, boxes_for(o.lines)
suborders(o)
deliver(o, Day("@m", -3), 600, results=("niet aanwezig", "niet aanwezig"), retry=900)
o.extra_cost = Decimal("17.50")
o.extra_note = "Twee keer niemand aanwezig op de afgesproken dag, extra rit naar de apotheek."
# Delivered and signed this morning.
for _ in range(6):
    o = pipe("afgeleverd", T, part="ochtend")
    o.boxes = boxes_for(o.lines)
    suborders(o)
    deliver(o, T, rng.randint(510, 630))
# Rush order delivered this morning by its own ride.
o = pipe("afgeleverd", T, part="ochtend", urgent=True, ordered=(T, "07:55"))
o.boxes = 1
suborders(o)
deliver(o, T, 600, urgent=True)
# On today's rounds, not visited yet.
for _ in range(9):
    o = pipe("verstuurd", T)
    o.boxes = boxes_for(o.lines)
    suborders(o)
    deliver(o, T, rng.randint(660, 990), results=(None,))
# Nobody home at the first visit; the courier comes back later today.
for first, second in ((555, 870), (630, 930)):
    o = pipe("verstuurd", T, part="ochtend")
    o.boxes = boxes_for(o.lines)
    suborders(o)
    deliver(o, T, first, results=("niet aanwezig", None), retry=second)
# Nobody home twice today: back in the distribution corner, sales calls the customer.
o = pipe("niet afgeleverd", T, part="ochtend")
o.boxes = boxes_for(o.lines)
suborders(o)
deliver(o, T, 585, results=("niet aanwezig", "niet aanwezig"), retry=840)
# Rush order with an external rush courier, on its way.
o = pipe("verstuurd", T, part="middag", urgent=True, ordered=(T, "11:40"), lines=None)
o.boxes = 1
suborders(o)
deliver(o, T, 840, courier_id=4, urgent=True, results=(None,))
# Planned for the next two working days.
for wanted, count in ((NW, 7), (NW2, 4)):
    for _ in range(count):
        o = pipe("verstuurd", wanted)
        o.boxes = boxes_for(o.lines)
        suborders(o)
        deliver(o, wanted, slot(o.part), results=(None,))
# Released, still to be scheduled.
for _ in range(4):
    o = pipe("verstuurd", NW, ordered=(T, hhmm(rng.randint(480, 600))))
    o.boxes = boxes_for(o.lines)
    suborders(o)
# Packed, still to be released.
for _ in range(3):
    o = pipe("ingepakt", NW, ordered=(T, hhmm(rng.randint(480, 660))))
    o.boxes = boxes_for(o.lines)
    suborders(o)
# Picked completely, still to be packed.
for _ in range(3):
    o = pipe("wordt verzameld", NW, ordered=(T, hhmm(rng.randint(480, 720))))
    suborders(o)
# Robots are still collecting: some sub-orders open, some without a bin yet.
for _ in range(6):
    o = pipe("wordt verzameld", NW, ordered=(T, hhmm(rng.randint(600, 840))))
    aisles = sorted({line["product"].aisle for line in o.lines})
    open_aisles = set(rng.sample(aisles, max(1, len(aisles) // 2)))
    missing = {a for a in open_aisles if rng.random() < 0.5}
    suborders(o, open_aisles=open_aisles, bin_missing=missing)
# Backorder as RobotOrderRepository.complete() records it: the robot found fewer
# boxes than assigned, that product is now out of stock and the customer wants the rest.
o = pipe("backorder", NW, ordered=(VW, hhmm(rng.randint(540, 780))))
short_product = by_name[sorted(OUT_OF_STOCK)[0]]
o.lines.append({"product": short_product, "qty": short_product.min_order * 3,
                "price": short_product.price, "short": True})
o.lines.sort(key=lambda line: line["product"].id)
suborders(o)
picked = (short_product, short_product.min_order * 2)
same_aisle = [sub for sub in o.suborders if sub["aisle"] == short_product.aisle]
if same_aisle:
    same_aisle[0]["lines"].append(picked)
else:
    o.suborders.append({"aisle": short_product.aisle, "lines": [picked], "done": True, "bins": 1})
    o.suborders.sort(key=lambda sub: sub["aisle"])
# Backorder as TelephoneOrderRepository.approve() records it when nothing is in stock.
o = pipe("backorder", NW2, ordered=(T, hhmm(rng.randint(540, 780))),
         lines=[{"product": by_name[name], "qty": by_name[name].min_order * 2,
                 "price": by_name[name].price, "short": True} for name in sorted(OUT_OF_STOCK)])
# Entered with reserved stock, not yet split over the robots.
for _ in range(3):
    o = pipe("nieuw", NW2, ordered=(T, hhmm(rng.randint(780, 900))))
    for line in o.lines:
        o.reservations[line["product"]] = line["qty"]
# The first order of a converted prospect: the 10% one-time discount applies.
o = new_order(first_timer, (T, "09:05"), NW, "middag", False, "wordt verzameld",
              order_lines(first_timer, old_prices=False, exclude=OUT_OF_STOCK))
suborders(o, open_aisles={o.lines[0]["product"].aisle})

orders.sort(key=lambda x: x.sort)
for o in orders:
    o.id = ids.next("bestelling")
first_order = {}
for o in orders:
    first_order.setdefault(o.customer.id, o)


# ---------------------------------------------------------------------------
# Warehouse stock, derived from demand and the open picking work
# ---------------------------------------------------------------------------

demand = defaultdict(int)
for o in orders:
    if getattr(o, "week", 99) <= 8:
        for line in o.lines:
            demand[line["product"]] += line["qty"]
reserved = defaultdict(int)
open_planned = defaultdict(int)
for o in orders:
    for p, qty in o.reservations.items():
        reserved[p] += qty
    for sub in o.suborders:
        if not sub["done"]:
            for p, qty in sub["lines"]:
                open_planned[p] += qty

low_stock = set(rng.sample([p for p in sellable if p.name not in OUT_OF_STOCK
                            and p.popularity >= 2 and p.reorderable], 12))
shelves = {}
next_shelf = defaultdict(lambda: 1)


def place(aisle, p, amount):
    shelf = next_shelf[aisle]
    next_shelf[aisle] += 1 + (rng.random() < 0.25)
    if shelf > 40:
        raise SystemExit(f"Aisle {aisle} has more than 40 shelves in use.")
    shelves[(aisle, shelf)] = (p, amount)


for p in products:
    weekly = max(1, demand[p] // 8)
    p.minimum = max(p.min_order * 2, round(weekly * 2.5))
    if p.name in OUT_OF_STOCK:
        stock = 0
    elif not p.in_assortment:
        stock = 0
    elif p in low_stock:
        stock = max(reserved[p] + rng.randint(0, 4), round(p.minimum * rng.uniform(0.2, 0.8)))
    else:
        stock = reserved[p] + round(p.minimum * rng.uniform(1.4, 3.2))
    if p in low_stock:
        p.minimum = max(p.minimum, stock + rng.randint(1, 10))
    if not p.in_assortment:
        continue
    second = SECOND_AISLE.get(p.name)
    if second and stock > reserved[p] + 20:
        # The primary shelf keeps everything the open sub-orders still have to collect.
        extra = (stock - reserved[p]) // 3
        place(p.aisle, p, stock - extra)
        place(second, p, extra)
    elif p.popularity >= 4 and stock > reserved[p] + 20:
        part = stock // 2
        place(p.aisle, p, max(part, open_planned[p]))
        place(p.aisle, p, stock - max(part, open_planned[p]))
    else:
        place(p.aisle, p, stock)
    p.stock = stock


# ---------------------------------------------------------------------------
# Deliveries, invoices and payments
# ---------------------------------------------------------------------------

for o in sorted(deliveries, key=lambda x: (x.delivery["day"].key(), x.id)):
    o.delivery["id"] = ids.next("levering")

invoices = []
weeks = defaultdict(list)
for o in orders:
    if o.status == "gefactureerd":
        weeks[(o.week, o.customer.id)].append(o)
for (k, customer_id), week_orders in sorted(weeks.items(), key=lambda item: (-item[0][0], item[0][1])):
    c = week_orders[0].customer
    payload = []
    for o in sorted(week_orders, key=lambda x: (x.sort, x.id)):
        net = sum((line["price"] * line["qty"] for line in o.lines), Decimal("0"))
        payload.append({
            "order_id": o.id,
            "first_order": first_order[c.id] is o,
            "order_total": euro(net * Decimal("1.09")),
            "customer_discount_percentage": Decimal(c.tier),
            "lines": [{"quantity": line["qty"], "unit_price": line["price"]} for line in o.lines],
        })
    amounts = Invoice(c.id, "", None).createWeeklyInvoiceForOrders(
        c.name, c.billing_text, payload, 0)
    invoices.append({"customer": c, "week": k, "orders": week_orders, "amounts": amounts,
                     "date": -7 * (k - 1)})
for invoice in invoices:
    invoice["id"] = ids.next("factuur")
    for o in invoice["orders"]:
        o.delivery["invoice"] = invoice["id"]

reminders = []
plan_invoice = next(i for i in invoices if i["customer"] is plan_customer and i["week"] == 7)
collection_invoices = [i for i in invoices if i["customer"] is collection_customer and i["week"] in (9, 10)]
# Still open in every reminder stage: a week (first reminder), two weeks
# (second reminder) and three weeks (propose a payment plan).
forced_open = []
for week, count in ((2, 2), (3, 1), (4, 2)):
    candidates = [i for i in invoices if i["week"] == week
                  and i["customer"] not in (plan_customer, collection_customer)]
    forced_open += rng.sample(candidates, count)
for invoice in invoices:
    issued = invoice["date"]
    invoice["plan"], invoice["collection"] = None, False
    if invoice is plan_invoice or invoice in collection_invoices or any(invoice is i for i in forced_open):
        delay = None
    else:
        r = rng.random()
        delay = (rng.randint(1, 6) if r < 0.82 else rng.randint(8, 13) if r < 0.94
                 else rng.randint(15, 20) if r < 0.985 else rng.randint(30, 45))
    paid = None if delay is None or issued + delay > 0 else issued + delay
    invoice["paid"] = paid
    # Reminders go out a week and two weeks after the invoice date, while unpaid.
    # Those due this week are left for the administration to send.
    for sequence in (1, 2):
        sent = issued + 7 * sequence
        if sent < 0 and (paid is None or paid > sent):
            reminders.append((invoice["id"], sequence, sent))
    contact = issued + 21 + rng.randint(1, 2)
    if (paid is None or paid > contact) and contact < 0:
        invoice["plan"] = invoice not in collection_invoices
        invoice["collection"] = invoice in collection_invoices


# ---------------------------------------------------------------------------
# Acquisition
# ---------------------------------------------------------------------------

prospects = []


def prospect(name, town, visits, customer=None, closed=False):
    region = next(r for r, entries in TOWNS.items() if any(t == town for t, _, _ in entries))
    area, prefix = next((a, p) for t, a, p in TOWNS[region] if t == town)
    contact = person()
    prospects.append({
        "id": ids.next("prospect"), "name": name, "contact": contact,
        "details": f"{phone(area)}, {contact.split(' ', 1)[1].replace(' ', '').lower()}@{name.lower().replace(' ', '')}.example",
        "address_id": new_address(street_address(town, prefix)), "customer": customer,
        "closed": closed or customer is not None, "visits": visits,
    })


for c in new:
    if c is first_timer:
        visits = [-45]
    elif c.start_k is None:
        visits = [-38]
    else:
        visits = [-7 * c.start_k - 40]
    prospect(c.name, c.town, visits, customer=c)
for name, town, visits in (
    ("Apotheek De Kroon", "Arnhem", [-84]), ("Apotheek Het Wiel", "Ede", [-63]),
    ("Apotheek De Rozenhof", "Tiel", [-52]), ("Apotheek Maasdal", "Oss", [-45]),
    ("Apotheek De Lier", "Nijmegen", [-120, -41]), ("Apotheek Het Hart", "Uden", [-36]),
    ("Apotheek Ter Weide", "Wageningen", [-17]), ("Apotheek De Ooij", "Beuningen", [-9]),
    ("Apotheek Kerkzicht", "Boxmeer", [-70, -12]), ("Apotheek De Wiel", "Velp", [-3]),
):
    prospect(name, town, visits)
for name, town, visits in (("Apotheek Het Fort", "Zevenaar", [-150]),
                           ("Apotheek De Heuvel", "Gennep", [-98]),
                           ("Apotheek Het Water", "Druten", [-77])):
    prospect(name, town, visits, closed=True)
visits = []
for p in prospects:
    for day in p["visits"]:
        visits.append((ids.next("bezoek"), p["id"], Day("@m", day)))


# ---------------------------------------------------------------------------
# Purchasing
# ---------------------------------------------------------------------------

purchase_orders = []
purchase_lines = []
for index in range(3):
    supplier = suppliers[index * 3]
    purchase_orders.append((ids.next("inkoop"), supplier["id"], None, None))
    for product_id in rng.sample(offered_by[supplier["id"]], min(2, len(offered_by[supplier["id"]]))):
        purchase_lines.append((ids.counters["inkoop"], product_id, rng.randint(2, 6) * 10))
for days_ago in sorted(rng.sample(range(2, 80), 26), reverse=True):
    supplier = rng.choice(suppliers)
    order_id = ids.next("inkoop")
    purchase_orders.append((order_id, supplier["id"],
                            at(Day("@m", -days_ago), hhmm(rng.randint(480, 990))), "besteld"))
    candidates = offered_by[supplier["id"]]
    for product_id in rng.sample(candidates, min(len(candidates), rng.randint(1, 4))):
        p = products[product_id - 1]
        purchase_lines.append((order_id, product_id, max(10, p.minimum * rng.randint(2, 4))))
# Reorders for the products that are out of stock or below the minimum.
for p in sorted(low_stock | {by_name[n] for n in OUT_OF_STOCK}, key=lambda x: x.id)[:8]:
    supplier_id = min((price, s) for s, pid, price in offers if pid == p.id)[1]
    order_id = ids.next("inkoop")
    purchase_orders.append((order_id, supplier_id, at(Day("@m", -rng.randint(0, 5)), "10:15"), "besteld"))
    purchase_lines.append((order_id, p.id, max(20, p.minimum * 3)))

purchase_invoices = []
for days_ago in sorted(rng.sample(range(3, 420), 48), reverse=True):
    supplier = rng.choice(suppliers)
    paid = -days_ago + rng.randint(10, 30)
    purchase_invoices.append((ids.next("inkoopfactuur"), supplier["id"], Day("@m", -days_ago),
                              money(rng.uniform(450, 9500)),
                              Day("@m", paid) if paid < 0 and rng.random() < 0.95 else None))


# ---------------------------------------------------------------------------
# Write seed.sql
# ---------------------------------------------------------------------------

sql = Script()
sql.line("-- =========================================")
sql.line("-- SEED DATA (demo)")
sql.line("-- Generated by generate_seed.py; change that script, not this file.")
sql.line("-- Fictional data for every screen: 55 pharmacies, a hundred medicines,")
sql.line(f"-- {HISTORY_WEEKS} weeks of delivered and invoiced orders, today's delivery rounds,")
sql.line("-- robots at work, open invoices in every reminder stage and acquisition follow-ups.")
sql.line("--")
sql.line("-- Run after schema.sql (and the migrations). It EMPTIES every table except")
sql.line("-- OrderStatus first, so it can be run again to reset the demo.")
sql.line("-- Dates follow the day you run it: @m is Monday of this week, @t is today.")
sql.line("-- =========================================")
sql.line()
sql.line("START TRANSACTION;")
sql.line()
sql.line("SET @t = CURDATE();")
sql.line("SET @m = @t - INTERVAL WEEKDAY(@t) DAY;")
sql.line("SET @y = YEAR(@t);")
sql.line("-- Previous and next working days, for orders around today.")
sql.line("SET @vw = @t - INTERVAL (CASE WEEKDAY(@t) WHEN 0 THEN 3 WHEN 6 THEN 2 ELSE 1 END) DAY;")
sql.line("SET @nw = @t + INTERVAL (CASE WEEKDAY(@t) WHEN 4 THEN 3 WHEN 5 THEN 2 ELSE 1 END) DAY;")
sql.line("SET @nw2 = @nw + INTERVAL (CASE WEEKDAY(@nw) WHEN 4 THEN 3 ELSE 1 END) DAY;")

sql.section("LEEGMAKEN", "Child tables first, because of the foreign keys.")
for table in ("Betalingsherinnering", "Leveringregel", "Leverpoging", "Levering", "Rit", "Koerier",
              "Verzamelbak", "Deelorderregel", "Deelorder", "Robot", "Voorraadreservering",
              "Bestelregel", "Bestelling", "Factuur", "Klantkorting", "Acquisitiebezoek",
              "PotentieleKlant", "Inkoopbestelregel", "Inkoopbestelling", "Inkoopfactuur",
              "LeveranciersAanbod", "Leverancier", "Magazijnlocatie", "ProductWerkzameStof",
              "Product", "Klant", "Adres"):
    sql.line(f"DELETE FROM {table};")

sql.section("ADRESSEN")
sql.insert("Adres", ("adres_id", "adres"), addresses)

sql.section("KLANTEN",
            "Tiers by revenue: 12 customers at 15%, 19 at 10%, the rest at 5%.",
            "Two closed pharmacies are inactive; one customer is with the debt collection agency.",
            "Four came from acquisition with the one-time discount; the last has not ordered yet.")
sql.insert("Klant", ("klant_id", "bedrijfsnaam", "telefoonnummer", "contactpersoon", "actief",
                     "eenmalige_korting_toegezegd", "afleveradres_id", "betaaladres_id"),
           [(c.id, c.name, c.phone, c.contact, c.active, c.one_time_promised, c.delivery_id,
             c.billing_id) for c in customers])

sql.section("ACQUISITIE",
            "Prospects last visited over a month ago appear in the follow-up list.")
sql.insert("PotentieleKlant", ("potentiele_klant_id", "bedrijfsnaam", "contactpersoon",
                               "contactgegevens", "adres_id", "klant_id", "opvolging_afgesloten"),
           [(p["id"], p["name"], p["contact"], p["details"], p["address_id"],
             p["customer"].id if p["customer"] else None, p["closed"]) for p in prospects])
sql.insert("Acquisitiebezoek", ("bezoek_id", "potentiele_klant_id", "bezoekdatum"), visits)

sql.section("PRODUCTEN",
            "Two products are off the assortment, two can no longer be reordered,",
            "two are out of stock and twelve are below their minimum stock.")
sql.insert("Product", ("product_id", "artikelnummer", "bestelcode", "productnaam",
                       "prijs_per_grootverpakking", "verpakkingssoort", "aantal_detailverpakkingen",
                       "korte_omschrijving", "lange_omschrijving", "minimale_bestelhoeveelheid",
                       "minimumvoorraad", "intern_bestelbaar", "in_assortiment"),
           [(p.id, p.number, p.order_code, p.name, p.price, p.packaging, p.packs, p.short, p.long,
             p.min_order, p.minimum, p.reorderable, p.in_assortment) for p in products])
sql.insert("ProductWerkzameStof", ("product_id", "stofnaam", "hoeveelheid"),
           [(p.id, name, amount) for p in products for name, amount in p.substances])

sql.section("MAGAZIJN", "One robot per aisle, forty shelves per aisle.")
sql.insert("Robot", ("robot_id", "gang"), [(i + 1, aisle) for i, aisle in enumerate("ABCDEFGH")])
location_rows = []
for aisle in "ABCDEFGH":
    for shelf in range(1, 41):
        p, amount = shelves.get((aisle, shelf), (None, 0))
        location_rows.append((aisle, shelf, p.id if p else None, amount))
sql.insert("Magazijnlocatie", ("gang", "schapnummer", "product_id", "aantal"), location_rows)

sql.section("LEVERANCIERS EN INKOOP",
            "Receiving stock is outside the case, so purchase orders stay 'besteld'.",
            "The first three purchase orders are legacy rows without date and status.")
sql.insert("Leverancier", ("leverancier_id", "naam", "adres_id", "contactpersoon", "telefoonnummer",
                           "internetadres"),
           [(s["id"], s["name"], s["address_id"], s["contact"], s["phone"], s["web"]) for s in suppliers])
sql.insert("LeveranciersAanbod", ("leverancier_id", "product_id", "inkoopprijs"), offers)
sql.insert("Inkoopbestelling", ("inkoopbestelling_id", "leverancier_id", "besteld_op", "status_naam"),
           purchase_orders)
sql.insert("Inkoopbestelregel", ("inkoopbestelling_id", "product_id", "aantal"), purchase_lines)
sql.insert("Inkoopfactuur", ("inkoopfactuur_id", "leverancier_id", "factuurdatum", "bedrag", "betaald_op"),
           purchase_invoices)

sql.section("BESTELLINGEN",
            "Weeks 64 to 2 are invoiced, last week is delivered but not yet invoiced,",
            "and this week every status from 'nieuw' to 'niet afgeleverd' is present.")
sql.insert("Bestelling", ("bestelling_id", "klant_id", "afleveradres_id", "betaaladres_id", "besteld_op",
                          "gewenste_leverdatum", "dagdeel", "spoed", "status_naam", "aantal_verhuisdozen",
                          "eenmalige_korting_toegepast", "extra_bezorgkosten",
                          "toelichting_extra_bezorgkosten"),
           [(o.id, o.customer.id, o.address_id, o.customer.billing_id, at(*o.ordered_at), o.wanted,
             o.part, o.urgent, o.status, o.boxes, first_order[o.customer.id] is o, o.extra_cost,
             o.extra_note) for o in orders])
sql.insert("Bestelregel", ("bestelling_id", "product_id", "aantal", "prijs_per_eenheid", "afnemen_bij_tekort"),
           [(o.id, line["product"].id, line["qty"], line["price"], line["short"])
            for o in orders for line in o.lines])

tiers = defaultdict(list)
for c in customers:
    tiers[c.tier].append(str(c.id))
sql.line()
sql.line("-- The rate of every year a customer ordered in; fixed per customer in this demo.")
sql.line("INSERT INTO Klantkorting (klant_id, kalenderjaar, percentage)")
sql.line("SELECT b.klant_id, j.jaar,")
sql.line(f"       CASE WHEN b.klant_id IN ({', '.join(tiers[15])}) THEN 15")
sql.line(f"            WHEN b.klant_id IN ({', '.join(tiers[10])}) THEN 10")
sql.line("            ELSE 5 END")
sql.line("FROM (SELECT klant_id, YEAR(MIN(besteld_op)) AS vanaf FROM Bestelling GROUP BY klant_id) AS b")
sql.line("JOIN (SELECT @y - 2 AS jaar UNION ALL SELECT @y - 1 UNION ALL SELECT @y) AS j")
sql.line("  ON j.jaar >= b.vanaf;")

sql.insert("Voorraadreservering", ("bestelling_id", "product_id", "aantal"),
           [(o.id, p.id, qty) for o in orders for p, qty in sorted(o.reservations.items(), key=lambda x: x[0].id)])

sql.section("ORDERPICKING",
            "Robots went live last week: older orders have no sub-orders.",
            "Open sub-orders still hold their reservation; some wait for their first bin.")
suborder_rows, suborder_lines, bin_rows = [], [], []
for o in orders:
    for sub in o.suborders:
        sub_id = ids.next("deelorder")
        suborder_rows.append((sub_id, o.id, "ABCDEFGH".index(sub["aisle"]) + 1, sub["done"]))
        for p, qty in sub["lines"]:
            suborder_lines.append((sub_id, p.id, qty))
        for n in range(sub["bins"]):
            bin_rows.append((f"VB-{sub_id:05d}{'-' + 'AB'[n] if sub['bins'] > 1 else ''}", sub_id))
sql.insert("Deelorder", ("deelorder_id", "bestelling_id", "robot_id", "afgerond"), suborder_rows)
sql.insert("Deelorderregel", ("deelorder_id", "product_id", "aantal"), suborder_lines)
sql.insert("Verzamelbak", ("unieke_code", "deelorder_id"), bin_rows)

sql.section("DISTRIBUTIE",
            "Three own couriers, one per region, and two external rush couriers.")
sql.insert("Koerier", ("koerier_id", "naam", "regio", "extern", "beschikbaar"), COURIERS)
sql.insert("Rit", ("rit_id", "koerier_id", "ritdatum"), ride_rows)
delivered = sorted(deliveries, key=lambda x: x.delivery["id"])
sql.insert("Levering", ("levering_id", "bestelling_id"), [(o.delivery["id"], o.id) for o in delivered])
sql.insert("Leverpoging", ("levering_id", "pogingnummer", "rit_id", "geplande_tijd", "resultaat",
                           "ontvangst_getekend"),
           [(o.delivery["id"], number, ride_id, Raw(f"'{start}:00'"), result, signed)
            for o in delivered for number, ride_id, start, result, signed in o.delivery["attempts"]])

sql.section("ADMINISTRATIE",
            "One invoice per customer per week, issued the Monday after. Amounts are the",
            "snapshot the application stores, computed with domain.business.Invoice.")
sql.insert("Factuur", ("factuur_id", "klant_id", "factuurdatum", "week_start", "afzenderadres",
                       "factuuradres", "betaald_op", "betalingsregeling_geaccepteerd",
                       "incasso_ingeschakeld", "bedrag_excl_btw", "btw_bedrag", "bestellingskorting",
                       "eenmalige_korting", "klantenkorting"),
           [(i["id"], i["customer"].id, Day("@m", i["date"]), Day("@m", -7 * i["week"]),
             "DEMOGEGEVENS: afzenderadres Timaflu", i["customer"].billing_text,
             Day("@m", i["paid"]) if i["paid"] is not None else None,
             False if i["collection"] else i["plan"], i["collection"],
             i["amounts"]["total_ex_vat"], i["amounts"]["vat_9_percent"], i["amounts"]["order_discount"],
             i["amounts"]["first_order_discount"], i["amounts"]["customer_discount"]) for i in invoices])
sql.insert("Leveringregel", ("levering_id", "product_id", "aantal_geleverd", "factuur_id"),
           [(o.delivery["id"], p.id, qty, o.delivery["invoice"])
            for o in delivered for p, qty in sorted(o.delivery["lines"], key=lambda x: x[0].id)])
sql.insert("Betalingsherinnering", ("factuur_id", "volgnummer", "verstuurd_op"),
           [(invoice_id, sequence, Day("@m", sent)) for invoice_id, sequence, sent in reminders])

sql.line()
sql.line("COMMIT;")
OUT.write_text(sql.text(), encoding="utf-8", newline="\n")

counts = {
    "klanten": len(customers), "producten": len(products), "bestellingen": len(orders),
    "bestelregels": sum(len(o.lines) for o in orders), "leveringen": len(deliveries),
    "ritten": len(ride_rows), "facturen": len(invoices), "herinneringen": len(reminders),
    "deelorders": len(suborder_rows), "verzamelbakken": len(bin_rows),
}
print(", ".join(f"{k}: {v}" for k, v in counts.items()))
# The tier must match a year of revenue (Tabel 1): 15% from EUR 20.000, 10% from EUR 10.000.
revenue = defaultdict(Decimal)
for i in invoices:
    if i["week"] <= 52:
        revenue[i["customer"]] += i["amounts"]["total"]
for tier in (15, 10, 5):
    totals = [revenue[c] for c in customers if c.tier == tier and c.active
              and not c.one_time_promised and c is not collection_customer]
    print(f"tier {tier}%: invoiced per customer over 52 weeks EUR {min(totals):.0f} to {max(totals):.0f}")
print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")
