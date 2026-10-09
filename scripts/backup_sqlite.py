"""Create a transactionally consistent SQLite backup without stopping the API."""

from __future__ import annotations

import argparse
import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "tasks.sqlite3"


def backup_database(source: str | Path, destination: str | Path) -> Path:
    """Back up an existing SQLite file, never replacing a prior backup."""
    source_path = Path(source).resolve()
    destination_path = Path(destination).resolve()

    if source_path == destination_path:
        raise ValueError("Origem e destino não podem ser o mesmo arquivo.")
    if not source_path.is_file():
        raise FileNotFoundError(f"Banco de origem inexistente: {source_path}")
    if destination_path.exists():
        raise FileExistsError(f"O destino já existe: {destination_path}")

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".task-manager-backup-", suffix=".sqlite3", dir=destination_path.parent
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        # mode=ro prevents a typo from silently creating an empty source database.
        with closing(sqlite3.connect(source_path.as_uri() + "?mode=ro", uri=True)) as source_db:
            with closing(sqlite3.connect(temporary_path)) as destination_db:
                source_db.backup(destination_db)
                result = destination_db.execute("PRAGMA integrity_check").fetchone()
                if result is None or result[0] != "ok":
                    raise sqlite3.DatabaseError("Verificação de integridade do backup falhou.")
        # Hard-linking in the same directory is atomic and refuses an existing destination.
        os.link(temporary_path, destination_path)
        return destination_path
    finally:
        temporary_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backup consistente do SQLite do Task Manager")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(os.getenv("TASK_MANAGER_DB_PATH", str(DEFAULT_SOURCE))),
        help="Banco de origem; padrão: TASK_MANAGER_DB_PATH ou data/tasks.sqlite3",
    )
    parser.add_argument("--destination", type=Path, required=True, help="Novo arquivo de backup")
    args = parser.parse_args()
    try:
        output = backup_database(args.source, args.destination)
    except (ValueError, OSError, sqlite3.DatabaseError) as exc:
        parser.error(str(exc))
    print(f"Backup concluído: {output}")


if __name__ == "__main__":
    main()
