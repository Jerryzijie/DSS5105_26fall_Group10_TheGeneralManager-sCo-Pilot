# Factory Copilot PostgreSQL Database

## Overview

This directory owns the reproducible PostgreSQL database lifecycle for the
Factory Copilot project. `sql/01_roles_and_database.sql` creates the project
roles and database, Alembic migrations are the canonical source for schemas,
tables, constraints, indexes, and grants, and the remaining SQL files import
seed data and validate data integrity and permissions.

The database is currently local rather than cloud-hosted. The main FastAPI and
LangGraph application uses PostgreSQL for operational, administrative,
authentication, and Copilot data. Database setup remains explicit and is not
run automatically when the application starts.

## Database design

- Database: `factory_copilot_db`
- Business schema: `app`
- Administration schema: `admin_meta`
- Project administrator: `factory_admin`
- Shared read-only permission role: `factory_reader` (`NOLOGIN`)
- Ordinary read-only login: `factory_user`
- AI Agent read-only login: `factory_agent`

`factory_user` and `factory_agent` inherit the permissions stored by `factory_reader`. Role attributes such as `LOGIN`, `CREATEDB` and `CREATEROLE` are defined separately for each login role.

### Business tables

| Table | Purpose |
|---|---|
| `app.orders` | Current complete orders dataset |
| `app.production_log` | Current complete production dataset |
| `app.workshops` | Current workshop capabilities, one row per workshop-category pair |
| `app.snapshot` | Distinct order states observed across the initial seed and subsequent successful `orders` uploads |

`app.snapshot` is append-only during normal application uploads. Its composite primary key (`order_id`, `status`, `stage`, `date`) prevents the same state observation from being stored twice. It contains both in-progress and complete states; it is not a copy of only the outgoing orders table.

The source `workshops.csv` retains its original format. During import, `TOPS+ACCESSORIES` is split into separate `TOPS` and `ACCESSORIES` rows. Therefore the supplied eight source rows become eleven database rows representing eight physical workshops.

### Administration tables

The `admin_meta` schema contains:

- `upload_history`: one record per upload attempt;
- `import_details`: per-table outcome for an upload;
- `data_sources`: the latest registered state and row count of each uploadable table.

Only `factory_admin` can access this schema. The two read-only login roles cannot inspect upload metadata.

## Directory structure

```text
postgresql_database/
|-- alembic.ini
|-- migrations/
|   |-- env.py
|   `-- versions/
|       |-- 001_initial_auth.py
|       `-- 002_auth_deactivation.py
|-- data/
|-- docs/
|-- evidence/
|-- sql/
|   |-- legacy/
|   |   |-- README.md
|   |   `-- schema_tables_permissions_pre_alembic.sql
|   |-- 01_roles_and_database.sql
|   |-- 03_import.sql
|   |-- 04_validate.sql
|   |-- 05_admin_permission_test.sql
|   `-- 06_readonly_permission_test.sql
`-- README.md
```

The `evidence` directory stores the latest reviewed local outputs from scripts 04–06. The SQL scripts remain the source of the tests; regenerate the evidence whenever the schema, data or permissions change.

## Prerequisites

- PostgreSQL server and command-line tools, including `psql`;
- a local PostgreSQL system administrator account, normally `postgres`;
- PostgreSQL `bin` on the Windows PATH;
- the three supplied current-data CSV files and `altogether_summary.csv` under `data/`.

### Start and verify PostgreSQL on Windows

PostgreSQL must be running before executing the SQL scripts or starting the administration backend.

First, confirm that the PostgreSQL command-line tools are available:

```powershell
psql --version
```
Find the PostgreSQL service installed on the computer:

```powershell
Get-Service -Name "postgresql*"
```

If its status is `Stopped`, open PowerShell as Administrator and start it using the service name shown by the previous command. For example:

```powershell
Start-Service -Name "postgresql-x64-18"
```

The exact service name depends on the installed PostgreSQL version. Do not assume that every computer uses `postgresql-x64-18`.

Verify that PostgreSQL is accepting connections:

```powershell
pg_isready -h localhost -p 5432
```

A successful result should resemble:

```text
localhost:5432 - accepting connections
```

If `Start-Service` reports a permission error, run PowerShell as Administrator. PostgreSQL can also be started visually by pressing `Win + R`, entering `services.msc`, locating the PostgreSQL service, and selecting **Start**.

Starting the PostgreSQL service is a routine operation and may be required after restarting the computer. Script `01` creates the project roles and database. Alembic creates or upgrades
the database structure. Script `03` imports the reproducible baseline data.

Do not store PostgreSQL passwords in this repository.

## Reproduce the database

Open PowerShell and move to this directory:

```powershell
Set-Location "C:\path\to\DSS5105_26fall_Group10_TheGeneralManager-sCo-Pilot\postgresql_database"
```

Run the commands from `postgresql_database`, because `03_import.sql` uses relative paths such as `data/orders.csv`.

### 1. Create roles and the database

Run once as the PostgreSQL system administrator:

```powershell
psql -X -h localhost -p 5432 -U postgres -d postgres -W -f "sql/01_roles_and_database.sql"
```

The script creates `factory_reader`, `factory_admin`, `factory_user`, `factory_agent`, grants the shared reader role to the two read-only logins, asks for three local login passwords, and creates `factory_copilot_db` owned by `factory_admin`.

This is an initial-setup script. Do not rerun it after the roles and database exist.

### 2. Apply canonical database migrations

With the project virtual environment activated, run:

```powershell
python -m alembic -c alembic.ini upgrade head
```
Alembic applies each missing revision in order:

- `001_initial_auth` creates the initial schemas, tables, constraints, indexes, and grants.
- `002_auth_deactivation` adds account-deactivation fields and constraints.
- `003_permissions_reconciliation` makes Alembic authoritative for database object permissions.
- `004_conversation_history` adds per-user conversations and persisted chat turns.

Run migrations after creating the project roles and database, and whenever a
pulled release contains a new revision. Apply migrations before starting or
restarting the backend. FastAPI checks the required baseline at startup but
does not run Alembic automatically.


### 3. Reset and import the reproducible baseline

Run as `factory_admin`:

```powershell
psql -X -h localhost -p 5432 -U factory_admin -d factory_copilot_db -W -f "sql/03_import.sql"
```

The baseline import runs as one transaction:

1. clear the three current business tables and `app.snapshot`;
2. import 120 current orders and 360 production rows;
3. import 223 initial order-state rows from `data/altogether_summary.csv`;
4. read eight workshop source rows through a temporary table;
5. split combined workshop categories and insert eleven workshop-category rows;
6. update the three `admin_meta.data_sources` records.

If any step fails, PostgreSQL rolls back the entire baseline reset and import.

This script is for initialisation and reproducible reset, not normal daily updates. Rerunning it deletes any order-state history accumulated after the baseline and restores the tracked 223-row seed. Use the application upload API for daily replacement of `orders`, `production_log`, or `workshops`.

### 4. Validate data and metadata

```powershell
psql -X -h localhost -p 5432 -U factory_admin -d factory_copilot_db -W -f "sql/04_validate.sql"
```

For the supplied current data, the key results are:

| Check | Expected result |
|---|---:|
| Orders rows | 120 |
| Unique order IDs | 120 |
| Total order pieces | 93,500 |
| Missing completed dates | 34 |
| Missing days late | 34 |
| Initial snapshot rows | 223 |
| Unique snapshot states | 223 |
| Snapshot `IN_PROGRESS` states | 137 |
| Snapshot `COMPLETE` states | 86 |
| Current order states missing from snapshot | 0 |
| Production rows/date-stage pairs | 360 |
| Production pieces completed | 231,595 |
| Workshop-category rows | 11 |
| Distinct physical workshops | 8 |
| Physical daily capacity | 1,600 |
| Active physical workshops | 7 |
| Physical workshops missing maximum batch | 7 |

Immediately after the baseline import, `snapshot_rows` and `unique_snapshot_states` should both be 223. During normal operation, the count may grow as new distinct order states are observed, but these two values must remain equal.

The workshop consistency query should return zero rows. All three `data_sources.row_count` values should match their corresponding current business tables.

The script actively asserts metadata row counts, workshop-profile consistency, and coverage of every current order state in `snapshot`. The other summary totals are reported for comparison with the expected baseline values above. A successful run ends with:

```text
VALIDATION PASSED: metadata counts, workshop profiles, and snapshot states are consistent
```

A metadata mismatch, inconsistent workshop profile, or missing current order state raises an exception and returns a non-zero `psql` exit code.

### 5. Test administrator permissions

```powershell
psql -X -h localhost -p 5432 -U factory_admin -d factory_copilot_db -W -f "sql/05_admin_permission_test.sql"
```

Expected behaviour:

- `factory_admin` can connect and use/create in both schemas;
- it can select, insert, update, delete and truncate all project tables;
- it can use the `admin_meta` identity sequence;
- a disposable table successfully passes create, read, update, delete, truncate and drop tests;
- the entire probe transaction is rolled back, and `probe_table_removed` is `t`.

The test does not persist its probe table or modify the four business tables.

### 6. Test read-only permissions

Run with either inherited read-only login. The Agent example is:

```powershell
psql -X -h localhost -p 5432 -U factory_agent -d factory_copilot_db -W -f "sql/06_readonly_permission_test.sql"
```

Expected behaviour:

- connection and `app` schema usage succeed;
- `admin_meta` schema usage and sequence usage are denied;
- `SELECT` succeeds for all four `app` tables;
- all write/create/drop permissions are false;
- explicit negative tests report that metadata SELECT, INSERT, UPDATE, DELETE, TRUNCATE, CREATE TABLE and DROP TABLE were denied;
- the final table counts remain unchanged.

A correct run includes:

```text
TEST PASSED: admin_meta data SELECT was denied
TEST PASSED: INSERT was denied
TEST PASSED: UPDATE was denied
TEST PASSED: DELETE was denied
TEST PASSED: TRUNCATE was denied
TEST PASSED: CREATE TABLE was denied
TEST PASSED: DROP TABLE was denied
=== All seven permission-denial tests passed ===
```

Immediately after the baseline import, the final counts should show 120 `orders`, 360 `production_log` rows, eleven `workshops` rows, and 223 `snapshot` rows. The snapshot count may be higher after later successful `orders` uploads.

## Safe reruns

- `01_roles_and_database.sql`: initial setup only;
- `python -m alembic -c alembic.ini upgrade head`: safe to rerun; Alembic applies only missing revisions;
- files under `sql/legacy/`: historical reference only; do not run during bootstrap;
- `03_import.sql`: technically rerunnable, but destructive to post-baseline snapshot history; it resets all four `app` tables to the tracked baseline files;
- `04_validate.sql`: safe to rerun;
- `05_admin_permission_test.sql`: safe to rerun because its changes are rolled back;
- `06_readonly_permission_test.sql`: safe to rerun because denied operations cannot persist.

Do not delete a database, schema, table or role merely to resolve an `already exists` message. First confirm the current database, user and intended environment.

## Connect the administration app

After completing Steps 1–3, configure and run the local FastAPI/React administration app using [`../SQL_related_app/README.md`](../SQL_related_app/README.md).

`SQL_related_app` remains a standalone data-administration middleware. It
handles file preview, validation, transactional imports, data-source metadata,
and controlled updates to the shared PostgreSQL database. It is not replaced
by the Manager Copilot application. Both applications are database clients;
the canonical schema remains owned by the Alembic migrations in this directory.

The active backend uses:

- `factory_agent` for read-only schema and SQL access;
- `factory_admin` for uploads and administration.

The backend can import CSV, XLSX and XLS files for the three current business tables. The SQL bootstrap script itself uses `psql` `\copy` to import the four tracked CSV baseline files, including the initial snapshot seed.

## Documentation

- [`docs/field_mapping.md`](docs/field_mapping.md): source-to-database field mapping and data audit;
- [`docs/database_guide.md`](docs/database_guide.md): database concepts, roles, permissions and usage guidance.

These documents should describe the current SQL files. They must not contain passwords or private environment values.

## Troubleshooting

- `psql is not recognized`: add the PostgreSQL `bin` directory to PATH and reopen PowerShell.
- `localhost:5432 - no response`: start the PostgreSQL service and verify it with `pg_isready`.
- `password authentication failed`: confirm the selected login role and its locally configured password.
- `data/orders.csv: No such file or directory`: run `03_import.sql` from `postgresql_database`.
- `role already exists` or `database already exists`: Step 1 has already been run; do not delete objects without checking the environment.
- Red underlines in a graphical SQL editor do not prove the file is invalid; `psql` backslash commands such as `\copy`, `\set` and `\echo` are not ordinary server-side SQL.

## Security and scope

- Never commit `.env` files or passwords.
- Use `factory_admin` only for maintenance and trusted administration endpoints.
- Use `factory_agent` for AI read-only access.
- The current deployment is local and is not a shared production server.
- The route name `/api/admin` does not itself authenticate a human administrator; application authentication remains a team integration decision.
