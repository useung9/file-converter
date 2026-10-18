"""SQLite-based statistics tracking for FileConvert.
Tracks:
- Daily & Total Unique Visitors (based on hashed IP + date)
- Daily & Total Converted Bytes
- Total Conversions count
"""
import hashlib
import os
import sqlite3
from datetime import date
from typing import Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "stats.db")


def _get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _get_connection() as conn:
        # Visitors table: one row per (ip_hash, visit_date)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS visitors (
                ip_hash TEXT NOT NULL,
                visit_date TEXT NOT NULL,
                visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (ip_hash, visit_date)
            )
        """)
        # Conversions log table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_size_bytes INTEGER NOT NULL,
                conv_date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def hash_ip(ip: str) -> str:
    """Hash IP address with salt for privacy."""
    salt = "fileconvert_salt_2026"
    return hashlib.sha256(f"{salt}_{ip}".encode("utf-8")).hexdigest()[:16]


def record_visit(ip: str):
    """Record a visitor for today if not already counted."""
    today_str = date.today().isoformat()
    ip_h = hash_ip(ip)
    try:
        with _get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO visitors (ip_hash, visit_date) VALUES (?, ?)",
                (ip_h, today_str)
            )
            conn.commit()
    except Exception:
        pass


def record_conversion(file_size_bytes: int):
    """Record a file conversion size for today."""
    today_str = date.today().isoformat()
    try:
        with _get_connection() as conn:
            conn.execute(
                "INSERT INTO conversions (file_size_bytes, conv_date) VALUES (?, ?)",
                (file_size_bytes, today_str)
            )
            conn.commit()
    except Exception:
        pass


def format_bytes(bytes_num: int) -> str:
    """Format bytes into readable string (KB, MB, GB)."""
    if bytes_num < 1024:
        return f"{bytes_num} B"
    elif bytes_num < 1024 * 1024:
        return f"{bytes_num / 1024:.1f} KB"
    elif bytes_num < 1024 * 1024 * 1024:
        return f"{bytes_num / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_num / (1024 * 1024 * 1024):.2f} GB"


def get_stats() -> Dict[str, Any]:
    """Return aggregated stats: today/total visitors and today/total conversion size."""
    today_str = date.today().isoformat()
    with _get_connection() as conn:
        cur = conn.cursor()

        # 1. Today unique visitors
        cur.execute("SELECT COUNT(DISTINCT ip_hash) FROM visitors WHERE visit_date = ?", (today_str,))
        today_visitors = cur.fetchone()[0] or 0

        # 2. Total unique visitors (across all dates, or total unique IP count)
        cur.execute("SELECT COUNT(DISTINCT ip_hash) FROM visitors")
        total_visitors = cur.fetchone()[0] or 0

        # 3. Today converted bytes
        cur.execute("SELECT COALESCE(SUM(file_size_bytes), 0), COUNT(*) FROM conversions WHERE conv_date = ?", (today_str,))
        row_today = cur.fetchone()
        today_bytes = row_today[0] or 0
        today_conv_count = row_today[1] or 0

        # 4. Total converted bytes
        cur.execute("SELECT COALESCE(SUM(file_size_bytes), 0), COUNT(*) FROM conversions")
        row_total = cur.fetchone()
        total_bytes = row_total[0] or 0
        total_conv_count = row_total[1] or 0

    return {
        "today_visitors": today_visitors,
        "total_visitors": total_visitors,
        "today_bytes": today_bytes,
        "today_bytes_formatted": format_bytes(today_bytes),
        "total_bytes": total_bytes,
        "total_bytes_formatted": format_bytes(total_bytes),
        "today_conversions": today_conv_count,
        "total_conversions": total_conv_count,
    }


# Initialize DB on module load
init_db()
