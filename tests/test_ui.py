"""UI тесты: end-to-end через реальный браузер (Playwright + Chromium)."""

import pytest
import allure

import database


# ── Главная страница ────────────────────────────────────────────────────────

@allure.feature("UI")
@allure.story("Главная страница")
@allure.title("Пустой список — отображается заглушка")
@allure.severity(allure.severity_level.NORMAL)
def test_ui_index_empty(pw_page):
    page, base = pw_page
    with allure.step("Открыть главную страницу"):
        page.goto(base + "/")
    with allure.step("Текст пустого состояния виден"):
        assert "Сотрудников пока нет" in page.content()


@allure.feature("UI")
@allure.story("Главная страница")
@allure.title("Созданный сотрудник виден в таблице")
@allure.severity(allure.severity_level.NORMAL)
def test_ui_index_shows_employee(pw_page, make_employee):
    page, base = pw_page
    with allure.step("Создать сотрудника через БД"):
        emp = make_employee("Анна Кузнецова", "Аналитик", "ИТ-отдел")
    with allure.step("Открыть главную"):
        page.goto(base + "/")
    with allure.step("Имя сотрудника присутствует в таблице"):
        assert emp["full_name"] in page.content()


# ── Создание сотрудника ─────────────────────────────────────────────────────

@allure.feature("UI")
@allure.story("Создание сотрудника")
@allure.title("Успешное создание через форму")
@allure.severity(allure.severity_level.CRITICAL)
def test_ui_create_employee(pw_page):
    page, base = pw_page
    with allure.step("Создать должность и отдел в справочниках"):
        pos_id = database.get_or_create_position("Разработчик")
        dept_id = database.get_or_create_department("ИТ-отдел")
    with allure.step("Открыть форму /create"):
        page.goto(base + "/create")
    with allure.step("Заполнить форму"):
        page.fill('[name="full_name"]', "Иван Иванов")
        page.select_option('[name="position"]', str(pos_id))
        page.select_option('[name="department"]', str(dept_id))
        page.fill('[name="email"]', "ivanov@example.com")
    with allure.step("Отправить форму"):
        page.click('button[type="submit"]')
    with allure.step("Редирект на главную, flash-сообщение и сотрудник в таблице"):
        page.wait_for_url(base + "/")
        content = page.content()
        assert "Иван Иванов" in content
        assert "добавлен" in content


@allure.feature("UI")
@allure.story("Создание сотрудника")
@allure.title("Пустое ФИО → сообщение об ошибке")
@allure.severity(allure.severity_level.CRITICAL)
def test_ui_create_empty_name(pw_page):
    page, base = pw_page
    with allure.step("Создать должность и отдел"):
        pos_id = database.get_or_create_position("Менеджер")
        dept_id = database.get_or_create_department("Кадры")
    with allure.step("Открыть /create и отправить без ФИО"):
        page.goto(base + "/create")
        page.select_option('[name="position"]', str(pos_id))
        page.select_option('[name="department"]', str(dept_id))
        page.fill('[name="email"]', "test@test.com")
        page.click('button[type="submit"]')
    with allure.step("Форма перерисована с сообщением об ошибке"):
        assert "Обязательное" in page.content()


@allure.feature("UI")
@allure.story("Создание сотрудника")
@allure.title("Некорректный email → сообщение об ошибке")
@allure.severity(allure.severity_level.CRITICAL)
def test_ui_create_invalid_email(pw_page):
    page, base = pw_page
    with allure.step("Создать должность и отдел"):
        pos_id = database.get_or_create_position("Менеджер")
        dept_id = database.get_or_create_department("Кадры")
    with allure.step("Отправить форму с некорректным email"):
        page.goto(base + "/create")
        page.fill('[name="full_name"]', "Тест Тестов")
        page.select_option('[name="position"]', str(pos_id))
        page.select_option('[name="department"]', str(dept_id))
        page.fill('[name="email"]', "not-an-email")
        page.click('button[type="submit"]')
    with allure.step("Ошибка про email в HTML"):
        assert "почт" in page.content()


# ── Редактирование ──────────────────────────────────────────────────────────

@allure.feature("UI")
@allure.story("Редактирование сотрудника")
@allure.title("Форма предзаполнена данными сотрудника")
@allure.severity(allure.severity_level.NORMAL)
def test_ui_edit_form_prefilled(pw_page, make_employee):
    page, base = pw_page
    with allure.step("Создать сотрудника"):
        emp = make_employee("Борис Смирнов", "Тестировщик", "QA")
    with allure.step(f"Открыть /edit/{emp['id']}"):
        page.goto(base + f"/edit/{emp['id']}")
    with allure.step("Поле full_name содержит имя сотрудника"):
        value = page.input_value('[name="full_name"]')
        assert value == "Борис Смирнов"


@allure.feature("UI")
@allure.story("Редактирование сотрудника")
@allure.title("Успешное обновление данных через форму")
@allure.severity(allure.severity_level.CRITICAL)
def test_ui_edit_employee(pw_page, make_employee):
    page, base = pw_page
    with allure.step("Создать сотрудника"):
        emp = make_employee()
    with allure.step("Создать новую должность"):
        new_pos_id = database.get_or_create_position("Архитектор")
    with allure.step("Открыть форму редактирования"):
        page.goto(base + f"/edit/{emp['id']}")
    with allure.step("Изменить имя и должность"):
        page.fill('[name="full_name"]', "")
        page.fill('[name="full_name"]', "Пётр Петров")
        page.select_option('[name="position"]', str(new_pos_id))
    with allure.step("Сохранить"):
        page.click('button[type="submit"]')
    with allure.step("Редирект на главную, имя обновлено"):
        page.wait_for_url(base + "/")
        assert "Пётр Петров" in page.content()
        assert "обновлены" in page.content()


# ── Удаление ────────────────────────────────────────────────────────────────

@allure.feature("UI")
@allure.story("Удаление сотрудника")
@allure.title("Удаление через кнопку с подтверждением")
@allure.severity(allure.severity_level.CRITICAL)
def test_ui_delete_employee(pw_page, make_employee):
    page, base = pw_page
    with allure.step("Создать сотрудника"):
        emp = make_employee("Сергей Орлов", "Менеджер", "Продажи")
    with allure.step("Открыть главную"):
        page.goto(base + "/")
    with allure.step("Принять диалог подтверждения и нажать Удалить"):
        page.on("dialog", lambda d: d.accept())
        page.click('button.btn-act.danger')
    with allure.step("Flash-сообщение об удалении, таблица пустая"):
        page.wait_for_url(base + "/")
        assert "удалён" in page.content()
        # Сотрудник удалён — таблица должна быть пустой
        assert "Сотрудников пока нет" in page.content()


# ── Поиск ───────────────────────────────────────────────────────────────────

@allure.feature("UI")
@allure.story("Поиск и фильтрация")
@allure.title("Поиск по имени — показывает только совпадающие записи")
@allure.severity(allure.severity_level.NORMAL)
def test_ui_search_by_name(pw_page, make_employee):
    page, base = pw_page
    with allure.step("Создать двух сотрудников"):
        make_employee("Иван Иванов", "Разработчик", "ИТ-отдел")
        make_employee("Пётр Петров", "Менеджер", "Кадры")
    with allure.step("Ввести поисковый запрос 'Иван' и нажать Найти"):
        page.goto(base + "/")
        page.fill('[name="q"]', "Иван")
        page.click('button[type="submit"]')
    with allure.step("'Иван Иванов' есть, 'Пётр Петров' — нет"):
        content = page.content()
        assert "Иван Иванов" in content
        assert "Пётр Петров" not in content


@allure.feature("UI")
@allure.story("Поиск и фильтрация")
@allure.title("Фильтр по отделу через select")
@allure.severity(allure.severity_level.NORMAL)
def test_ui_filter_by_department(pw_page, make_employee):
    page, base = pw_page
    with allure.step("Создать двух сотрудников из разных отделов"):
        make_employee("Иван Иванов", "Разработчик", "ИТ-отдел")
        make_employee("Пётр Петров", "Менеджер", "Кадры")
    with allure.step("Выбрать отдел 'ИТ-отдел' в фильтре"):
        page.goto(base + "/")
        page.select_option('[name="dept"]', "ИТ-отдел")
        page.wait_for_load_state("networkidle")
    with allure.step("Только 'Иван Иванов' виден"):
        content = page.content()
        assert "Иван Иванов" in content
        assert "Пётр Петров" not in content


# ── Справочник должностей ───────────────────────────────────────────────────

@allure.feature("UI")
@allure.story("Справочник должностей")
@allure.title("Добавление должности через форму")
@allure.severity(allure.severity_level.CRITICAL)
def test_ui_positions_create(pw_page):
    page, base = pw_page
    with allure.step("Открыть /positions"):
        page.goto(base + "/positions")
    with allure.step("Ввести название и нажать Добавить"):
        page.fill('[name="name"]', "DevOps-инженер")
        page.click('button[type="submit"]')
    with allure.step("Должность появилась в списке"):
        page.wait_for_url(base + "/positions")
        assert "DevOps-инженер" in page.content()


@allure.feature("UI")
@allure.story("Справочник должностей")
@allure.title("Редактирование должности через inline-форму")
@allure.severity(allure.severity_level.CRITICAL)
def test_ui_positions_edit(pw_page):
    page, base = pw_page
    with allure.step("Создать должность в БД"):
        database.create_position("Стажёр")
        pos = database.get_all_positions()[0]
    with allure.step("Нажать Изменить для должности"):
        page.goto(base + "/positions")
        page.click('a.btn-act[href*="edit"]')
    with allure.step("Изменить название и сохранить"):
        page.fill('[name="name"]', "")
        page.fill('[name="name"]', "Специалист")
        page.click('button[type="submit"]')
    with allure.step("Обновлённое название в списке"):
        assert "Специалист" in page.content()
        assert "Стажёр" not in page.content()


@allure.feature("UI")
@allure.story("Справочник должностей")
@allure.title("Удаление должности с подтверждением")
@allure.severity(allure.severity_level.CRITICAL)
def test_ui_positions_delete(pw_page):
    page, base = pw_page
    with allure.step("Создать должность в БД"):
        database.create_position("Временная")
    with allure.step("Нажать Удалить и подтвердить"):
        page.goto(base + "/positions")
        page.on("dialog", lambda d: d.accept())
        page.click('button.btn-act.danger')
    with allure.step("Должность исчезла из списка"):
        assert "Временная" not in page.content()


# ── Справочник отделов ──────────────────────────────────────────────────────

@allure.feature("UI")
@allure.story("Справочник отделов")
@allure.title("Добавление отдела через форму")
@allure.severity(allure.severity_level.CRITICAL)
def test_ui_departments_create(pw_page):
    page, base = pw_page
    with allure.step("Открыть /departments"):
        page.goto(base + "/departments")
    with allure.step("Ввести название и нажать Добавить"):
        page.fill('[name="name"]', "Маркетинг")
        page.click('button[type="submit"]')
    with allure.step("Отдел появился в списке"):
        page.wait_for_url(base + "/departments")
        assert "Маркетинг" in page.content()


@allure.feature("UI")
@allure.story("Справочник отделов")
@allure.title("Удаление отдела с подтверждением")
@allure.severity(allure.severity_level.CRITICAL)
def test_ui_departments_delete(pw_page):
    page, base = pw_page
    with allure.step("Создать отдел в БД"):
        database.create_department("Временный отдел")
    with allure.step("Нажать Удалить и подтвердить"):
        page.goto(base + "/departments")
        page.on("dialog", lambda d: d.accept())
        page.click('button.btn-act.danger')
    with allure.step("Отдел исчез из списка"):
        assert "Временный отдел" not in page.content()


# ── Навигация ───────────────────────────────────────────────────────────────

@allure.feature("UI")
@allure.story("Навигация")
@allure.title("Кнопка '+ Добавить' ведёт на форму создания")
@allure.severity(allure.severity_level.MINOR)
def test_ui_nav_add_button(pw_page):
    page, base = pw_page
    with allure.step("Открыть главную"):
        page.goto(base + "/")
    with allure.step("Нажать '+ Добавить' в навбаре"):
        page.click("text=+ Добавить")
    with allure.step("Открылась форма создания"):
        page.wait_for_url(base + "/create")
        assert "Новый сотрудник" in page.content()
