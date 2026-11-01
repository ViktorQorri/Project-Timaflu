"""AD01-AD28: verify requirement-to-design-to-code-to-test references.

This guards file and entity traceability only; it does not claim that all
database-backed acceptance scenarios were run against MySQL.
"""
import csv
import re
from pathlib import Path
from unittest import TestCase

ROOT=Path(__file__).resolve().parents[2]
MATRIX=ROOT/"Documentation/Architecture/traceability.csv"

class TraceabilityMatrixTests(TestCase):
    @classmethod
    def setUpClass(cls):
        with MATRIX.open(encoding="utf-8-sig",newline="") as file:
            cls.rows=list(csv.DictReader(file,delimiter=";"))
        cls.schema=(ROOT/"code/database/schema.sql").read_text(encoding="utf-8-sig")
        cls.tables=set(re.findall(r"CREATE TABLE\\s+(\\w+)",cls.schema,re.I))
        cls.usecases=(ROOT/"Documentation/Architecture/uml/src/use_cases/informatiesysteem.puml").read_text(encoding="utf-8")

    def test_28_unique_requirements_are_mapped(self):
        self.assertEqual([row["eis_id"] for row in self.rows],
                         [f"AD{i:02}" for i in range(1,29)])
        self.assertEqual({row["proces"] for row in self.rows},
            {"Verkoop","Inkoop","Orderpicking","Distributie","Administratie","Acquisitie"})

    def test_each_requirement_links_to_existing_sources(self):
        for row in self.rows:
            with self.subTest(ad=row["eis_id"]):
                for column in ("casusbron","activity_diagram","schermontwerp",
                               "backend","testbestand"):
                    rel=row[column]
                    self.assertFalse(Path(rel).is_absolute(),(row["eis_id"],column))
                    self.assertTrue((ROOT/rel).is_file(),(row["eis_id"],column,rel))
                for rel in row["usecase_diagram"].split("|"):
                    self.assertTrue((ROOT/rel).is_file(),(row["eis_id"],rel))
                if row["sequence_diagram"]:
                    self.assertTrue((ROOT/row["sequence_diagram"]).is_file())
                self.assertIn("("+row["usecase"]+")",self.usecases)
                for name in row["database_entiteiten"].split(","):
                    self.assertIn(name,self.tables,(row["eis_id"],name))
                tests=(ROOT/row["testbestand"]).read_text(encoding="utf-8")
                self.assertRegex(tests,r"(?m)^\\s*def test_")

    def test_five_mandatory_backend_sequence_scenarios_are_linked(self):
        sequence={Path(row["sequence_diagram"]).name for row in self.rows
                  if row["sequence_diagram"]}
        self.assertEqual(sequence,{
            "SD01_Klantenkorting.puml",
            "SD02_ProductNietOpVoorraad.puml",
            "SD03_KlantHeeftNietBetaald.puml",
            "SD04_KlantNietThuis.puml",
            "SD05_PotentieleKlantGeenBestelling.puml",
        })
