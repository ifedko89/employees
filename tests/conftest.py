import concurrent.futures
import threading

import grpc
import pytest
from faker import Faker
from werkzeug.serving import make_server

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
def live_server(setup_db):
    """Запускает Flask на случайном порту в фоновом потоке."""
    server = make_server("127.0.0.1", 0, flask_app)
    port = server.socket.getsockname()[1]
    t = threading.Thread(target=server.serve_forever)
    t.daemon = True
    t.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


@pytest.fixture
def pw_page(live_server):
    """Открывает браузер Chromium и возвращает (page, base_url)."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        yield page, live_server
        browser.close()


@pytest.fixture
def make_employee():
    def _make(full_name=None, position=None, department=None, email=None, phone=""):
        full_name = full_name or fake.name()[:50]
        pos_name = position or fake.job()[:50]
        dept_name = department or fake.company()[:50]
        email = email or fake.email()
        pos_id = database.get_or_create_position(pos_name)
        dept_id = database.get_or_create_department(dept_name)
        database.create(full_name, pos_id, dept_id, email, phone)
        with database._cursor() as cur:
            cur.execute("""
                SELECT e.id, e.full_name,
                       p.name AS position, p.id AS position_id,
                       d.name AS department, d.id AS department_id,
                       e.email, e.phone, e.created_at, e.updated_at
                FROM employees e
                JOIN positions p ON p.id = e.position_id
                JOIN departments d ON d.id = e.department_id
                ORDER BY e.id DESC LIMIT 1
            """)
            return cur.fetchone()
    return _make
