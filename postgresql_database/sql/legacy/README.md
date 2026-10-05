# Legacy schema SQL

This directory preserves schema SQL from before Alembic became the canonical
migration system.

Do not run these files during database bootstrap. The authoritative definitions
for schemas, tables, constraints, indexes, and grants are maintained under
`../../migrations/versions/`.