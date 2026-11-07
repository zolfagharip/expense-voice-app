import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "expenses.db"

CATEGORIES = [
    "بنزین", "خوراک", "قهوه", "حمل‌ونقل", "خرید",
    "قبض", "سلامت", "سرگرمی", "سایر",
]


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount INTEGER NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                raw_transcript TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.commit()


def add_expense(amount: int, category: str, description: str = "",
                raw_transcript: str = "") -> int:
    """مبلغ به ریال ذخیره می‌شه. ورودی این تابع هم ریاله."""
    if category not in CATEGORIES:
        category = "سایر"
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO expenses (amount, category, description, raw_transcript) "
            "VALUES (?, ?, ?, ?)",
            (int(amount), category, description, raw_transcript),
        )
        conn.commit()
        return cur.lastrowid


def list_expenses(limit: int = 100):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM expenses ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def delete_expense(expense_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        conn.commit()
        return cur.rowcount > 0


def total_amount() -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT COALESCE(SUM(amount), 0) AS s FROM expenses").fetchone()
        return row["s"]
        
def get_summary() -> dict:
    """خلاصه هزینه‌ها: امروز، ۷ روز اخیر، ۳۰ روز اخیر."""
    with get_conn() as conn:
        today = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS s FROM expenses "
            "WHERE date(created_at) = date('now', 'localtime')"
        ).fetchone()["s"]

        week = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS s FROM expenses "
            "WHERE date(created_at) >= date('now', '-6 days', 'localtime')"
        ).fetchone()["s"]

        month = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS s FROM expenses "
            "WHERE date(created_at) >= date('now', '-29 days', 'localtime')"
        ).fetchone()["s"]

        return {"today": today, "week": week, "month": month}


def get_category_breakdown(days: int = 30) -> list:
    """تفکیک هزینه‌ها بر اساس دسته‌بندی در N روز اخیر."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT category, SUM(amount) AS total, COUNT(*) AS count "
            "FROM expenses "
            "WHERE date(created_at) >= date('now', ? , 'localtime') "
            "GROUP BY category ORDER BY total DESC",
            (f"-{days - 1} days",),
        ).fetchall()
        return [dict(r) for r in rows]


def get_daily_trend(days: int = 7) -> list:
    """روند روزانه هزینه‌ها در N روز اخیر (برای نمودار)."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT date(created_at) AS day, SUM(amount) AS total "
            "FROM expenses "
            "WHERE date(created_at) >= date('now', ?, 'localtime') "
            "GROUP BY date(created_at) ORDER BY day",
            (f"-{days - 1} days",),
        ).fetchall()
        return [dict(r) for r in rows]