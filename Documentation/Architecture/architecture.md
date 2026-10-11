# Software architecture

Issue: Define software architecture. This document describes how the frontend, backend and database fit together.

![Software architecture](architecture.svg)

Source: [architecture.drawio](architecture.drawio). Update the `.drawio` file and the `.svg` export together.

## Overview

The system has three parts: a frontend of plain HTML and CSS, a Python backend that serves it, and a MySQL database. The robots in the warehouse use the same backend through a small JSON API.

| Part | Technology | Talks to |
| --- | --- | --- |
| Frontend | HTML, CSS (no libraries, no JS) | Backend, over HTTP |
| Backend | Python, Flask, Jinja2 | Browser, robots and database |
| Database | MySQL | Backend only |
| Robots | Any HTTP client | Backend JSON API |

## Frontend

- Plain HTML and CSS, no libraries and no JavaScript, as the product description requires.
- Without JS a page cannot fetch data by itself. Every page is rendered on the server: the backend fills an HTML template with data from the database and sends finished HTML to the browser.
- Navigating is done with links (GET). Changing data is done with HTML forms (POST), for example placing an order or marking a delivery as delivered.
- After a successful POST the backend redirects to a GET page (post/redirect/get), so refreshing the page never submits a form twice.
- One template per screen from the screen designs. The order picking and distribution screens are responsive (CSS media queries) and work on mobile devices. The other screens are designed for desktop.

## Backend

Python with Flask. Flask (with its template engine Jinja2) is the only web dependency, to keep dependencies minimal. The code is split in layers so every class is easy to find and to trace to the class diagram.

| Layer | Responsibility |
| --- | --- |
| Page routes | Receive a browser request, call a service, return a rendered template or a redirect |
| JSON API routes | Same as page routes, but for the robots: JSON in, JSON out |
| Services | The business logic, including the five fully implemented processes |
| Repositories | The only place with SQL. They return domain classes |
| Domain classes | Customer, Order, Product, Supplier, Invoice and so on. Same names as in the class diagram and the EER |

The five processes that must be fully implemented live in the services layer:

1. Order discount (sales)
2. Product out of stock, supplier list (purchasing)
3. Unpaid invoice (administration)
4. Customer absent at delivery (distribution)
5. Potential customer without order (acquisition)

Rules for the layers:

- A route never contains business logic or SQL.
- A service never contains SQL and never knows about HTTP.
- A repository never contains business logic.
- Calls only go downwards: routes, services, repositories.

## Robot communication

Robots are not browsers, so they do not use the HTML pages. Each robot (one per aisle) talks to the JSON API routes. The exact endpoints follow from the use case diagram of the robot and the order picking activity diagram. Expected calls:

- Get the next partial order for this aisle
- Report the scanned code of a collection crate
- Report that a crate is full and put on the conveyor belt
- Report that the partial order is complete, so a new one can be assigned

## Database

- MySQL, normalized, hosted online and filled with enough relevant data.
- Only the backend talks to the database, always through parameterized queries from the repositories. The browser and the robots never access it directly.
- The queries per screen in the query document are the same queries the repositories run.

## Traceability

| Product | How it connects |
| --- | --- |
| Screen designs | One template and one page route per screen |
| Class diagram | Domain classes, services and repositories |
| Sequence diagrams | Route, service, repository, database for the five processes |
| EER | Tables map to domain classes and repositories |

## Open points

- Hosting must be free. Candidate: Azure for Students (App Service for the backend, Azure Database for MySQL for the database), claimed with the school email. Check the credit and eligibility on the Azure and GitHub Education pages before deciding.
- Fix the robot endpoints once the robot use case diagram is final.
