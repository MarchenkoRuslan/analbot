"""
analytics.py
This module provides analytical functions over the sales data stored in
the SQLite database. It uses SQL queries for efficiency and avoids
loading all data into memory unless necessary. The primary functions
include:

* calculate_daily_sales() – Compute total revenue per day for a given
  number of recent days.
* calculate_average_check() – Compute the average value of a sale.
* get_top_products() – Rank products by total revenue and return the
  top N.
* forecast_sales() – Provide a naive forecast of future revenue based
  on recent history.

These functions rely on `data.get_connection()` to access the database.
"""

from __future__ import annotations

import sqlite3
from typing import List, Tuple, Optional
from datetime import datetime, timedelta

from .data import get_connection


def calculate_daily_sales(days: int = 7) -> List[Tuple[str, float]]:
    """
    Calculate total revenue for each day over the last `days` days.

    :param days: Number of recent days to include (inclusive of today).
    :return: List of (date, total) tuples ordered chronologically (oldest
             to newest). Dates are formatted as YYYY-MM-DD strings.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Compute the cutoff date. We use >= cutoff to include today and
        # the previous (days-1) days. SQLite uses text comparison for
        # dates stored as TEXT in ISO format.
        cutoff_date = (datetime.now().date() - timedelta(days=days - 1)).isoformat()
        cursor.execute(
            """
            SELECT date, SUM(amount) as total
            FROM sales
            WHERE date >= ?
            GROUP BY date
            ORDER BY date ASC
            """,
            (cutoff_date,),
        )
        rows = cursor.fetchall()
        return [(row[0], float(row[1])) for row in rows]
    finally:
        conn.close()


def calculate_average_check() -> float:
    """
    Compute the average value of a sale (average check).

    :return: The average amount per sale. Returns 0.0 if no sales.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT AVG(amount) FROM sales"
        )
        result = cursor.fetchone()
        avg_value = result[0] if result and result[0] is not None else 0.0
        return float(avg_value)
    finally:
        conn.close()


def get_top_products(limit: int = 3) -> List[Tuple[str, float]]:
    """
    Return the top `limit` products ranked by total revenue.

    :param limit: Number of products to return
    :return: List of (product, total_revenue) tuples ordered by revenue
             descending
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT product, SUM(amount) as total
            FROM sales
            GROUP BY product
            ORDER BY total DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        return [(row[0], float(row[1])) for row in rows]
    finally:
        conn.close()


def forecast_sales(days: int = 1) -> Optional[float]:
    """
    Provide a naive forecast for total revenue on the next day.

    The forecast is computed as the average daily revenue over the last
    7 days. If fewer than 3 days of data are available, the function
    returns None to indicate insufficient history.

    :param days: Number of days ahead to forecast (currently only 1 is
                 supported; additional values return the same forecast
                 repeated).
    :return: Forecasted total revenue or None if insufficient data.
    """
    # Get revenue for the last 7 days
    daily_sales = calculate_daily_sales(days=7)
    if len(daily_sales) < 3:
        # Not enough data to make a reasonable forecast
        return None

    # Compute average of the totals
    totals = [total for _, total in daily_sales]
    avg_daily = sum(totals) / len(totals)
    # For now we return only a single forecast value. If days>1, one
    # could extend this by returning a list or repeating the mean.
    return float(avg_daily)