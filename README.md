# Employees — справочник сотрудников

Flask-приложение для управления сотрудниками с gRPC-бэкендом и PostgreSQL.

[![Tests](https://github.com/ifedko89/employees/actions/workflows/tests.yml/badge.svg)](https://github.com/ifedko89/employees/actions/workflows/tests.yml)
[![Allure Report](https://img.shields.io/badge/Allure-Report-brightgreen)](https://ifedko89.github.io/employees/)
[![Coverage Heatmap](https://img.shields.io/badge/Coverage-Heatmap-orange)](https://ifedko89.github.io/employees/coverage/)

---

## Содержание

- [Обзор](#обзор)
- [Архитектура](#архитектура)
- [Быстрый старт](#быстрый-старт)
  - [Docker Compose](#docker-compose)
  - [Локальный запуск](#локальный-запуск)
- [Схема базы данных](#схема-базы-данных)
- [HTTP API (маршруты Flask)](#http-api-маршруты-flask)
- [gRPC API](#grpc-api)
- [Шаблоны и UI](#шаблоны-и-ui)
- [Тестирование](#тестирование)
- [CI/CD](#cicd)
- [Переменные окружения](#переменные-окружения)
- [Регенерация protobuf](#регенерация-protobuf)
- [Известные особенности](#известные-особенности)

---

## Обзор

Веб-приложение для ведения справочника сотрудников организации. Позволяет:

- управлять сотрудниками (создание, редактирование, удаление, поиск);
- вести нормализованные справочники должностей и отделов;
- просматривать историю изменений каждого сотрудника;
- искать и фильтровать список по имени и отделу, сортировать по любому столбцу.

**Технологический стек:**

| Компонент | Технология |
|-----------|-----------|
| Web-фронт | Flask 3.x, Jinja2, Bootstrap 5.3.3 |
| Транспорт | gRPC (grpcio ≥ 1.60) |
| База данных | PostgreSQL 16 (psycopg2, без ORM) |
| Контейнеризация | Docker, Docker Compose |
| Тесты | pytest, Playwright, Allure |
| CI/CD | GitHub Actions → GitHub Pages |

---

## Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                        Browser                          │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP :8000
┌───────────────────────▼─────────────────────────────────┐
│              Flask-приложение (app.py)                  │
│  - маршруты /  /create  /edit  /delete  /history        │
│  - маршруты /positions  /departments                    │
│  - валидация входных данных                             │
│  - конвертеры protobuf → dict для шаблонов              │
└───────────────────────┬─────────────────────────────────┘
                        │ gRPC :50051
┌───────────────────────▼─────────────────────────────────┐
│              gRPC-сервер (grpc_server.py)               │
│  - EmployeesServicer (16 RPC-методов)                   │
│  - ThreadPoolExecutor (10 воркеров)                     │
│  - конвертеры row → protobuf                            │
└───────────────────────┬─────────────────────────────────┘
                        │ psycopg2
┌───────────────────────▼─────────────────────────────────┐
│              Слой данных (database.py)                  │
│  - прямые SQL-запросы                                   │
│  - auto-commit / rollback через контекстный менеджер    │
│  - init_db() + миграции при старте                      │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│                   PostgreSQL 16                         │
│  employees · positions · departments · employee_history │
└─────────────────────────────────────────────────────────┘
```

**Ключевые файлы:**

```
employees/
├── app.py                    # Flask-приложение, HTTP → gRPC-stub
├── database.py               # Слой данных (SQL без ORM)
├── grpc_server.py            # gRPC-сервер, реализует EmployeesServicer
├── employees.proto           # Описание сервиса (источник истины)
├── employees_pb2.py          # Сгенерированные protobuf-сообщения
├── employees_pb2_grpc.py     # Сгенерированный stub + servicer
├── Dockerfile                # Единый образ для grpc и web
├── docker-compose.yml        # postgres + grpc + web
├── requirements.txt          # Зависимости приложения
├── requirements-dev.txt      # Зависимости для тестирования
├── pytest.ini                # Конфигурация pytest
├── templates/                # Jinja2-шаблоны
│   ├── base.html             # Layout: navbar, flash, Bootstrap
│   ├── index.html            # Список сотрудников с поиском и фильтрацией
│   ├── form.html             # Форма создания / редактирования
│   ├── history.html          # История изменений
│   └── reference.html        # Универсальный шаблон справочников
├── tests/
│   ├── conftest.py           # Фикстуры: БД, gRPC, Flask, Playwright
│   ├── test_database.py      # Тесты слоя данных (mark: db)
│   ├── test_routes.py        # Тесты HTTP-маршрутов (mark: routes)
│   ├── test_ui.py            # E2E Playwright-тесты (mark: ui)
│   └── reference_helper.py   # Хелпер для страниц справочников
├── scripts/
│   └── gen_coverage_heatmap.py  # Интерактивная Plotly-карта покрытия
└── .github/workflows/
    └── tests.yml             # CI: test → ui-test → deploy
```

---

## Быстрый старт

### Docker Compose

Самый простой способ запустить всё приложение:

```bash
docker compose up --build
```

Приложение будет доступно по адресу `http://localhost:8000`.

Остановить и удалить контейнеры:

```bash
docker compose down
```

Удалить вместе с данными:

```bash
docker compose down -v
```

### Локальный запуск

**Требования:** Python 3.13, PostgreSQL 16.

```bash
# 1. Создать виртуальное окружение и установить зависимости
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Настроить переменные окружения (или использовать значения по умолчанию)
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/employees
export GRPC_HOST=localhost:50051

# 3. Запустить gRPC-сервер (в отдельном терминале)
python grpc_server.py

# 4. Запустить Flask-приложение
python app.py
```

Flask запустится на `http://127.0.0.1:5000` в режиме debug.

---

## Схема базы данных

```sql
-- Справочники
CREATE TABLE positions (
    id   SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE departments (
    id   SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

-- Основная таблица сотрудников
CREATE TABLE employees (
    id            SERIAL PRIMARY KEY,
    full_name     TEXT NOT NULL,
    position_id   INTEGER REFERENCES positions(id),
    department_id INTEGER REFERENCES departments(id),
    email         TEXT UNIQUE,
    phone         TEXT,
    created_at    TIMESTAMP DEFAULT NOW(),
    updated_at    TIMESTAMP DEFAULT NOW()
);

-- Журнал изменений
CREATE TABLE employee_history (
    id          SERIAL PRIMARY KEY,
    employee_id INTEGER REFERENCES employees(id) ON DELETE CASCADE,
    changed_at  TIMESTAMP DEFAULT NOW(),
    change_type TEXT NOT NULL,   -- 'create' | 'update'
    field_name  TEXT,
    old_value   TEXT,            -- хранит имена (строки), не FK-идентификаторы
    new_value   TEXT
);
```

**Примечания:**
- `positions` и `departments` защищены FK-ограничениями: удалить запись справочника, используемую сотрудниками, невозможно (→ `IntegrityError` → сообщение об ошибке).
- `employee_history` хранит значения полей в виде строк (не FK) — для читаемости истории при переименовании справочных записей.
- `init_db()` включает автоматическую миграцию: если в таблице `employees` есть текстовые столбцы `position`/`department` (старая схема), они конвертируются в FK на справочники.
- Вспомогательные функции `get_or_create_position(name) → int` и `get_or_create_department(name) → int` атомарно создают запись справочника при её отсутствии.

---

## HTTP API (маршруты Flask)

### Сотрудники

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/` | Список сотрудников |
| GET/POST | `/create` | Создание сотрудника |
| GET/POST | `/edit/<id>` | Редактирование сотрудника |
| GET | `/history/<id>` | История изменений сотрудника |
| POST | `/delete/<id>` | Удаление сотрудника |

**Параметры запроса для GET `/`:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `q` | string | Полнотекстовый поиск по ФИО, должности, отделу, email, телефону |
| `sort` | string | Поле сортировки: `full_name`, `position`, `department` |
| `order` | string | Направление: `asc` (по умолчанию) / `desc` |
| `dept` | string | Фильтр по названию отдела |

**Поля формы сотрудника:**

| Поле | Обязательное | Валидация |
|------|:---:|----------|
| `full_name` | да | непустое |
| `position_id` | да | выбор из справочника |
| `department_id` | да | выбор из справочника |
| `email` | нет | формат `user@domain.tld` |
| `phone` | нет | только цифры, пробелы, `+`, `-`, `(`, `)` |

### Справочники

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/positions` | Список должностей (`?edit=<id>` — предзаполнить форму редактирования) |
| POST | `/positions/create` | Создать должность |
| POST | `/positions/<id>/edit` | Переименовать должность |
| POST | `/positions/<id>/delete` | Удалить должность (ошибка, если используется) |
| GET | `/departments` | Список отделов |
| POST | `/departments/create` | Создать отдел |
| POST | `/departments/<id>/edit` | Переименовать отдел |
| POST | `/departments/<id>/delete` | Удалить отдел (ошибка, если используется) |

Все операции возвращают flash-сообщение (успех / ошибка) и выполняют redirect.

---

## gRPC API

Описание сервиса: [`employees.proto`](employees.proto)

### Сообщения

```protobuf
message Employee {
    int32  id            = 1;
    string full_name     = 2;
    string position      = 3;   // название (денормализовано для удобства клиента)
    string department    = 4;
    string email         = 5;
    string phone         = 6;
    string created_at    = 7;
    string updated_at    = 8;
    int32  position_id   = 9;
    int32  department_id = 10;
}

message HistoryRecord {
    int32  id          = 1;
    int32  employee_id = 2;
    string changed_at  = 3;
    string change_type = 4;   // "create" | "update"
    string field_name  = 5;
    string old_value   = 6;
    string new_value   = 7;
}

message OperationResponse {
    bool   success = 1;
    string error   = 2;   // "duplicate_email" | "duplicate_name" | "in_use"
}
```

### Методы

**Сотрудники:**

| Метод | Запрос | Ответ |
|-------|--------|-------|
| `ListEmployees` | `ListEmployeesRequest` (q, sort, order, dept) | `ListEmployeesResponse` |
| `GetEmployee` | `GetEmployeeRequest` (id) | `GetEmployeeResponse` |
| `CreateEmployee` | `CreateEmployeeRequest` (full_name, position_id, department_id, email, phone) | `OperationResponse` |
| `UpdateEmployee` | `UpdateEmployeeRequest` (id, full_name, position_id, department_id, email, phone) | `OperationResponse` |
| `DeleteEmployee` | `DeleteEmployeeRequest` (id) | `OperationResponse` |
| `GetHistory` | `GetHistoryRequest` (id) | `GetHistoryResponse` |

**Отделы и должности** — симметричный CRUD (`List`, `Get`, `Create`, `Update`, `Delete`) для каждого справочника, итого 10 методов.

---

## Шаблоны и UI

Все шаблоны наследуют `base.html`, который подключает Bootstrap 5.3.3 с CDN и определяет общий layout.

**`index.html`** — таблица сотрудников:
- Сортировка кликом по заголовкам столбцов (ФИО, Должность, Отдел), с индикатором направления.
- Фильтр по отделу через `<select>` с автоматической отправкой формы.
- Поиск через текстовое поле.
- Кнопки действий: Изменить, История, Удалить (с `confirm`-диалогом).
- Временны́е метки `<time datetime="...">` форматируются в локальное время через JavaScript.

**`form.html`** — единая форма создания и редактирования:
- Должность и отдел — выпадающие списки, наполненные из справочников.
- В режиме редактирования отображает `created_at` / `updated_at`.

**`history.html`** — журнал изменений:
- Тип события отображается как Bootstrap-badge: «Создание» (зелёный) / «Изменение» (синий).
- Для изменений показывает: поле, старое значение → новое значение.

**`reference.html`** — универсальный шаблон справочников:
- Левая колонка: форма добавления (или редактирования, если `?edit=<id>`).
- Правая колонка: таблица с кнопками «Изменить» и «Удалить».

---

## Тестирование

### Установка зависимостей

```bash
pip install -r requirements.txt -r requirements-dev.txt
playwright install chromium --with-deps
```

### Запуск тестов

```bash
# Все тесты (без UI)
pytest --ignore=tests/test_ui.py

# Только тесты слоя данных
pytest -m db

# Только тесты HTTP-маршрутов
pytest -m routes

# Только UI-тесты (Playwright)
pytest tests/test_ui.py

# С отчётом Allure
pytest --alluredir=allure-results
allure serve allure-results

# С отчётом о покрытии
pytest --cov=. --cov-report=html
```

### Структура тестов

**`tests/conftest.py`** — общие фикстуры:

| Фикстура | Область | Описание |
|----------|---------|----------|
| `setup_db` | session, autouse | Поднимает временный PostgreSQL (`pytest-postgresql`), подменяет `DATABASE_URL`, запускает `init_db()`, поднимает gRPC-сервер на случайном порту, подменяет stub в `app.py` |
| `client` | function | Flask test client (`app.test_client()`) |
| `live_server` | function | Flask в фоновом потоке на случайном порту (для Playwright) |
| `pw_page` | function | Playwright Chromium; при падении теста прикрепляет скриншот и trace в Allure |
| `make_employee` | function | Фабрика сотрудников через `database.create()` с Faker `ru_RU` |

**`tests/test_database.py`** (~29 тестов, `@pytest.mark.db`):
- CRUD сотрудников, включая обновление с историей.
- Поиск: параметрический по 3 вариантам строки; фильтрация по отделу; сортировка по 2 полям; невалидный параметр `sort`.
- CRUD для `positions` и `departments`; защита от дубликатов (`IntegrityError`).
- Хелперы `get_or_create_position` / `get_or_create_department`.

**`tests/test_routes.py`** (~35 тестов, `@pytest.mark.routes`):
- Главная страница: отрендерен список, поиск возвращает совпадение / пустой результат.
- Создание сотрудника: успех → redirect; невалидные данные → форма с ошибкой; дублирующийся email → ошибка.
- Редактирование: предзаполнение, успешное обновление, невалидные данные.
- Удаление, история.
- Справочники: создание, дубликат, пустое имя, редактирование с предзаполнением, удаление.

**`tests/test_ui.py`** (~20 тестов, `@pytest.mark.ui`):
- Отображение: пустой список, сотрудник в таблице после создания.
- Формы: создание (smoke), валидация (пустое ФИО, некорректный email).
- Редактирование (smoke), удаление с диалогом подтверждения (smoke).
- Поиск по имени; фильтр по отделу через `<select>`.
- Справочники: создание, редактирование, удаление должностей и отделов; попытка удалить используемую должность → сообщение об ошибке.
- История: страница открывается; запись «Создание» присутствует; запись «Изменение» после редактирования.

---

## CI/CD

Пайплайн состоит из трёх job-ов в `.github/workflows/tests.yml`:

```
push/PR → [test] ──→ [ui-test] ──→ [deploy]  (if: always())
```

### Job `test`

1. Устанавливает Python 3.13 и зависимости.
2. Записывает `allure-results/environment.properties` (версии Python, Flask, тип БД).
3. Запускает все тесты кроме UI (`pytest --ignore=tests/test_ui.py`) с `pytest-postgresql` (встроенный PostgreSQL-сервер, `pg_ctl` из `/usr/lib/postgresql`).
4. Генерирует интерактивную карту покрытия (`scripts/gen_coverage_heatmap.py`).
5. Публикует результаты junit через `EnricoMi/publish-unit-test-result-action`.
6. Сохраняет артефакты: `allure-results`, `coverage.xml`, `coverage_heatmap/`.

### Job `ui-test` (needs: test)

1. Устанавливает Playwright и браузер Chromium.
2. Запускает `pytest tests/test_ui.py` с `-n auto` (параллельно), `--reruns 2` (повтор нестабильных тестов).
3. Сохраняет артефакт `allure-results-ui`.

### Job `deploy` (needs: test, ui-test; if: always())

1. Скачивает все артефакты (оба набора allure-results объединяются в одну папку).
2. Checkout ветки `gh-pages` в `./gh-pages`.
3. `simple-elf/allure-report-action` генерирует полный отчёт с историей последних 20 запусков.
4. `sudo rm -rf allure-history/.git` — удаляет `.git`, созданный Docker-action от имени root (без этого шага пуш в `gh-pages` падает).
5. Публикует отчёт Allure и карту покрытия в ветку `gh-pages` (`keep_files: true`).
6. При PR — добавляет комментарий со ссылками на отчёт и покрытие + процент покрытия из `coverage.xml`.

**Опубликованные результаты:**
- Allure Report: `https://ifedko89.github.io/employees/<run_number>/`
- Coverage Heatmap: `https://ifedko89.github.io/employees/coverage/`

---

## Переменные окружения

| Переменная | Значение по умолчанию | Где используется |
|------------|----------------------|-----------------|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/employees` | `database.py`, `grpc_server.py` |
| `GRPC_HOST` | `localhost:50051` | `app.py` |

В Docker Compose:

| Сервис | Переменная | Значение |
|--------|-----------|---------|
| `postgres` | `POSTGRES_DB/USER/PASSWORD` | `employees` |
| `grpc` | `DATABASE_URL` | `postgresql://employees:employees@postgres:5432/employees` |
| `web` | `GRPC_HOST` | `grpc:50051` |

---

## Регенерация protobuf

После изменения `employees.proto` нужно заново сгенерировать Python-файлы:

```bash
pip install grpcio-tools
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. employees.proto
```

Сгенерированные файлы `employees_pb2.py` и `employees_pb2_grpc.py` закоммичены в репозиторий — отдельная установка `grpcio-tools` для запуска приложения не требуется.

---

## Известные особенности

**Дублирующаяся функция в тестах.** В `tests/test_ui.py` функция `test_ui_positions_delete` объявлена дважды. Python молча перезаписывает первое определение вторым — фактически выполняется только последний вариант, первый теряется.

**Версия grpcio.** `requirements.txt` указывает `grpcio>=1.60.0`, но `employees_pb2_grpc.py` сгенерирован под версию 1.78.0 и выполняет проверку при импорте. На практике pip устанавливает последнюю доступную версию — проблем нет, однако нижняя граница в `requirements.txt` устарела.

**Карта покрытия.** `scripts/gen_coverage_heatmap.py` читает `coverage.json`, который генерируется только при запуске pytest с флагом `--cov-report=json`. При локальном запуске без этого флага скрипт завершится с ошибкой.
