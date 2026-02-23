import pytest
import allure
import database


@allure.feature("HTTP-маршруты")
@allure.story("Список сотрудников")
@allure.title("Главная страница — пустой список")
@allure.severity(allure.severity_level.NORMAL)
def test_index_empty(client):
    with allure.step("GET /"):
        resp = client.get("/")
    with allure.step("Ответ 200"):
        assert resp.status_code == 200


@allure.feature("HTTP-маршруты")
@allure.story("Список сотрудников")
@allure.title("Главная страница — сотрудник отображается в таблице")
@allure.severity(allure.severity_level.NORMAL)
def test_index_shows_employees(client, make_employee):
    with allure.step("Создать сотрудника"):
        emp = make_employee()
    with allure.step("GET /"):
        resp = client.get("/")
    with allure.step("Имя сотрудника присутствует в HTML"):
        assert emp["full_name"] in resp.data.decode()


@allure.feature("HTTP-маршруты")
@allure.story("Список сотрудников")
@allure.title("Фильтрация: {url}")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize("url,present,absent", [
    ("/?q=Иван", "Иван Иванов", "Пётр Петров"),
    ("/?dept=ИТ-отдел", "Иван Иванов", "Пётр Петров"),
])
def test_index_filter(client, make_employee, url, present, absent):
    with allure.step("Создать двух сотрудников из разных отделов"):
        make_employee("Иван Иванов", "Разработчик", "ИТ-отдел")
        make_employee("Пётр Петров", "Менеджер", "Кадры")
    with allure.step(f"GET {url}"):
        resp = client.get(url)
        data = resp.data.decode()
    with allure.step(f"'{present}' есть в ответе, '{absent}' — нет"):
        assert present in data
        assert absent not in data


@allure.feature("HTTP-маршруты")
@allure.story("Создание сотрудника")
@allure.title("GET /create — форма открывается")
@allure.severity(allure.severity_level.MINOR)
def test_create_get(client):
    with allure.step("GET /create"):
        resp = client.get("/create")
    with allure.step("Ответ 200"):
        assert resp.status_code == 200


@allure.feature("HTTP-маршруты")
@allure.story("Создание сотрудника")
@allure.title("POST /create — валидные данные → редирект и запись в БД")
@allure.severity(allure.severity_level.CRITICAL)
def test_create_post_valid(client):
    with allure.step("POST /create с валидными данными"):
        resp = client.post("/create", data={
            "full_name": "Иван Иванов",
            "position": "Разработчик",
            "department": "ИТ-отдел",
            "email": "ivanov@apple.com",
            "phone": "",
        })
    with allure.step("Редирект 302"):
        assert resp.status_code == 302
    with allure.step("Запись появилась в БД"):
        assert len(database.get_all()) == 1


@allure.feature("HTTP-маршруты")
@allure.story("Создание сотрудника")
@allure.title("POST /create — невалидные данные: {expected_text}")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.parametrize("data,expected_text", [
    (
        {"full_name": "", "position": "Разработчик", "department": "ИТ-отдел", "email": "testerov@tester.fv", "phone": ""},
        "обязательные",
    ),
    (
        {"full_name": "Иван Иванов", "position": "Разработчик", "department": "ИТ-отдел", "email": "not-an-email", "phone": ""},
        "почт",
    ),
    (
        {"full_name": "Иван Иванов", "position": "Разработчик", "department": "ИТ-отдел", "email": "testerov@tester.fv", "phone": "abc"},
        "телефон",
    ),
])
def test_create_invalid(client, data, expected_text):
    with allure.step("POST /create с невалидными данными"):
        resp = client.post("/create", data=data)
    with allure.step("Форма перерисована (200), сообщение об ошибке в HTML"):
        assert resp.status_code == 200
        assert expected_text in resp.data.decode()


@allure.feature("HTTP-маршруты")
@allure.story("Редактирование сотрудника")
@allure.title("GET /edit/<id> — форма заполнена данными сотрудника")
@allure.severity(allure.severity_level.NORMAL)
def test_edit_get_existing(client, make_employee):
    with allure.step("Создать сотрудника"):
        emp = make_employee()
    with allure.step(f"GET /edit/{emp['id']}"):
        resp = client.get(f"/edit/{emp['id']}")
    with allure.step("Ответ 200, данные сотрудника в HTML"):
        assert resp.status_code == 200
        assert emp["full_name"] in resp.data.decode()


@allure.feature("HTTP-маршруты")
@allure.story("Редактирование сотрудника")
@allure.title("GET /edit/<id> — несуществующий ID → редирект")
@allure.severity(allure.severity_level.NORMAL)
def test_edit_get_nonexistent(client):
    with allure.step("GET /edit/999"):
        resp = client.get("/edit/999")
    with allure.step("Редирект 302 на главную"):
        assert resp.status_code == 302


@allure.feature("HTTP-маршруты")
@allure.story("Редактирование сотрудника")
@allure.title("POST /edit/<id> — валидные данные → обновление и редирект")
@allure.severity(allure.severity_level.CRITICAL)
def test_edit_post_valid(client, make_employee):
    with allure.step("Создать сотрудника"):
        emp = make_employee()
    with allure.step(f"POST /edit/{emp['id']} с новыми данными"):
        resp = client.post(f"/edit/{emp['id']}", data={
            "full_name": "Пётр Петров",
            "position": "Менеджер",
            "department": "Кадры",
            "email": "new@email.com",
            "phone": "",
        })
    with allure.step("Редирект 302"):
        assert resp.status_code == 302
    with allure.step("Данные обновлены в БД"):
        assert database.get_by_id(emp["id"])["full_name"] == "Пётр Петров"


@allure.feature("HTTP-маршруты")
@allure.story("Редактирование сотрудника")
@allure.title("POST /edit/<id> — невалидные данные: {expected_text}")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.parametrize("data,expected_text", [
    (
        {"full_name": "", "position": "Менеджер", "department": "Кадры", "email": "manager@ozon.ru", "phone": ""},
        "обязательные",
    ),
    (
        {"full_name": "Иван Иванов", "position": "Разработчик", "department": "ИТ-отдел", "email": "bad@fgbf", "phone": ""},
        "почт",
    ),
    (
        {"full_name": "Иван Иванов", "position": "Разработчик", "department": "ИТ-отдел", "email": "ivanov@rtk.com", "phone": "abc"},
        "телефон",
    ),
])
def test_edit_post_invalid(client, make_employee, data, expected_text):
    with allure.step("Создать сотрудника"):
        emp = make_employee()
    with allure.step(f"POST /edit/{emp['id']} с невалидными данными"):
        resp = client.post(f"/edit/{emp['id']}", data=data)
    with allure.step("Форма перерисована (200), сообщение об ошибке в HTML"):
        assert resp.status_code == 200
        assert expected_text in resp.data.decode()


@allure.feature("HTTP-маршруты")
@allure.story("Удаление сотрудника")
@allure.title("POST /delete/<id> — существующий сотрудник удаляется")
@allure.severity(allure.severity_level.CRITICAL)
def test_delete_existing(client, make_employee):
    with allure.step("Создать сотрудника"):
        emp = make_employee()
    with allure.step(f"POST /delete/{emp['id']}"):
        resp = client.post(f"/delete/{emp['id']}")
    with allure.step("Редирект 302, запись удалена из БД"):
        assert resp.status_code == 302
        assert database.get_by_id(emp["id"]) is None


@allure.feature("HTTP-маршруты")
@allure.story("Удаление сотрудника")
@allure.title("POST /delete/<id> — несуществующий ID → редирект без ошибки")
@allure.severity(allure.severity_level.MINOR)
def test_delete_nonexistent(client):
    with allure.step("POST /delete/999"):
        resp = client.post("/delete/999")
    with allure.step("Редирект 302, без краша"):
        assert resp.status_code == 302


@allure.feature("HTTP-маршруты")
@allure.story("Идемпотентность")
@allure.title("Повторное создание сотрудника с тем же email невозможно")
@allure.severity(allure.severity_level.CRITICAL)
def test_create_duplicate_email(client):
    email = "ivan@example.com"

    with allure.step("Создать первого сотрудника"):
        resp = client.post("/create", data={
            "full_name": "Иван Иванов",
            "position": "Разработчик",
            "department": "ИТ-отдел",
            "email": email,
            "phone": "",
        })
        assert resp.status_code == 302

    with allure.step("Попытаться создать второго сотрудника с тем же email"):
        resp = client.post("/create", data={
            "full_name": "Другой Человек",
            "position": "Менеджер",
            "department": "Кадры",
            "email": email,
            "phone": "",
        })

    with allure.step("Форма возвращена с ошибкой (200)"):
        assert resp.status_code == 200
        assert "уже существует" in resp.data.decode()

    with allure.step("В БД по-прежнему один сотрудник"):
        assert len(database.get_all()) == 1
