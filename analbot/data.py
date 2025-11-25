"""
data.py
Helper functions for interacting with the SQLite database. This module
encapsulates database initialisation, insertion of sales records and
common queries used by the analytics layer. All database operations
connect to a single file-based database located under the `db/`
directory. SQLite is sufficient for a small number of records and is
portable across systems.

The table schema for `sales` is defined as follows:

    id       INTEGER PRIMARY KEY AUTOINCREMENT
    date     TEXT    (in ISO format YYYY-MM-DD)
    product  TEXT
    quantity INTEGER
    amount   REAL    (monetary value of the sale)

When new sales data is uploaded, each CSV row should include these
columns. The insert_sales() function normalises and persists the
records.
"""

import os
import sqlite3
from typing import Iterable, Tuple, List

import pandas as pd


# Path to the database file. Users may override via the ANALBOT_DB_PATH
# environment variable. When absent, defaults to 'db/database.db'.
DB_PATH = os.getenv("ANALBOT_DB_PATH", os.path.join("db", "database.db"))


def _ensure_db_dir() -> None:
    """Ensure that the directory for the database exists."""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.isdir(db_dir):
        os.makedirs(db_dir, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    """Return a new connection to the SQLite database.

    SQLite connections are not inherently thread-safe; specifying
    `check_same_thread=False` allows connections to be shared across
    different threads (as used by the Telegram bot). However, ensure
    that each thread uses its own cursor or connection where possible.
    """
    _ensure_db_dir()
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db() -> None:
    """Initialise the database by creating the required tables if missing."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                product TEXT,
                quantity INTEGER,
                amount REAL
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def insert_sales(df: pd.DataFrame) -> int:
    """
    Insert sales records from a pandas DataFrame into the database.

    The DataFrame must contain columns: 'date', 'product', 'quantity',
    'amount'. Dates are parsed and normalised to ISO format
    (YYYY-MM-DD). The function returns the number of inserted rows.

    :param df: DataFrame with sales data
    :return: count of inserted rows
    """
    required_cols = {"date", "product", "quantity", "amount"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Normalise date column to ISO format
    # If date parsing fails, let pandas raise to inform the caller
    df["date"] = pd.to_datetime(df["date"]).dt.date.astype(str)
    # Ensure quantity is integer and amount is float
    df["quantity"] = df["quantity"].astype(int)
    df["amount"] = df["amount"].astype(float)

    records: List[Tuple[str, str, int, float]] = [
        (row["date"], row["product"], int(row["quantity"]), float(row["amount"]))
        for _, row in df.iterrows()
    ]

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO sales (date, product, quantity, amount) VALUES (?, ?, ?, ?)",
            records,
        )
        conn.commit()
        return len(records)
    finally:
        conn.close()