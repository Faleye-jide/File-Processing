"""Check whether the configured database is reachable, without exposing credentials."""

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.db.session import engine


def main() -> int:
    try:
        with engine.connect() as connection:
            if engine.dialect.name == "postgresql":
                database, username, port = connection.execute(
                    text("SELECT current_database(), current_user, inet_server_port()")
                ).one()
                print(f"PostgreSQL connection OK: database={database}, user={username}, port={port}")
            else:
                connection.execute(text("SELECT 1"))
                print(f"{engine.dialect.name} connection OK")
        return 0
    except SQLAlchemyError as exc:
        print(
            f"Database connection failed ({type(exc).__name__}). "
            "Check the running server, DATABASE_URL, port, database, and role permissions."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
