import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("DATABASE_PATH", Path(__file__).parent / "employees.db"))


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name  TEXT NOT NULL,
                position   TEXT NOT NULL,
                department TEXT NOT NULL,
                email      TEXT NOT NULL UNIQUE,
                phone      TEXT
            )
        """)


_ALLOWED_SORT = {"full_name", "position", "department"}


def get_all(search: str = "", sort: str = "full_name",
            order: str = "asc", dept: str = "") -> list:
    if sort not in _ALLOWED_SORT:
        sort = "full_name"
    order_sql = "ASC" if order != "desc" else "DESC"

    conditions, params = [], []
    if search:
        like = f"%{search}%"
        conditions.append(
            "(full_name LIKE ? OR position LIKE ? OR department LIKE ?)"
        )
        params.extend([like, like, like])
    if dept:
        conditions.append("department = ?")
        params.append(dept)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT * FROM employees {where} ORDER BY {sort} {order_sql}"
    with get_connection() as conn:
        return conn.execute(sql, params).fetchall()


def get_departments() -> list:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT department FROM employees ORDER BY department"
        ).fetchall()
        return [r["department"] for r in rows]


def get_by_id(employee_id: int):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM employees WHERE id = ?", (employee_id,)
        ).fetchone()


def create(full_name: str, position: str, department: str, email: str, phone: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO employees (full_name, position, department, email, phone)"
            " VALUES (?, ?, ?, ?, ?)",
            (full_name, position, department, email, phone),
        )


def update(employee_id: int, full_name: str, position: str, department: str,
           email: str, phone: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE employees"
            " SET full_name=?, position=?, department=?, email=?, phone=?"
            " WHERE id=?",
            (full_name, position, department, email, phone, employee_id),
        )


def delete(employee_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
