from app.bootstrap import ensure_database_ready
from app.db import Base


def main() -> None:
    ensure_database_ready()
    tables = ", ".join(sorted(Base.metadata.tables.keys()))
    print(f"Database initialized. Tables: {tables}")


if __name__ == "__main__":
    main()
