# Timaflu code

The Flask backend, the HTML and CSS frontend, and how to run them locally. The design behind it is in [the software architecture](../Documentation/Architecture/architecture.md).

## Structure

```text
code/
  backend/
    app.py              creates the Flask app, registers routes and error handlers
    config.py           reads settings from environment variables (.env)
    db.py               opens one database connection per request
    routes/             page routes and JSON API routes, one file per process
    services/           business logic, one file per process
    repositories/       SQL, one file per aggregate
    domain/             domain classes and domain errors
    requirements.txt
    .env.example
  frontend/
    templates/          Jinja2 templates, one per screen, all extend base.html
    static/css/         shared and screen-specific stylesheets
  database/
    schema.sql          creates the tables
    migrations/         one-time updates for existing databases
    seed.sql            demo data for every screen, made by generate_seed.py
```

## Run locally

Requirements: Python 3.10 or newer and a local MySQL server.

1. Create the database and a user for the backend (in MySQL Workbench or the `mysql` client):

   ```sql
   CREATE DATABASE timaflu;
   CREATE USER 'timaflu_app'@'localhost' IDENTIFIED BY 'choose-a-password';
   GRANT SELECT, INSERT, UPDATE, DELETE ON timaflu.* TO 'timaflu_app'@'localhost';
   ```

2. Run `database\schema.sql` against the `timaflu` database to create the tables.
   For an existing database, apply each unapplied SQL file in `database\migrations\`
   once, in filename order.
   For demo data, then run `database\seed.sql`. It empties every table first, so
   running it again resets the demo. Its dates follow the day you run it.

3. Install the dependencies, from the `code` folder:

   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r backend\requirements.txt
   ```

4. Copy `backend\.env.example` to `backend\.env` and fill in the password.

5. Start the app:

   ```powershell
   cd backend
   flask --app app run --debug
   ```

Open http://127.0.0.1:5000. The homepage is static; database errors are shown when a data-dependent process is used.

## Opleverbestanden maken

De school vraagt aparte ZIP-bestanden voor Python-backend en HTML/CSS-website,
plus het actuele EER, de databasequeries en de ontwerpproducten. Genereer
eerst het queryrapport met `python code/database/audit_ui_queries.py` tegen een
geïsoleerde lokale MySQL-testdatabase, zoals in de broncode beveiligd.
Het rapport komt in de genegeerde map `deliverables/` en blijft buiten Git.
Maak daarna de ZIP-bestanden vanuit de repositoryhoofdmap met:

```powershell
python code/build_deliverables.py --output-dir deliverables
```

Dit levert `timaflu-backend.zip`, `timaflu-frontend.zip`,
`timaflu-database-en-queries.zip` en `timaflu-ontwerpen.zip`.
Het websitearchief bevat de Jinja/HTML-templates en CSS; voor dynamische
schermen blijft de Python-backend nodig. De databasebestanden zijn
MySQL-scripts en documentatie, geen automatisch gepubliceerde online database.

De ZIP-bestanden worden niet opgeslagen in Git. Maak deze lokaal wanneer
de schooloplevering plaatsvindt. Alleen Git-tracked bronbestanden en het lokaal gegenereerde queryrapport
worden opgenomen; lokale wachtwoorden en overige tijdelijke gegevens niet.

## Adding a screen

Every screen follows the same path through the layers, as in the home page:

1. `repositories/`: a method with the SQL, returning domain classes.
2. `services/`: the business logic, receiving the repository through the constructor.
3. `routes/`: a route that calls the service and renders a template, or redirects after a POST.
4. `frontend/templates/`: a template that extends `base.html`.

Rules: no SQL outside repositories, no business logic in routes or templates, no HTTP in services. A broken business rule raises one of the errors from `domain/errors.py`.
