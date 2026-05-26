from app.db import Base, engine

# IMPORTANT: import models so their tables register on Base.metadata before
# create_all — without this the metadata is empty and no tables are created.
from app import models  # noqa: F401


def main() -> None:
    Base.metadata.create_all(bind=engine)
    tables = ", ".join(sorted(Base.metadata.tables.keys()))
    print(f"SQLite DB initialized. Tables: {tables}")


if __name__ == "__main__":
    main()
