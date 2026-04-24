from app.core.db import check_database_connection


def main() -> None:
    result = check_database_connection()
    print(result)


if __name__ == "__main__":
    main()
