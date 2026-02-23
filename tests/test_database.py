import pytest
import allure
import database


@allure.feature("База данных")
@allure.story("CRUD")
@allure.title("Создание записи и получение по ID")
@allure.severity(allure.severity_level.CRITICAL)
def test_create_and_get_by_id(make_employee):
    with allure.step("Создать сотрудника"):
        emp = make_employee()
    with allure.step("Получить по ID и проверить поля"):
        result = database.get_by_id(emp["id"])
        assert result is not None
        assert result["full_name"] == emp["full_name"]
        assert result["position"] == emp["position"]
        assert result["department"] == emp["department"]
        assert result["email"] == emp["email"]


@allure.feature("База данных")
@allure.story("CRUD")
@allure.title("Обновление записи")
@allure.severity(allure.severity_level.CRITICAL)
def test_update(make_employee):
    with allure.step("Создать сотрудника"):
        emp = make_employee()
    with allure.step("Обновить все поля"):
        database.update(emp["id"], "Пётр Петров", "Менеджер", "HR", "p2@p2.com", "+7 999 000 00 00")
    with allure.step("Проверить изменения в БД"):
        updated = database.get_by_id(emp["id"])
        assert updated["full_name"] == "Пётр Петров"
        assert updated["position"] == "Менеджер"
        assert updated["department"] == "HR"
        assert updated["email"] == "p2@p2.com"


@allure.feature("База данных")
@allure.story("CRUD")
@allure.title("Удаление записи")
@allure.severity(allure.severity_level.CRITICAL)
def test_delete(make_employee):
    with allure.step("Создать сотрудника"):
        emp = make_employee()
    with allure.step("Удалить сотрудника"):
        database.delete(emp["id"])
    with allure.step("Убедиться что запись не существует"):
        assert database.get_by_id(emp["id"]) is None


@allure.feature("База данных")
@allure.story("Поиск и фильтрация")
@allure.title("Получение всех записей без фильтров")
@allure.severity(allure.severity_level.NORMAL)
def test_get_all_no_filter(make_employee):
    with allure.step("Создать двух сотрудников"):
        make_employee("А Аааов", "Разработчик", "ИТ")
        make_employee("Б Бббов", "Менеджер", "HR")
    with allure.step("Получить всех и проверить количество"):
        rows = database.get_all()
        assert len(rows) == 2


@allure.feature("База данных")
@allure.story("Поиск и фильтрация")
@allure.title("Поиск по полю '{search}'")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize("search,expected_name", [
    ("Иван", "Иван Иванов"),
    ("Разработчик", "Иван Иванов"),
    ("ИТ", "Иван Иванов"),
])
def test_get_all_search(make_employee, search, expected_name):
    with allure.step("Создать двух сотрудников"):
        make_employee("Иван Иванов", "Разработчик", "ИТ")
        make_employee("Пётр Петров", "Менеджер", "HR")
    with allure.step(f"Поиск по запросу '{search}'"):
        rows = database.get_all(search=search)
    with allure.step("Проверить что найден ровно один подходящий сотрудник"):
        assert len(rows) == 1
        assert rows[0]["full_name"] == expected_name


@allure.feature("База данных")
@allure.story("Поиск и фильтрация")
@allure.title("Фильтрация по отделу")
@allure.severity(allure.severity_level.NORMAL)
def test_get_all_filter_by_dept(make_employee):
    with allure.step("Создать сотрудников из разных отделов"):
        make_employee("Иван Иванов", "Разработчик", "ИТ")
        make_employee("Пётр Петров", "Менеджер", "HR")
    with allure.step("Отфильтровать по отделу ИТ"):
        rows = database.get_all(dept="ИТ")
    with allure.step("Проверить что возвращён только сотрудник из ИТ"):
        assert len(rows) == 1
        assert rows[0]["department"] == "ИТ"


@allure.feature("База данных")
@allure.story("Сортировка")
@allure.title("Сортировка по full_name, порядок: {order}")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize("order,expected_first", [
    ("asc", "А Аааов"),
    ("desc", "Б Бббов"),
])
def test_get_all_sort_and_order(make_employee, order, expected_first):
    with allure.step("Создать сотрудников"):
        make_employee("Б Бббов", "Разработчик", "ИТ")
        make_employee("А Аааов", "Менеджер", "HR")
    with allure.step(f"Получить список с order={order}"):
        rows = database.get_all(sort="full_name", order=order)
    with allure.step(f"Первый в списке должен быть '{expected_first}'"):
        assert rows[0]["full_name"] == expected_first


@allure.feature("База данных")
@allure.story("Сортировка")
@allure.title("Невалидный sort — fallback на full_name")
@allure.severity(allure.severity_level.MINOR)
def test_get_all_invalid_sort(make_employee):
    with allure.step("Создать сотрудника"):
        make_employee()
    with allure.step("Запросить с невалидным полем сортировки"):
        rows = database.get_all(sort="invalid_field")
    with allure.step("Запрос не упал, данные возвращены"):
        assert len(rows) == 1


@allure.feature("База данных")
@allure.story("Справочники")
@allure.title("Получение уникальных отделов в алфавитном порядке")
@allure.severity(allure.severity_level.NORMAL)
def test_get_departments(make_employee):
    with allure.step("Создать сотрудников из двух отделов (ИТ дважды)"):
        make_employee("Иван Иванов", "Разработчик", "ИТ")
        make_employee("Пётр Петров", "Менеджер", "HR")
        make_employee("Анна Аннова", "Дизайнер", "ИТ")
    with allure.step("Получить список отделов"):
        depts = database.get_departments()
    with allure.step("Проверить уникальность и порядок"):
        assert depts == ["HR", "ИТ"]
