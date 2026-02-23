import pytest
from faker import Faker
import database
from app import app as flask_app

fake = Faker("ru_RU")


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", db_file)
    database.init_db()


@pytest.fixture
def client(setup_db):
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def make_employee():
    def _make(full_name=None, position=None, department=None, email=None, phone=""):
        full_name = full_name or fake.name()[:50]
        position = position or fake.job()[:50]
        department = department or fake.company()[:50]
        email = email or fake.email()
        database.create(full_name, position, department, email, phone)
        with database.get_connection() as conn:
            return conn.execute(
                "SELECT * FROM employees ORDER BY id DESC LIMIT 1"
            ).fetchone()
    return _make
