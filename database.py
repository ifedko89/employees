import os
import random
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from datetime import datetime, timezone

_LAST_NAMES = [
    "Иванов", "Петров", "Сидоров", "Кузнецов", "Смирнов",
    "Попов", "Волков", "Козлов", "Новиков", "Морозов",
    "Соловьёв", "Васильев", "Зайцев", "Павлов", "Семёнов",
    "Голубев", "Виноградов", "Богданов", "Воробьёв", "Фёдоров",
    "Михайлов", "Беляев", "Тарасов", "Белов", "Комаров",
    "Орлов", "Киселёв", "Макаров", "Андреев", "Ковалёв",
]

_FIRST_NAMES_M = [
    "Александр", "Дмитрий", "Максим", "Сергей", "Андрей",
    "Алексей", "Артём", "Илья", "Кирилл", "Михаил",
    "Никита", "Матвей", "Роман", "Егор", "Иван",
]

_FIRST_NAMES_F = [
    "Анна", "Мария", "Елена", "Ольга", "Наталья",
    "Татьяна", "Ирина", "Светлана", "Екатерина", "Юлия",
    "Дарья", "Алина", "Виктория", "Полина", "Ксения",
]

_PATRONYMICS_M = [
    "Александрович", "Дмитриевич", "Сергеевич", "Андреевич", "Алексеевич",
    "Михайлович", "Иванович", "Николаевич", "Владимирович", "Петрович",
    "Олегович", "Павлович", "Юрьевич", "Викторович", "Евгеньевич",
]

_PATRONYMICS_F = [
    "Александровна", "Дмитриевна", "Сергеевна", "Андреевна", "Алексеевна",
    "Михайловна", "Ивановна", "Николаевна", "Владимировна", "Петровна",
    "Олеговна", "Павловна", "Юрьевна", "Викторовна", "Евгеньевна",
]

_SEED_POSITIONS = [
    "Разработчик", "Аналитик", "Менеджер", "Тестировщик", "Дизайнер",
    "DevOps-инженер", "Системный администратор", "Бизнес-аналитик",
    "Руководитель проекта", "Технический писатель",
]

_SEED_DEPARTMENTS = [
    "IT", "Бухгалтерия", "HR", "Маркетинг", "Продажи",
    "Логистика", "Юридический", "Техподдержка",
]

_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def _transliterate(text: str) -> str:
    result = []
    for ch in text.lower():
        result.append(_TRANSLIT.get(ch, ch))
    return "".join(result)


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

        _seed_employees(cur)


def _seed_employees(cur):
    cur.execute("SELECT COUNT(*) AS cnt FROM employees")
    if cur.fetchone()["cnt"] > 0:
        return

    for name in _SEED_POSITIONS:
        cur.execute(
            "INSERT INTO positions (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
            (name,),
        )
    for name in _SEED_DEPARTMENTS:
        cur.execute(
            "INSERT INTO departments (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
            (name,),
        )

    cur.execute("SELECT id, name FROM positions")
    positions = [(r["id"], r["name"]) for r in cur.fetchall()]
    cur.execute("SELECT id, name FROM departments")
    departments = [(r["id"], r["name"]) for r in cur.fetchall()]

    now = datetime.now(timezone.utc).isoformat()
    employees_data = []
    history_data = []

    for i in range(1, 1001):
        is_male = random.random() < 0.5
        last_name = random.choice(_LAST_NAMES)
        if is_male:
            first_name = random.choice(_FIRST_NAMES_M)
            patronymic = random.choice(_PATRONYMICS_M)
        else:
            last_name_f = last_name + "а" if not last_name.endswith("о") else last_name
            last_name = last_name_f
            first_name = random.choice(_FIRST_NAMES_F)
            patronymic = random.choice(_PATRONYMICS_F)

        full_name = f"{last_name} {first_name} {patronymic}"
        pos_id, pos_name = random.choice(positions)
        dept_id, dept_name = random.choice(departments)
        email = f"{_transliterate(last_name)}{i}@example.com"
        phone = "+7 9{:02d} {:03d}-{:02d}-{:02d}".format(
            random.randint(0, 99),
            random.randint(0, 999),
            random.randint(0, 99),
            random.randint(0, 99),
        )
        employees_data.append((full_name, pos_id, dept_id, email, phone, now, now))

    cur.executemany(
        "INSERT INTO employees (full_name, position_id, department_id, email, phone, created_at, updated_at)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s)",
        employees_data,
    )

    cur.execute("SELECT id FROM employees ORDER BY id")
    emp_ids = [r["id"] for r in cur.fetchall()]
    for emp_id in emp_ids:
        history_data.append((emp_id, now, "create"))

    cur.executemany(
        "INSERT INTO employee_history (employee_id, changed_at, change_type)"
        " VALUES (%s, %s, %s)",
        history_data,
    )


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
            order: str = "asc", dept: str = "",
            limit: int = 0, offset: int = 0) -> dict:
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

    with _cursor() as cur:
        cur.execute(
            f"SELECT COUNT(*) AS cnt FROM employees e "
            f"JOIN positions p ON p.id = e.position_id "
            f"JOIN departments d ON d.id = e.department_id {where}",
            params,
        )
        total = cur.fetchone()["cnt"]

        sql = f"{_EMPLOYEE_SELECT} {where} ORDER BY {sort_col} {order_sql}"
        if limit > 0:
            sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"
        cur.execute(sql, params)
        return {"rows": cur.fetchall(), "total": total}


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
