import argparse
import sqlite3
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
DEFAULT_DATABASE = PROJECT_ROOT / "data" / "demo" / "retail_analytics.db"


def build_database(database_path: Path, *, force: bool = False) -> Path:
    database_path = database_path.resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    if database_path.exists():
        if not force:
            raise FileExistsError(
                f"{database_path} already exists; pass --force to rebuild it."
            )
        database_path.unlink()

    schema_sql = (HERE / "schema.sql").read_text(encoding="utf-8")
    seed_sql = (HERE / "seed.sql").read_text(encoding="utf-8")

    connection = sqlite3.connect(database_path)
    try:
        connection.executescript(schema_sql)
        connection.executescript(seed_sql)
        connection.commit()
    finally:
        connection.close()

    return database_path


def main() -> None:
    parser = argparse.ArgumentParser(description="初始化零售分析只读演示数据库")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    path = build_database(args.database, force=args.force)
    print(f"Demo database ready: {path}")
    print("Enable with DATACOPILOT_QUERY_EXECUTION__ENABLED=true")


if __name__ == "__main__":
    main()
