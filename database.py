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
        cur.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id            SERIAL PRIMARY KEY,
                full_name     TEXT NOT NULL,
                position_id   INTEGER NOT NULL REFERENCES positions(id),
                department_id INTEGER NOT NULL REFERENCES departments(id),
                email         TEXT NOT NULL UNIQUE,
                phone         TEXT,
                created_at    TEXT,
                updated_at    TEXT
            )
        """)
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

        # Migration: add FK columns if not exist (for databases with old schema)
        cur.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS position_id INTEGER")
        cur.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS department_id INTEGER")
        cur.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS created_at TEXT")
        cur.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS updated_at TEXT")

        # Migration: if old text column 'position' exists, migrate data and drop it
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'employees' AND column_name = 'position'
        """)
        if cur.fetchone():
            cur.execute("""
                INSERT INTO positions (name)
                SELECT DISTINCT position FROM employees
                WHERE position IS NOT NULL AND position <> ''
                ON CONFLICT DO NOTHING
            """)
            cur.execute("""
                UPDATE employees e
                SET position_id = p.id
                FROM positions p
                WHERE p.name = e.position AND e.position_id IS NULL
            """)
            cur.execute("ALTER TABLE employees DROP COLUMN position")

        # Migration: if old text column 'department' exists, migrate data and drop it
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'employees' AND column_name = 'department'
        """)
        if cur.fetchone():
            cur.execute("""
                INSERT INTO departments (name)
                SELECT DISTINCT department FROM employees
                WHERE department IS NOT NULL AND department <> ''
                ON CONFLICT DO NOTHING
            """)
            cur.execute("""
                UPDATE employees e
                SET department_id = d.id
                FROM departments d
                WHERE d.name = e.department AND e.department_id IS NULL
            """)
            cur.execute("ALTER TABLE employees DROP COLUMN department")

        # Migration: set NOT NULL on FK columns (after data is filled)
        cur.execute("ALTER TABLE employees ALTER COLUMN position_id SET NOT NULL")
        cur.execute("ALTER TABLE employees ALTER COLUMN department_id SET NOT NULL")

        # Migration: add FK constraints if not already present
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'fk_emp_position' AND conrelid = 'employees'::regclass
                ) THEN
                    ALTER TABLE employees
                    ADD CONSTRAINT fk_emp_position FOREIGN KEY (position_id) REFERENCES positions(id);
                END IF;
            END $$
        """)
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'fk_emp_department' AND conrelid = 'employees'::regclass
                ) THEN
                    ALTER TABLE employees
                    ADD CONSTRAINT fk_emp_department FOREIGN KEY (department_id) REFERENCES departments(id);
                END IF;
            END $$
        """)


_ALLOWED_SORT = {"full_name", "position", "department"}

_SORT_COL_MAP = {
    "full_name": "e.full_name",
    "position": "p.name",
    "department": "d.name",
}

_EMPLOYEE_SELECT = """
    SELECT e.id, e.full_name,
           p.name AS position, p.id AS position_id,
           d.name AS department, d.id AS department_id,
           e.email, e.phone, e.created_at, e.updated_at
    FROM employees e
    JOIN positions p ON p.id = e.position_id
    JOIN departments d ON d.id = e.department_id
"""


def get_all(search: str = "", sort: str = "full_name",
            order: str = "asc", dept: str = "") -> list:
    if sort not in _ALLOWED_SORT:
        sort = "full_name"
    order_sql = "ASC" if order != "desc" else "DESC"
    sort_col = _SORT_COL_MAP[sort]

    conditions, params = [], []
    if search:
        like = f"%{search}%"
        conditions.append(
            "(e.full_name LIKE %s OR p.name LIKE %s OR d.name LIKE %s)"
        )
        params.extend([like, like, like])
    if dept:
        conditions.append("d.name = %s")
        params.append(dept)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"{_EMPLOYEE_SELECT} {where} ORDER BY {sort_col} {order_sql}"
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


def get_or_create_position(name: str) -> int:
    with _cursor() as cur:
        cur.execute(
            "INSERT INTO positions (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
            (name,),
        )
        cur.execute("SELECT id FROM positions WHERE name = %s", (name,))
        return cur.fetchone()["id"]


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


def get_or_create_department(name: str) -> int:
    with _cursor() as cur:
        cur.execute(
            "INSERT INTO departments (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
            (name,),
        )
        cur.execute("SELECT id FROM departments WHERE name = %s", (name,))
        return cur.fetchone()["id"]


def get_by_id(employee_id: int):
    with _cursor() as cur:
        cur.execute(
            f"{_EMPLOYEE_SELECT} WHERE e.id = %s",
            (employee_id,),
        )
        return cur.fetchone()


def _get_position_name(cur, position_id: int) -> str:
    cur.execute("SELECT name FROM positions WHERE id = %s", (position_id,))
    row = cur.fetchone()
    return row["name"] if row else str(position_id)


def _get_department_name(cur, department_id: int) -> str:
    cur.execute("SELECT name FROM departments WHERE id = %s", (department_id,))
    row = cur.fetchone()
    return row["name"] if row else str(department_id)


def create(full_name: str, position_id: int, department_id: int, email: str, phone: str):
    now = datetime.now(timezone.utc).isoformat()
    with _cursor() as cur:
        cur.execute(
            "INSERT INTO employees (full_name, position_id, department_id, email, phone, created_at, updated_at)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (full_name, position_id, department_id, email, phone, now, now),
        )
        employee_id = cur.fetchone()["id"]
        cur.execute(
            "INSERT INTO employee_history (employee_id, changed_at, change_type)"
            " VALUES (%s, %s, %s)",
            (employee_id, now, "create"),
        )


def update(employee_id: int, full_name: str, position_id: int, department_id: int,
           email: str, phone: str):
    old = get_by_id(employee_id)
    now = datetime.now(timezone.utc).isoformat()
    with _cursor() as cur:
        new_position_name = _get_position_name(cur, position_id)
        new_department_name = _get_department_name(cur, department_id)
        fields = [
            ("full_name", old["full_name"], full_name),
            ("position", old["position"], new_position_name),
            ("department", old["department"], new_department_name),
            ("email", old["email"], email),
            ("phone", old["phone"] or "", phone or ""),
        ]
        cur.execute(
            "UPDATE employees"
            " SET full_name=%s, position_id=%s, department_id=%s, email=%s, phone=%s, updated_at=%s"
            " WHERE id=%s",
            (full_name, position_id, department_id, email, phone, now, employee_id),
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
