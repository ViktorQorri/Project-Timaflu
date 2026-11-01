# Issue #25: audit-log requirements and scope decision

## Requirements review
Issue #25 requests three acceptance criteria: log orders, log stock changes and register users.

The authoritative `Documentation/brightspace/Product-description.md` requires the six core business processes and expressly excludes receiving incoming stock. The current/desired process descriptions explain that orders, deliveries, stock and invoices must be tracked as **business records**, but do not specify a general-purpose actor audit trail. The current architecture leaves authentication undecided, so the system does not provide a reliable identifier for the employee responsible for an action.

## Business status records are not an audit trail
- `Bestelling` and `OrderStatus` represent a current order and its current status; they cannot prove who performed each change.
- `Magazijnlocatie` stores current physical quantities; it does not represent change history.
- `Deelorder`, `Verzamelbak` and delivery records represent business state, not a complete chronological actor history.
- Storing only the current state or a local timestamp would not meet the issue's requirement to register users and track changes.

## Decision required
Do not invent an `AuditLog` table or add unspecified logging to every write path. The project group must first decide:
1. Is the audit feature in scope despite its absence from the mandatory project products?
2. Is authentication (#24) in scope, and what stable user identity is recorded?
3. Which specific order and stock operations require before/after values and what retention period applies?
4. Does the log include the robot as an actor, and how is a robot authenticated?
5. Is manual correction supported, and who can view or export history?

If approved, amend the actual editable EER, SQL schema and migrations, the domain model, repository transaction boundaries and automated tests in one reviewed issue PR. Ensure each audited write is atomic with its business action. Never write passwords, tokens or customer medical details to an event log.

## Current implementation and traceability
| Deliverable | Finding |
|---|---|
| Product description | No explicit general audit-log requirement |
| Architecture | User authentication unresolved |
| Case-defined business records | Current state stored by business tables |
| Audit EER and SQL | No approved audit model |
| Backend and frontend | No audit event repository or audit overview |
| Validation | No actor identity or event requirements to test safely |

**Status:** Requirements investigation, blocked on group scope decision. No database changes, production activity or acceptance criteria are represented as complete. Use `Refs #25`, not `Closes #25`.
