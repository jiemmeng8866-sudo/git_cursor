from __future__ import annotations

from typing import Annotated, Generator

import sqlite3

from fastapi import Depends

from novel_edit.config import get_db_path
from novel_edit.repository import ensure_db

DB_PATH = get_db_path()


def get_conn() -> Generator[sqlite3.Connection, None, None]:
    conn = ensure_db(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


Conn = Annotated[sqlite3.Connection, Depends(get_conn)]
