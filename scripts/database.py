"""Shared SQLite database utilities for AxieOS."""

import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "blockchain"
    / "database"
    / "axieos.db"
)


def connect_database() -> sqlite3.Connection:
    """Return a connection to the existing AxieOS database."""

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"AxieOS database not found: {DATABASE_PATH}"
        )

    return sqlite3.connect(DATABASE_PATH)