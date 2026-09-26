"""Exécute les requêtes SQL de sql/ avec DuckDB sur les transactions nettoyées.

Usage :
    python src/analyses.py   # sql/*.sql -> output/tables/*.csv
"""

from pathlib import Path

import duckdb
import pandas as pd

DATA = Path("data/processed/transactions.parquet")
SQL_DIR = Path("sql")
TABLES_DIR = Path("output/tables")


def connect() -> duckdb.DuckDBPyConnection:
    """Connexion DuckDB en mémoire avec une vue `transactions` sur le fichier parquet."""
    con = duckdb.connect()
    con.execute(f"CREATE VIEW transactions AS SELECT * FROM read_parquet('{DATA}')")
    return con


def run_query(con: duckdb.DuckDBPyConnection, name: str) -> pd.DataFrame:
    return con.execute((SQL_DIR / f"{name}.sql").read_text(encoding="utf-8")).df()


def main() -> None:
    con = connect()
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(SQL_DIR.glob("*.sql")):
        df = run_query(con, path.stem)
        df.to_csv(TABLES_DIR / f"{path.stem}.csv", index=False)
        print(f"{path.stem}: {len(df)} lignes -> {TABLES_DIR / (path.stem + '.csv')}")


if __name__ == "__main__":
    main()
