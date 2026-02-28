import os
import sqlite3
from datetime import datetime, timezone
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
                phone      TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        for col in ("created_at", "updated_at"):
            try:
                conn.execute(f"ALTER TABLE employees ADD COLUMN {col} TEXT")
            except sqlite3.OperationalError:
                pass
        conn.execute("""
            CREATE TABLE IF NOT EXISTS employee_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                changed_at  TEXT NOT NULL,
                change_type TEXT NOT NULL,
                field_name  TEXT,
                old_value   TEXT,
                new_value   TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        conn.execute("INSERT OR IGNORE INTO positions (name) SELECT DISTINCT position FROM employees")
        conn.execute("INSERT OR IGNORE INTO departments (name) SELECT DISTINCT department FROM employees")


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
        rows = conn.execute("SELECT name FROM departments ORDER BY name").fetchall()
        return [r["name"] for r in rows]


def get_all_positions() -> list:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM positions ORDER BY name").fetchall()


def get_position_by_id(position_id: int):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM positions WHERE id = ?", (position_id,)
        ).fetchone()


def create_position(name: str):
    with get_connection() as conn:
        conn.execute("INSERT INTO positions (name) VALUES (?)", (name,))


def update_position(position_id: int, name: str):
    with get_connection() as conn:
        conn.execute("UPDATE positions SET name = ? WHERE id = ?", (name, position_id))


def delete_position(position_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM positions WHERE id = ?", (position_id,))


def get_all_departments() -> list:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM departments ORDER BY name").fetchall()


def get_department_by_id(department_id: int):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM departments WHERE id = ?", (department_id,)
        ).fetchone()


def create_department(name: str):
    with get_connection() as conn:
        conn.execute("INSERT INTO departments (name) VALUES (?)", (name,))


def update_department(department_id: int, name: str):
    with get_connection() as conn:
        conn.execute("UPDATE departments SET name = ? WHERE id = ?", (name, department_id))


def delete_department(department_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM departments WHERE id = ?", (department_id,))


def get_by_id(employee_id: int):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM employees WHERE id = ?", (employee_id,)
        ).fetchone()


def create(full_name: str, position: str, department: str, email: str, phone: str):
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO employees (full_name, position, department, email, phone, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (full_name, position, department, email, phone, now, now),
        )
        employee_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO employee_history (employee_id, changed_at, change_type)"
            " VALUES (?, ?, ?)",
            (employee_id, now, "create"),
        )


def update(employee_id: int, full_name: str, position: str, department: str,
           email: str, phone: str):
    old = get_by_id(employee_id)
    now = datetime.now(timezone.utc).isoformat()
    fields = [
        ("full_name", old["full_name"], full_name),
        ("position", old["position"], position),
        ("department", old["department"], department),
        ("email", old["email"], email),
        ("phone", old["phone"] or "", phone or ""),
    ]
    with get_connection() as conn:
        conn.execute(
            "UPDATE employees"
            " SET full_name=?, position=?, department=?, email=?, phone=?, updated_at=?"
            " WHERE id=?",
            (full_name, position, department, email, phone, now, employee_id),
        )
        for field_name, old_val, new_val in fields:
            if (old_val or "") != (new_val or ""):
                conn.execute(
                    "INSERT INTO employee_history"
                    " (employee_id, changed_at, change_type, field_name, old_value, new_value)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (employee_id, now, "update", field_name, old_val, new_val),
                )


def get_history(employee_id: int) -> list:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM employee_history WHERE employee_id = ? ORDER BY changed_at DESC",
            (employee_id,),
        ).fetchall()


def delete(employee_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
