# AGENTS.md

Instructions for AI agents working in this repository.

## Source hierarchy: the case is authoritative

Apply these sources in this order:

1. `Documentation/brightspace/Current-processes.md` and `Documentation/brightspace/Desired-process.md`, which describe Timaflu's actual current and desired business processes.
2. `Documentation/brightspace/Product-description.md`, which defines the school's mandatory deliverables and five required fully implemented backend scenarios.
3. The approved activity diagrams, use cases, domain class diagram (DKD), EER and sequence diagrams, checked against the case and the required deliverables.
4. GitHub issues, user stories and acceptance criteria, which are task planning aids, **not additional authority** to invent or extend the case.

When a user story requests functionality that the case does not describe, do not treat that extra criterion as a mandatory case requirement and do not invent behavior, database fields, status values, hardware APIs or user roles to satisfy it. Identify the discrepancy in the relevant PR and keep the code within the documented case.

The case explicitly excludes receiving incoming stock. The school requires HTML/CSS without JavaScript or frontend libraries, with responsive orderpicking and distribution screens. The five scenarios listed in Product-description.md must work; other classes and methods may be stubs as the assignment allows. Keep the Python implementation, DKD, EER and SQL consistent.

If two case sources themselves disagree on a material business rule, document the conflicting passages and ask for clarification rather than choosing an unsupported rule.

## Keep queries.sql and the repositories in sync

The SQL for the screens lives in two places:

- `code/backend/repositories/`: the queries the app runs, with `%s` placeholders.
- `code/database/queries.sql`: the same queries per screen, with example values, used for the query document deliverable.

Both must contain the same query for each screen. Only the placeholders differ.

When you add, change or remove a query in one of them, make the same change in the other in the same task.

When you find that they differ (a different column, join, filter or table), do not choose yourself. Stop, show the user both versions, and ask which one is leading. Then update the other one to match.
