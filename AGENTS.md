# AGENTS.md

Instructions for AI agents working in this repository.

## Keep queries.sql and the repositories in sync

The SQL for the screens lives in two places:

- `code/backend/repositories/`: the queries the app runs, with `%s` placeholders.
- `code/database/queries.sql`: the same queries per screen, with example values, used for the query document deliverable.

Both must contain the same query for each screen. Only the placeholders differ.

When you add, change or remove a query in one of them, make the same change in the other in the same task.

When you find that they differ (a different column, join, filter or table), do not choose yourself. Stop, show the user both versions, and ask which one is leading. Then update the other one to match.
