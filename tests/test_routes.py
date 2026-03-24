import pytest
import allure
import database

pytestmark = [pytest.mark.routes]


@allure.feature("REST API")
@allure.story("Список сотрудников")
@allure.title("GET /api/employees — пустой список")
@allure.severity(allure.severity_level.NORMAL)
def test_index_empty(client):
    with allure.step("GET /api/employees"):
        resp = client.get("/api/employees")
    with allure.step("Ответ 200, пустой список"):
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["employees"] == []


@allure.feature("REST API")
@allure.story("Список сотрудников")
@allure.title("GET /api/employees — сотрудник в списке")
@allure.severity(allure.severity_level.NORMAL)
def test_index_shows_employees(client, make_employee):
    with allure.step("Создать сотрудника"):
        emp = make_employee()
    with allure.step("GET /api/employees"):
        resp = client.get("/api/employees")
    with allure.step("Сотрудник присутствует в ответе"):
        names = [e["full_name"] for e in resp.get_json()["employees"]]
        assert emp["full_name"] in names


@allure.feature("REST API")
@allure.story("Список сотрудников")
@allure.title("Фильтрация: {params}")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize("params,present,absent", [
    ({"q": "Иван"}, "Иван Иванов", "Пётр Петров"),
    ({"dept": "ИТ-отдел"}, "Иван Иванов", "Пётр Петров"),
])
def test_index_filter(client, make_employee, params, present, absent):
    with allure.step("Создать двух сотрудников из разных отделов"):
        make_employee("Иван Иванов", "Разработчик", "ИТ-отдел")
        make_employee("Пётр Петров", "Менеджер", "Кадры")
    with allure.step(f"GET /api/employees с параметрами {params}"):
        resp = client.get("/api/employees", query_string=params)
        names = [e["full_name"] for e in resp.get_json()["employees"]]
    with allure.step(f"'{present}' есть в ответе, '{absent}' — нет"):
        assert present in names
        assert absent not in names


@allure.feature("REST API")
@allure.story("Создание сотрудника")
@allure.title("POST /api/employees — валидные данные → 201")
@allure.severity(allure.severity_level.CRITICAL)
def test_create_post_valid(client):
    pos_id = database.get_or_create_position("Разработчик")
    dept_id = database.get_or_create_department("ИТ-отдел")
    with allure.step("POST /api/employees с валидными данными"):
        resp = client.post("/api/employees", json={
            "full_name": "Иван Иванов",
            "position_id": pos_id,
            "department_id": dept_id,
            "email": "ivanov@apple.com",
            "phone": "",
        })
    with allure.step("Статус 201"):
        assert resp.status_code == 201
    with allure.step("Запись появилась в БД"):
        assert len(database.get_all()) == 1


@allure.feature("REST API")
@allure.story("Создание сотрудника")
@allure.title("POST /api/employees — невалидные данные: {expected_text}")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.parametrize("data,expected_text", [
    (
        {"full_name": "", "position_id": 1, "department_id": 1, "email": "testerov@tester.fv", "phone": ""},
        "Обязательное",
    ),
    (
        {"full_name": "Иван Иванов", "position_id": 1, "department_id": 1, "email": "not-an-email", "phone": ""},
        "почт",
    ),
    (
        {"full_name": "Иван Иванов", "position_id": 1, "department_id": 1, "email": "testerov@tester.fv", "phone": "abc"},
        "телефон",
    ),
])
def test_create_invalid(client, data, expected_text):
    with allure.step("POST /api/employees с невалидными данными"):
        resp = client.post("/api/employees", json=data)
    with allure.step("Статус 400, ошибка в ответе"):
        assert resp.status_code == 400
        errors = resp.get_json()["errors"]
        assert any(expected_text in v for v in errors.values())


@allure.feature("REST API")
@allure.story("Получение сотрудника")
@allure.title("GET /api/employees/<id> — существующий сотрудник")
@allure.severity(allure.severity_level.NORMAL)
def test_get_existing(client, make_employee):
    with allure.step("Создать сотрудника"):
        emp = make_employee()
    with allure.step(f"GET /api/employees/{emp['id']}"):
        resp = client.get(f"/api/employees/{emp['id']}")
    with allure.step("Ответ 200, данные сотрудника"):
        assert resp.status_code == 200
        assert resp.get_json()["employee"]["full_name"] == emp["full_name"]


@allure.feature("REST API")
@allure.story("Получение сотрудника")
@allure.title("GET /api/employees/<id> — несуществующий ID → 404")
@allure.severity(allure.severity_level.NORMAL)
def test_get_nonexistent(client):
    with allure.step("GET /api/employees/999"):
        resp = client.get("/api/employees/999")
    with allure.step("Статус 404"):
        assert resp.status_code == 404


@allure.feature("REST API")
@allure.story("Обновление сотрудника")
@allure.title("PUT /api/employees/<id> — валидные данные → обновление")
@allure.severity(allure.severity_level.CRITICAL)
def test_update_valid(client, make_employee):
    with allure.step("Создать сотрудника"):
        emp = make_employee()
    pos_id = database.get_or_create_position("Менеджер")
    dept_id = database.get_or_create_department("Кадры")
    with allure.step(f"PUT /api/employees/{emp['id']}"):
        resp = client.put(f"/api/employees/{emp['id']}", json={
            "full_name": "Пётр Петров",
            "position_id": pos_id,
            "department_id": dept_id,
            "email": "new@email.com",
            "phone": "",
        })
    with allure.step("Статус 200"):
        assert resp.status_code == 200
    with allure.step("Данные обновлены в БД"):
        assert database.get_by_id(emp["id"])["full_name"] == "Пётр Петров"


@allure.feature("REST API")
@allure.story("Обновление сотрудника")
@allure.title("PUT /api/employees/<id> — невалидные данные: {expected_text}")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.parametrize("data,expected_text", [
    (
        {"full_name": "", "position_id": 1, "department_id": 1, "email": "manager@ozon.ru", "phone": ""},
        "Обязательное",
    ),
    (
        {"full_name": "Иван Иванов", "position_id": 1, "department_id": 1, "email": "bad@fgbf", "phone": ""},
        "почт",
    ),
    (
        {"full_name": "Иван Иванов", "position_id": 1, "department_id": 1, "email": "ivanov@rtk.com", "phone": "abc"},
        "телефон",
    ),
])
def test_update_invalid(client, make_employee, data, expected_text):
    with allure.step("Создать сотрудника"):
        emp = make_employee()
    with allure.step(f"PUT /api/employees/{emp['id']} с невалидными данными"):
        resp = client.put(f"/api/employees/{emp['id']}", json=data)
    with allure.step("Статус 400, ошибка в ответе"):
        assert resp.status_code == 400
        errors = resp.get_json()["errors"]
        assert any(expected_text in v for v in errors.values())


@allure.feature("REST API")
@allure.story("Удаление сотрудника")
@allure.title("DELETE /api/employees/<id> — существующий сотрудник удаляется")
@allure.severity(allure.severity_level.CRITICAL)
def test_delete_existing(client, make_employee):
    with allure.step("Создать сотрудника"):
        emp = make_employee()
    with allure.step(f"DELETE /api/employees/{emp['id']}"):
        resp = client.delete(f"/api/employees/{emp['id']}")
    with allure.step("Статус 200, запись удалена"):
        assert resp.status_code == 200
        assert database.get_by_id(emp["id"]) is None


@allure.feature("REST API")
@allure.story("Удаление сотрудника")
@allure.title("DELETE /api/employees/<id> — несуществующий ID → 200")
@allure.severity(allure.severity_level.MINOR)
def test_delete_nonexistent(client):
    with allure.step("DELETE /api/employees/999"):
        resp = client.delete("/api/employees/999")
    with allure.step("Статус 200"):
        assert resp.status_code == 200


@allure.feature("REST API")
@allure.story("Справочник должностей")
@allure.title("GET /api/positions — список")
@allure.severity(allure.severity_level.NORMAL)
def test_positions_get(client):
    with allure.step("GET /api/positions"):
        resp = client.get("/api/positions")
    with allure.step("Ответ 200"):
        assert resp.status_code == 200
        assert "positions" in resp.get_json()


@allure.feature("REST API")
@allure.story("Справочник должностей")
@allure.title("POST /api/positions — создаёт должность")
@allure.severity(allure.severity_level.CRITICAL)
def test_positions_create(client):
    with allure.step("POST /api/positions"):
        resp = client.post("/api/positions", json={"name": "Разработчик"})
    with allure.step("Статус 201"):
        assert resp.status_code == 201
    with allure.step("Запись появилась в БД"):
        names = [r["name"] for r in database.get_all_positions()]
        assert "Разработчик" in names


@allure.feature("REST API")
@allure.story("Справочник должностей")
@allure.title("POST /api/positions — дубликат → ошибка")
@allure.severity(allure.severity_level.CRITICAL)
def test_positions_create_duplicate(client):
    with allure.step("Создать должность первый раз"):
        client.post("/api/positions", json={"name": "Менеджер"})
    with allure.step("Попытаться создать дубль"):
        resp = client.post("/api/positions", json={"name": "Менеджер"})
    with allure.step("Ошибка в ответе"):
        assert resp.status_code == 400
        assert "уже существует" in resp.get_json()["error"]


@allure.feature("REST API")
@allure.story("Справочник должностей")
@allure.title("POST /api/positions — пустое имя → ошибка")
@allure.severity(allure.severity_level.NORMAL)
def test_positions_create_empty_name(client):
    with allure.step("POST с пустым именем"):
        resp = client.post("/api/positions", json={"name": ""})
    with allure.step("Ошибка в ответе"):
        assert resp.status_code == 400
        assert "пустым" in resp.get_json()["error"]


@allure.feature("REST API")
@allure.story("Справочник должностей")
@allure.title("PUT /api/positions/<id> — обновляет")
@allure.severity(allure.severity_level.CRITICAL)
def test_positions_edit(client):
    with allure.step("Создать должность"):
        database.create_position("Стажёр")
        pos = database.get_all_positions()[0]
    with allure.step("PUT"):
        resp = client.put(f"/api/positions/{pos['id']}", json={"name": "Специалист"})
    with allure.step("Статус 200"):
        assert resp.status_code == 200
    with allure.step("Название обновлено в БД"):
        updated = database.get_position_by_id(pos["id"])
        assert updated["name"] == "Специалист"


@allure.feature("REST API")
@allure.story("Справочник должностей")
@allure.title("DELETE /api/positions/<id> — удаляет")
@allure.severity(allure.severity_level.CRITICAL)
def test_positions_delete(client):
    with allure.step("Создать должность"):
        database.create_position("Временная")
        pos = database.get_all_positions()[0]
    with allure.step("DELETE"):
        resp = client.delete(f"/api/positions/{pos['id']}")
    with allure.step("Статус 200, запись удалена"):
        assert resp.status_code == 200
        assert database.get_position_by_id(pos["id"]) is None


@allure.feature("REST API")
@allure.story("Справочник отделов")
@allure.title("GET /api/departments — список")
@allure.severity(allure.severity_level.NORMAL)
def test_departments_get(client):
    with allure.step("GET /api/departments"):
        resp = client.get("/api/departments")
    with allure.step("Ответ 200"):
        assert resp.status_code == 200
        assert "departments" in resp.get_json()


@allure.feature("REST API")
@allure.story("Справочник отделов")
@allure.title("POST /api/departments — создаёт отдел")
@allure.severity(allure.severity_level.CRITICAL)
def test_departments_create(client):
    with allure.step("POST /api/departments"):
        resp = client.post("/api/departments", json={"name": "ИТ-отдел"})
    with allure.step("Статус 201"):
        assert resp.status_code == 201
    with allure.step("Запись появилась в БД"):
        names = [r["name"] for r in database.get_all_departments()]
        assert "ИТ-отдел" in names


@allure.feature("REST API")
@allure.story("Справочник отделов")
@allure.title("POST /api/departments — дубликат → ошибка")
@allure.severity(allure.severity_level.CRITICAL)
def test_departments_create_duplicate(client):
    with allure.step("Создать отдел"):
        client.post("/api/departments", json={"name": "Кадры"})
    with allure.step("Попытаться создать дубль"):
        resp = client.post("/api/departments", json={"name": "Кадры"})
    with allure.step("Ошибка в ответе"):
        assert resp.status_code == 400
        assert "уже существует" in resp.get_json()["error"]


@allure.feature("REST API")
@allure.story("Справочник отделов")
@allure.title("PUT /api/departments/<id> — обновляет")
@allure.severity(allure.severity_level.CRITICAL)
def test_departments_edit(client):
    with allure.step("Создать отдел"):
        database.create_department("Бухгалтерия")
        dept = database.get_all_departments()[0]
    with allure.step("PUT"):
        resp = client.put(f"/api/departments/{dept['id']}", json={"name": "Финансы"})
    with allure.step("Статус 200"):
        assert resp.status_code == 200
    with allure.step("Название обновлено в БД"):
        updated = database.get_department_by_id(dept["id"])
        assert updated["name"] == "Финансы"


@allure.feature("REST API")
@allure.story("Справочник отделов")
@allure.title("DELETE /api/departments/<id> — удаляет")
@allure.severity(allure.severity_level.CRITICAL)
def test_departments_delete(client):
    with allure.step("Создать отдел"):
        database.create_department("Временный")
        dept = database.get_all_departments()[0]
    with allure.step("DELETE"):
        resp = client.delete(f"/api/departments/{dept['id']}")
    with allure.step("Статус 200, запись удалена"):
        assert resp.status_code == 200
        assert database.get_department_by_id(dept["id"]) is None


@allure.feature("REST API")
@allure.story("Интеграция")
@allure.title("GET /api/employees/<id> содержит должности из справочника")
@allure.severity(allure.severity_level.NORMAL)
def test_get_employee_has_positions(client, make_employee):
    with allure.step("Добавить должность в справочник"):
        database.create_position("DevOps-инженер")
    with allure.step("Создать сотрудника"):
        emp = make_employee()
    with allure.step(f"GET /api/employees/{emp['id']}"):
        resp = client.get(f"/api/employees/{emp['id']}")
    with allure.step("Должности присутствуют в ответе"):
        pos_names = [p["name"] for p in resp.get_json()["positions"]]
        assert "DevOps-инженер" in pos_names


@allure.feature("REST API")
@allure.story("Идемпотентность")
@allure.title("Повторное создание сотрудника с тем же email невозможно")
@allure.severity(allure.severity_level.CRITICAL)
def test_create_duplicate_email(client):
    email = "ivan@example.com"

    pos1_id = database.get_or_create_position("Разработчик")
    dept1_id = database.get_or_create_department("ИТ-отдел")
    pos2_id = database.get_or_create_position("Менеджер")
    dept2_id = database.get_or_create_department("Кадры")

    with allure.step("Создать первого сотрудника"):
        resp = client.post("/api/employees", json={
            "full_name": "Иван Иванов",
            "position_id": pos1_id,
            "department_id": dept1_id,
            "email": email,
            "phone": "",
        })
        assert resp.status_code == 201

    with allure.step("Попытаться создать второго сотрудника с тем же email"):
        resp = client.post("/api/employees", json={
            "full_name": "Другой Человек",
            "position_id": pos2_id,
            "department_id": dept2_id,
            "email": email,
            "phone": "",
        })

    with allure.step("Ошибка 400 с сообщением о дубликате"):
        assert resp.status_code == 400
        assert "уже существует" in resp.get_json()["errors"]["email"]

    with allure.step("В БД по-прежнему один сотрудник"):
        assert len(database.get_all()) == 1


# ── История изменений ────────────────────────────────────────────────────────

@allure.feature("REST API")
@allure.story("История изменений")
@allure.title("GET /api/employees/<id>/history — существующий сотрудник")
@allure.severity(allure.severity_level.NORMAL)
def test_history_get_existing(client, make_employee):
    with allure.step("Создать сотрудника в БД"):
        emp = make_employee()
    with allure.step("GET /api/employees/<id>/history"):
        resp = client.get(f"/api/employees/{emp['id']}/history")
    with allure.step("Ответ 200"):
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["employee"]["full_name"] == emp["full_name"]
        assert "records" in data


@allure.feature("REST API")
@allure.story("История изменений")
@allure.title("GET /api/employees/999/history — несуществующий ID → 404")
@allure.severity(allure.severity_level.NORMAL)
def test_history_get_nonexistent(client):
    with allure.step("GET /api/employees/999/history"):
        resp = client.get("/api/employees/999/history")
    with allure.step("Статус 404"):
        assert resp.status_code == 404
