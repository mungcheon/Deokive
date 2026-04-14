from app import models  # noqa: F401
from app.db import Base, engine


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("SQLite DB initialized.")


if __name__ == "__main__":
    main()
