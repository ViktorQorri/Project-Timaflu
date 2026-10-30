# Issue #24: authentication and authorization scope review

## Evidence and applicable requirements
- `Documentation/brightspace/Product-description.md` requires the six operational processes, an HTML/CSS interface and Python/MySQL backend. It does **not** require login, identity management, password storage or a role administration UI.
- `Documentation/brightspace/Current-processes.md` describes employee groups, including sales, warehouse, purchasing, administration, couriers and acquisition.
- `Documentation/Architecture/architecture.md` explicitly lists the decision whether employees must log in as **undecided**.
- `code/frontend/DESIGN_SYSTEM.MD` contains proposed role visibility for a prototype and warns that production rights must also be enforced by the backend.
- `code/backend/app.py` currently registers process blueprints without a login or authorization component.

## Issue versus case
Issue #24 asks to manage roles, check permissions and restrict individual functions. None of these acceptance criteria can safely be claimed implemented. Adding hard-coded demo credentials or hiding menu entries would not secure the endpoints and could be misleading. There is no approved credential lifecycle, user schema, admin permission model, test identity or deployment policy. For the school submission, no additional authentication system is introduced until the team explicitly confirms the scope.

## Security consequence
The current Flask application must not be presented as production-secure or exposed to an untrusted public network with business data. HTML navigation visibility is not an access-control boundary. If access is needed for school demonstrations, use a controlled local environment and fictional sample data.

## Decision required from the project group
Confirm whether issue #24 is part of the graded scope. If yes, decide:
1. Which employees need accounts and how accounts are created, reset and disabled.
2. Which operations are read-only and writable for each role.
3. Whether robot API authentication is required and what credentials a robot uses.
4. Where employee identities and role assignments live in the EER and schema.
5. How test users and credentials are managed without committing secrets.

These decisions must be reflected in the EER, domain model, routes, UI and tests before any acceptance criterion is marked complete.

## Traceability and verification
| Artifact | Current position |
|---|---|
| Case and product description | No explicit authentication requirement |
| Architecture | Login question open |
| Frontend design | Role visibility described, not an implemented backend boundary |
| EER/SQL | No reviewed identity model in the current issue scope |
| Backend | No authorization middleware or route decorators |
| Tests | Authenticated role matrix cannot be tested until a model is approved |

**PR status:** Scope analysis only, blocked on a group decision. Do not use `Closes #24`.
