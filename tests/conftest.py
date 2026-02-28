import concurrent.futures

import grpc
import pytest
from faker import Faker

import database
import employees_pb2_grpc
import grpc_server
import app as flask_app_module
from app import app as flask_app

fake = Faker("ru_RU")


@pytest.fixture(autouse=True)
def setup_db(postgresql, monkeypatch):
    info = postgresql.info
    dsn = f"postgresql://{info.user}@{info.host}:{info.port}/{info.dbname}"
    monkeypatch.setattr(database, "DATABASE_URL", dsn)
    database.init_db()

    server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=2))
    employees_pb2_grpc.add_EmployeesServiceServicer_to_server(
        grpc_server.EmployeesServicer(), server
    )
    port = server.add_insecure_port("[::]:0")
    server.start()

    channel = grpc.insecure_channel(f"localhost:{port}")
    monkeypatch.setattr(flask_app_module, "stub",
                        employees_pb2_grpc.EmployeesServiceStub(channel))
    yield
    server.stop(0)


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
        with database._cursor() as cur:
            cur.execute("SELECT * FROM employees ORDER BY id DESC LIMIT 1")
            return cur.fetchone()
    return _make
