from sqlalchemy import create_engine, text
from .config import database_url


def main():
    engine = create_engine(database_url(), hide_parameters=True)
    with engine.begin() as conn:
        conn.execute(text("GRANT USAGE ON SCHEMA public TO coursework_app"))
        conn.execute(
            text("GRANT SELECT ON ALL TABLES IN SCHEMA public TO coursework_app")
        )
        conn.execute(text("REVOKE SELECT ON alembic_version FROM coursework_app"))
        conn.execute(
            text("GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO coursework_app")
        )
        for table in [
            "tickets",
            "comments",
            "history_events",
            "ticket_intervals",
            "idempotency_keys",
            "sessions",
        ]:
            conn.execute(text(f"GRANT INSERT ON {table} TO coursework_app"))
        # PostgreSQL row locks require UPDATE privilege on at least one column.
        for table in ["users", "queues", "categories"]:
            conn.execute(text(f"GRANT UPDATE (version) ON {table} TO coursework_app"))
        conn.execute(text("GRANT UPDATE (revision) ON sla_policies TO coursework_app"))
        for table in ["tickets", "ticket_intervals", "sessions"]:
            conn.execute(text(f"GRANT UPDATE ON {table} TO coursework_app"))
    engine.dispose()


if __name__ == "__main__":
    main()
