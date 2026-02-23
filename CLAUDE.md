# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Установка зависимостей
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Запуск приложения
python app.py
# Приложение запустится на http://127.0.0.1:5000 в режиме debug
```

Тестов нет. CI/CD нет.

## Architecture

Минималистичное Flask CRUD-приложение для управления справочником сотрудников. Весь интерфейс на русском языке.

**Стек:** Python 3.13, Flask 3.x, SQLite (stdlib `sqlite3`), Jinja2, Bootstrap 5.3.3 (CDN).

**Два основных модуля:**
- `app.py` — Flask-приложение, все маршруты (list/create/edit/delete)
- `database.py` — слой доступа к данным, прямые SQL-запросы без ORM

**База данных:** файл `employees.db` рядом с исходниками, создаётся автоматически при первом запуске через `database.init_db()`. Схема: таблица `employees` с полями `id`, `full_name`, `position`, `department` (обязательные) и `email`, `phone` (опциональные).

**Маршруты:**
| Метод | URL | Назначение |
|-------|-----|------------|
| GET | `/` | Список сотрудников, поддерживает `?q=` для поиска |
| GET/POST | `/create` | Создание сотрудника |
| GET/POST | `/edit/<id>` | Редактирование сотрудника |
| POST | `/delete/<id>` | Удаление сотрудника |

**Шаблоны** (`templates/`): `base.html` — базовый layout с navbar и flash-сообщениями; `index.html` — таблица сотрудников с поиском; `form.html` — единая форма для создания и редактирования.