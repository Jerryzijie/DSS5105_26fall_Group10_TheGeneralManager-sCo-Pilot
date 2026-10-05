"""Make Alembic authoritative for PostgreSQL permissions.

Revision ID: 003_permissions_reconciliation
Revises: 002_auth_deactivation
"""

from alembic import op


revision = "003_permissions_reconciliation"
down_revision = "002_auth_deactivation"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Database connection privileges.
    op.execute(
        """
        DO $$
        BEGIN
            EXECUTE format(
                'REVOKE CONNECT, TEMPORARY ON DATABASE %I FROM PUBLIC',
                current_database()
            );
            EXECUTE format(
                'GRANT CONNECT, TEMPORARY ON DATABASE %I TO factory_admin',
                current_database()
            );
            EXECUTE format(
                'GRANT CONNECT ON DATABASE %I TO factory_reader',
                current_database()
            );
        END
        $$;
        """
    )

    # Business data is readable through the shared read-only role.
    op.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
    op.execute("GRANT USAGE ON SCHEMA app TO factory_reader")
    op.execute("REVOKE CREATE ON SCHEMA app FROM factory_reader")
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA app FROM PUBLIC")
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA app TO factory_reader")
    op.execute(
        "REVOKE ALL ON ALL SEQUENCES IN SCHEMA app "
        "FROM PUBLIC, factory_reader, factory_user, factory_agent"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA app "
        "GRANT SELECT ON TABLES TO factory_reader"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA app "
        "REVOKE ALL ON TABLES FROM PUBLIC"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA app "
        "REVOKE ALL ON SEQUENCES "
        "FROM PUBLIC, factory_reader, factory_user, factory_agent"
    )

    # Authentication, Copilot state, and administration metadata are private.
    for schema in ("admin_meta", "auth", "copilot"):
        op.execute(
            f"REVOKE ALL ON SCHEMA {schema} "
            "FROM PUBLIC, factory_reader, factory_user, factory_agent"
        )
        op.execute(
            f"REVOKE ALL ON ALL TABLES IN SCHEMA {schema} "
            "FROM PUBLIC, factory_reader, factory_user, factory_agent"
        )
        op.execute(
            f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA {schema} "
            "FROM PUBLIC, factory_reader, factory_user, factory_agent"
        )
        op.execute(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} "
            "REVOKE ALL ON TABLES "
            "FROM PUBLIC, factory_reader, factory_user, factory_agent"
        )
        op.execute(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} "
            "REVOKE ALL ON SEQUENCES "
            "FROM PUBLIC, factory_reader, factory_user, factory_agent"
        )


def downgrade() -> None:
    # Remove grants introduced by this revision. Security revokes remain in place.
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA app "
        "REVOKE SELECT ON TABLES FROM factory_reader"
    )
    op.execute("REVOKE SELECT ON ALL TABLES IN SCHEMA app FROM factory_reader")
    op.execute("REVOKE USAGE ON SCHEMA app FROM factory_reader")

    op.execute(
        """
        DO $$
        BEGIN
            EXECUTE format(
                'REVOKE CONNECT, TEMPORARY ON DATABASE %I FROM factory_admin',
                current_database()
            );
            EXECUTE format(
                'REVOKE CONNECT ON DATABASE %I FROM factory_reader',
                current_database()
            );
            EXECUTE format(
                'GRANT CONNECT, TEMPORARY ON DATABASE %I TO PUBLIC',
                current_database()
            );
        END
        $$;
        """
    )