import pytest
import allure
import database

pytestmark = [pytest.mark.db]


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
        pos_id = database.get_or_create_position("Менеджер")
        dept_id = database.get_or_create_department("HR")
        database.update(emp["id"], "Пётр Петров", pos_id, dept_id, "p2@p2.com", "+7 999 000 00 00")
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
        result = database.get_all()
        assert result["total"] == 2


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
        result = database.get_all(search=search)
    with allure.step("Проверить что найден ровно один подходящий сотрудник"):
        assert result["total"] == 1
        assert result["rows"][0]["full_name"] == expected_name


@allure.feature("База данных")
@allure.story("Поиск и фильтрация")
@allure.title("Фильтрация по отделу")
@allure.severity(allure.severity_level.NORMAL)
def test_get_all_filter_by_dept(make_employee):
    with allure.step("Создать сотрудников из разных отделов"):
        make_employee("Иван Иванов", "Разработчик", "ИТ")
        make_employee("Пётр Петров", "Менеджер", "HR")
    with allure.step("Отфильтровать по отделу ИТ"):
        result = database.get_all(dept="ИТ")
    with allure.step("Проверить что возвращён только сотрудник из ИТ"):
        assert result["total"] == 1
        assert result["rows"][0]["department"] == "ИТ"


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
        result = database.get_all(sort="full_name", order=order)
    with allure.step(f"Первый в списке должен быть '{expected_first}'"):
        assert result["rows"][0]["full_name"] == expected_first


@allure.feature("База данных")
@allure.story("Сортировка")
@allure.title("Невалидный sort — fallback на full_name")
@allure.severity(allure.severity_level.MINOR)
def test_get_all_invalid_sort(make_employee):
    with allure.step("Создать сотрудника"):
        make_employee()
    with allure.step("Запросить с невалидным полем сортировки"):
        result = database.get_all(sort="invalid_field")
    with allure.step("Запрос не упал, данные возвращены"):
        assert result["total"] == 1


@allure.feature("База данных")
@allure.story("Справочники")
@allure.title("Получение уникальных отделов в алфавитном порядке")
@allure.severity(allure.severity_level.NORMAL)
def test_get_departments():
    with allure.step("Создать отделы напрямую в справочнике"):
        database.create_department("ИТ")
        database.create_department("HR")
    with allure.step("Получить список отделов"):
        depts = database.get_departments()
    with allure.step("Проверить уникальность и порядок"):
        assert depts == ["HR", "ИТ"]


# --- Positions ---

@allure.feature("База данных")
@allure.story("Справочник должностей")
@allure.title("Создание должности и получение всех")
@allure.severity(allure.severity_level.CRITICAL)
def test_position_create_and_get_all():
    with allure.step("Создать две должности"):
        database.create_position("Разработчик")
        database.create_position("Менеджер")
    with allure.step("Получить все должности"):
        items = database.get_all_positions()
    with allure.step("Проверить наличие обеих должностей"):
        names = [r["name"] for r in items]
        assert "Разработчик" in names
        assert "Менеджер" in names


@allure.feature("База данных")
@allure.story("Справочник должностей")
@allure.title("Получение должности по ID")
@allure.severity(allure.severity_level.NORMAL)
def test_position_get_by_id():
    with allure.step("Создать должность"):
        database.create_position("Аналитик")
    with allure.step("Получить все и взять первую"):
        items = database.get_all_positions()
        pos_id = items[0]["id"]
    with allure.step("Получить по ID"):
        pos = database.get_position_by_id(pos_id)
        assert pos is not None
        assert pos["name"] == "Аналитик"


@allure.feature("База данных")
@allure.story("Справочник должностей")
@allure.title("Обновление должности")
@allure.severity(allure.severity_level.CRITICAL)
def test_position_update():
    with allure.step("Создать должность"):
        database.create_position("Тестировщик")
        items = database.get_all_positions()
        pos_id = items[0]["id"]
    with allure.step("Обновить название"):
        database.update_position(pos_id, "QA-инженер")
    with allure.step("Проверить изменение"):
        pos = database.get_position_by_id(pos_id)
        assert pos["name"] == "QA-инженер"

@allure.feature("База данных")
@allure.story("Справочник должностей")
@allure.title("Обновление должности на null")
@allure.severity(allure.severity_level.CRITICAL)
def test_position_null_update():
    with allure.step("Создать должность"):
        database.create_position("Тестировщик")
        items = database.get_all_positions()
        pos_id = items[0]["id"]
    with allure.step("Обновить название на null"):
        database.update_position(pos_id, "")
    with allure.step("Проверить изменение"):
        pos = database.get_position_by_id(pos_id)
        assert pos["name"] == ""

@allure.feature("База данных")
@allure.story("Справочник должностей")
@allure.title("Удаление должности")
@allure.severity(allure.severity_level.CRITICAL)
def test_position_delete():
    with allure.step("Создать должность"):
        database.create_position("Стажёр")
        items = database.get_all_positions()
        pos_id = items[0]["id"]
    with allure.step("Удалить должность"):
        database.delete_position(pos_id)
    with allure.step("Убедиться что не существует"):
        assert database.get_position_by_id(pos_id) is None


@allure.feature("База данных")
@allure.story("Справочник должностей")
@allure.title("Дублирующее название должности вызывает IntegrityError")
@allure.severity(allure.severity_level.CRITICAL)
def test_position_duplicate_raises():
    with allure.step("Создать должность"):
        database.create_position("Архитектор")
    with allure.step("Попытаться создать дубль"):
        with pytest.raises(Exception):
            database.create_position("Архитектор")


@allure.feature("База данных")
@allure.story("Справочник должностей")
@allure.title("Миграция должностей из существующих сотрудников")
@allure.severity(allure.severity_level.NORMAL)
def test_position_migration_from_employees(make_employee):
    with allure.step("Создать сотрудника с должностью"):
        make_employee("Иван Иванов", "DevOps-инженер", "ИТ")
    with allure.step("Переинициализировать БД (должна подтянуть должность)"):
        database.init_db()
    with allure.step("Должность должна быть в справочнике"):
        names = [r["name"] for r in database.get_all_positions()]
        assert "DevOps-инженер" in names


# --- Departments ---

@allure.feature("База данных")
@allure.story("Справочник отделов")
@allure.title("Создание отдела и получение всех")
@allure.severity(allure.severity_level.CRITICAL)
def test_department_create_and_get_all():
    with allure.step("Создать два отдела"):
        database.create_department("Разработка")
        database.create_department("Маркетинг")
    with allure.step("Получить все отделы"):
        items = database.get_all_departments()
    with allure.step("Проверить наличие обоих отделов"):
        names = [r["name"] for r in items]
        assert "Разработка" in names
        assert "Маркетинг" in names


@allure.feature("База данных")
@allure.story("Справочник отделов")
@allure.title("Обновление отдела")
@allure.severity(allure.severity_level.CRITICAL)
def test_department_update():
    with allure.step("Создать отдел"):
        database.create_department("Кадры")
        items = database.get_all_departments()
        dept_id = items[0]["id"]
    with allure.step("Обновить название"):
        database.update_department(dept_id, "HR")
    with allure.step("Проверить изменение"):
        dept = database.get_department_by_id(dept_id)
        assert dept["name"] == "HR"


@allure.feature("База данных")
@allure.story("Справочник отделов")
@allure.title("Удаление отдела")
@allure.severity(allure.severity_level.CRITICAL)
def test_department_delete():
    with allure.step("Создать отдел"):
        database.create_department("Временный")
        items = database.get_all_departments()
        dept_id = items[0]["id"]
    with allure.step("Удалить отдел"):
        database.delete_department(dept_id)
    with allure.step("Убедиться что не существует"):
        assert database.get_department_by_id(dept_id) is None


@allure.feature("База данных")
@allure.story("Справочник отделов")
@allure.title("Дублирующее название отдела вызывает IntegrityError")
@allure.severity(allure.severity_level.CRITICAL)
def test_department_duplicate_raises():
    with allure.step("Создать отдел"):
        database.create_department("Бухгалтерия")
    with allure.step("Попытаться создать дубль"):
        with pytest.raises(Exception):
            database.create_department("Бухгалтерия")


@allure.feature("База данных")
@allure.story("Справочник отделов")
@allure.title("get_departments читает из таблицы departments")
@allure.severity(allure.severity_level.NORMAL)
def test_get_departments_from_table():
    with allure.step("Создать отделы в таблице departments"):
        database.create_department("Финансы")
        database.create_department("Юридический")
        database.create_department("Дирекция")
    with allure.step("get_departments возвращает их"):
        depts = database.get_departments()
        assert "Финансы" in depts
        assert "Юридический" in depts
        assert "Дирекция" in depts
