import os
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from datetime import datetime, timezone

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/employees",
)


def get_connection():
    return psycopg2.connect(DATABASE_URL)


@contextmanager
def _cursor():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with _cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id         SERIAL PRIMARY KEY,
                full_name  TEXT NOT NULL,
                position   TEXT NOT NULL,
                department TEXT NOT NULL,
                email      TEXT NOT NULL UNIQUE,
                phone      TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        # Миграция: добавляем колонки если их нет (для существующих БД)
        cur.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS created_at TEXT")
        cur.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS updated_at TEXT")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS employee_history (
                id          SERIAL PRIMARY KEY,
                employee_id INTEGER NOT NULL,
                changed_at  TEXT NOT NULL,
                change_type TEXT NOT NULL,
                field_name  TEXT,
                old_value   TEXT,
                new_value   TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id   SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                id   SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            )
        """)
        cur.execute(
            "INSERT INTO positions (name) SELECT DISTINCT position FROM employees"
            " ON CONFLICT DO NOTHING"
        )
        cur.execute(
            "INSERT INTO departments (name) SELECT DISTINCT department FROM employees"
            " ON CONFLICT DO NOTHING"
        )


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
            "(full_name LIKE %s OR position LIKE %s OR department LIKE %s)"
        )
        params.extend([like, like, like])
    if dept:
        conditions.append("department = %s")
        params.append(dept)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT * FROM employees {where} ORDER BY {sort} {order_sql}"
    with _cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_departments() -> list:
    with _cursor() as cur:
        cur.execute('SELECT name FROM departments ORDER BY name COLLATE "C"')
        rows = cur.fetchall()
        return [r["name"] for r in rows]


def get_all_positions() -> list:
    with _cursor() as cur:
        cur.execute('SELECT * FROM positions ORDER BY name COLLATE "C"')
        return cur.fetchall()


def get_position_by_id(position_id: int):
    with _cursor() as cur:
        cur.execute("SELECT * FROM positions WHERE id = %s", (position_id,))
        return cur.fetchone()


def create_position(name: str):
    with _cursor() as cur:
        cur.execute("INSERT INTO positions (name) VALUES (%s)", (name,))


def update_position(position_id: int, name: str):
    with _cursor() as cur:
        cur.execute("UPDATE positions SET name = %s WHERE id = %s", (name, position_id))


def delete_position(position_id: int):
    with _cursor() as cur:
        cur.execute("DELETE FROM positions WHERE id = %s", (position_id,))


def get_all_departments() -> list:
    with _cursor() as cur:
        cur.execute('SELECT * FROM departments ORDER BY name COLLATE "C"')
        return cur.fetchall()


def get_department_by_id(department_id: int):
    with _cursor() as cur:
        cur.execute("SELECT * FROM departments WHERE id = %s", (department_id,))
        return cur.fetchone()


def create_department(name: str):
    with _cursor() as cur:
        cur.execute("INSERT INTO departments (name) VALUES (%s)", (name,))


def update_department(department_id: int, name: str):
    with _cursor() as cur:
        cur.execute("UPDATE departments SET name = %s WHERE id = %s", (name, department_id))


def delete_department(department_id: int):
    with _cursor() as cur:
        cur.execute("DELETE FROM departments WHERE id = %s", (department_id,))


def get_by_id(employee_id: int):
    with _cursor() as cur:
        cur.execute("SELECT * FROM employees WHERE id = %s", (employee_id,))
        return cur.fetchone()


def create(full_name: str, position: str, department: str, email: str, phone: str):
    now = datetime.now(timezone.utc).isoformat()
    with _cursor() as cur:
        cur.execute(
            "INSERT INTO employees (full_name, position, department, email, phone, created_at, updated_at)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (full_name, position, department, email, phone, now, now),
        )
        employee_id = cur.fetchone()["id"]
        cur.execute(
            "INSERT INTO employee_history (employee_id, changed_at, change_type)"
            " VALUES (%s, %s, %s)",
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
    with _cursor() as cur:
        cur.execute(
            "UPDATE employees"
            " SET full_name=%s, position=%s, department=%s, email=%s, phone=%s, updated_at=%s"
            " WHERE id=%s",
            (full_name, position, department, email, phone, now, employee_id),
        )
        for field_name, old_val, new_val in fields:
            if (old_val or "") != (new_val or ""):
                cur.execute(
                    "INSERT INTO employee_history"
                    " (employee_id, changed_at, change_type, field_name, old_value, new_value)"
                    " VALUES (%s, %s, %s, %s, %s, %s)",
                    (employee_id, now, "update", field_name, old_val, new_val),
                )


def get_history(employee_id: int) -> list:
    with _cursor() as cur:
        cur.execute(
            "SELECT * FROM employee_history WHERE employee_id = %s ORDER BY changed_at DESC",
            (employee_id,),
        )
        return cur.fetchall()


def delete(employee_id: int):
    with _cursor() as cur:
        cur.execute("DELETE FROM employees WHERE id = %s", (employee_id,))
