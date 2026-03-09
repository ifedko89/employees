"""Хелпер для страниц-справочников /positions и /departments.

Оба маршрута используют один шаблон reference.html,
поэтому взаимодействие с ними одинаково.
"""


class ReferenceHelper:
    def __init__(self, page, base: str, path: str):
        """
        page — объект Playwright Page
        base — базовый URL живого сервера, например http://127.0.0.1:54321
        path — путь к справочнику: "/positions" или "/departments"
        """
        self._page = page
        self._base = base
        self._path = path

    def open(self):
        self._page.goto(self._base + self._path)

    def add(self, name: str):
        self._page.fill('[name="name"]', name)
        self._page.click('button[type="submit"]')
        self._page.wait_for_url(self._base + self._path)

    def edit_first(self, new_name: str):
        self._page.click('a.btn-act[href*="edit"]')
        self._page.fill('[name="name"]', new_name)
        self._page.click('button[type="submit"]')

    def delete_first(self):
        self._page.on("dialog", lambda d: d.accept())
        self._page.click('button.btn-act.danger')

    def items(self) -> list:
        """Возвращает список названий всех записей в таблице."""
        return self._page.locator("tbody td:first-child").all_inner_texts()
