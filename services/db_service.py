# services/db_service.py
# Author: Emsii (refactored)
# Jedyne miejsce w aplikacji które dotyka SQLite.
# Bez SQL injection — parametryzowane zapytania + whitelist tabel.

import sqlite3
import threading
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
DB_FILE = BASE_DIR / "Heat.db"

_lock = threading.Lock()  # SQLite nie jest thread-safe dla wielu połączeń

# Whitelist tabel — ochrona przed SQL injection przez nazwę tabeli
ALLOWED_TABLES = {"temperatura", "temperatura_outdoor"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS {table} (
    id         INTEGER PRIMARY KEY ASC,
    data       VARCHAR(250) NOT NULL,
    time    VARCHAR(250) NOT NULL,
    temp_dot   REAL NOT NULL,
    temp_comma VARCHAR(250) NOT NULL,
    jednostka  VARCHAR(250) NOT NULL
)
"""

ALLOWED_TABLES_RP = {"Temperatura_RP"}

SCHEMA_RP = """
CREATE TABLE IF NOT EXISTS {table} (
    id         INTEGER PRIMARY KEY ASC,
    data       VARCHAR(250) NOT NULL,
    time    VARCHAR(250) NOT NULL,
    temp_dot   REAL NOT NULL,
    wentylator   INTEGER NOT NULL,
    CPU   INTEGER NOT NULL,
    RAM   INTEGER NOT NULL
)
"""


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_FILE))
    conn.execute("PRAGMA journal_mode=WAL")  # bezpieczniejszy tryb zapisu
    return conn


def ensure_tables() -> None:
    """Utwórz tabele jeśli nie istnieją. Wywoływać przy starcie."""
    with _lock:
        conn = _get_connection()
        try:
            for table in ALLOWED_TABLES:
                conn.execute(SCHEMA.format(table=table))
            for table in ALLOWED_TABLES_RP:
                conn.execute(SCHEMA_RP.format(table=table))    
            conn.commit()
            logger.info("DB tables ready")
        finally:
            conn.close()

def insert_temperature_rp(
    table: str,
    date: str,
    time: str,
    value: float,
    wentylator: int,
    CPU: int,
    RAM: int
) -> None:
    """
    Wstaw odczyt temperatury i stanu wentylatora.
    Nazwy tabel przez whitelist — nie przez f-string z user input.
    """
    if table not in ALLOWED_TABLES_RP:
        raise ValueError(f"Unknown table: {table!r}. Allowed: {ALLOWED_TABLES_RP}")

    with _lock:
        conn = _get_connection()
        try:
            conn.execute(
                f"INSERT INTO {table} (data, time, temp_dot, wentylator, CPU, RAM) "
                f"VALUES (?, ?, ?, ?, ?, ?)",
                (date, time, value, wentylator, CPU, RAM),  
            )
            conn.commit()
            logger.debug(f"DB insert RP: {table} {value}°C, wentylator={wentylator}, CPU={CPU}, RAM={RAM} @ {date} {time}")
        except sqlite3.Error:
            logger.exception(f"DB insert failed for table {table}")
        finally:
            conn.close()

            
def insert_temperature(
    table: str,
    date: str,
    time: str,
    value: float,
) -> None:
    """
    Wstaw odczyt temperatury.
    Nazwy tabel przez whitelist — nie przez f-string z user input.
    """
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Unknown table: {table!r}. Allowed: {ALLOWED_TABLES}")

    comma_value = str(value).replace(".", ",")
    unit = "\u00b0C"

    with _lock:
        conn = _get_connection()
        try:
            conn.execute(
                f"INSERT INTO {table} (data, time, temp_dot, temp_comma, jednostka) "
                f"VALUES (?, ?, ?, ?, ?)",
                (date, time, value, comma_value, unit),
            )
            conn.commit()
            logger.debug(f"DB insert: {table} {value}{unit} @ {date} {time}")
        except sqlite3.Error:
            logger.exception(f"DB insert failed for table {table}")
        finally:
            conn.close()


def get_latest_temperatures(table: str, limit: int = 10) -> list:
    """Pobierz ostatnie n odczytów z tabeli."""
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Unknown table: {table!r}")

    with _lock:
        conn = _get_connection()
        try:
            cur = conn.execute(
                f"SELECT data, godzina, temp_dot FROM {table} ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            return cur.fetchall()
        except sqlite3.Error:
            logger.exception(f"DB read failed for table {table}")
            return []
        finally:
            conn.close()
