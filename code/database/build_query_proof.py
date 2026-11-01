"""Create the complete Timaflu school query document on isolated localhost MySQL.

One command records every GET, executes reversible form actions, renders 28
screen designs with Chrome and composes the output with actual SQL results.
"""
import os
from pathlib import Path
from audit_ui_queries import main as audit_reads, create_app, DATABASE
from audit_ui_actions import record_mutations
from render_design_screens import render
from assemble_query_submission import create
from render_query_document import render as render_pdf

def main():
    if os.getenv("TIMAFLU_TEST_ALLOW_RESET")!="isolated" or os.getenv("TIMAFLU_TEST_MYSQL_HOST")!="127.0.0.1":
        raise SystemExit("Only run on explicitly isolated localhost MySQL")
    audit_reads()
    options=dict(host="127.0.0.1",port=int(os.environ["TIMAFLU_TEST_MYSQL_PORT"]),
        user=os.environ.get("TIMAFLU_TEST_MYSQL_USER","root"),
        password=os.environ["TIMAFLU_TEST_MYSQL_PASSWORD"],database=DATABASE)
    app=create_app()
    app.config.update(TESTING=True,SECRET_KEY="testkey",
        DB_HOST=options["host"],DB_PORT=options["port"],DB_USER=options["user"],
        DB_PASSWORD=options["password"],DB_NAME=DATABASE,
        TIMAFLU_ADDRESS="TESTGEGEVENS: Fictieve Afzenderstraat 9, Breda")
    record_mutations(app,options)
    render()
    create()
    render_pdf()
if __name__=="__main__":main()
