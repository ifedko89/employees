import re
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash
import database

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[\d\s\-()]{7,20}$")


def validate_reference_name(name: str):
    if not name:
        return "Название не может быть пустым."
    if not (2 <= len(name) <= 50):
        return "Название должно содержать от 2 до 50 символов."
    return None


def validate_form(full_name, position, department, email, phone):
    if not full_name or not position or not department or not email:
        return "ФИО, должность, отдел и email — обязательные поля."
    for field, label in ((full_name, "ФИО"), (position, "Должность"), (department, "Отдел")):
        if not (3 <= len(field) <= 50):
            return f"{label} должно содержать от 3 до 50 символов."
    if not EMAIL_RE.match(email):
        return "Некорректный адрес электронной почты."
    if phone and not PHONE_RE.match(phone):
        return "Некорректный номер телефона."
    return None

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"

database.init_db()


@app.route("/")
def index():
    query = request.args.get("q", "").strip()
    sort = request.args.get("sort", "full_name")
    order = request.args.get("order", "asc")
    dept = request.args.get("dept", "")
    employees = database.get_all(search=query, sort=sort, order=order, dept=dept)
    departments = database.get_departments()
    return render_template(
        "index.html",
        employees=employees, query=query,
        sort=sort, order=order, dept=dept,
        departments=departments,
    )


@app.route("/create", methods=["GET", "POST"])
def create():
    positions = database.get_all_positions()
    departments = database.get_all_departments()

    if request.method == "POST":
        full_name = request.form["full_name"].strip()
        position = request.form["position"].strip()
        department = request.form["department"].strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()

        error = validate_form(full_name, position, department, email, phone)
        if error:
            flash(error, "error")
        else:
            try:
                database.create(full_name, position, department, email, phone)
                flash(f"Сотрудник «{full_name}» добавлен.", "success")
                return redirect(url_for("index"))
            except sqlite3.IntegrityError:
                flash("Сотрудник с таким email уже существует.", "error")

    return render_template("form.html", action="create", employee=None,
                           positions=positions, departments=departments)


@app.route("/edit/<int:employee_id>", methods=["GET", "POST"])
def edit(employee_id):
    employee = database.get_by_id(employee_id)
    if employee is None:
        flash("Сотрудник не найден.", "error")
        return redirect(url_for("index"))

    positions = database.get_all_positions()
    departments = database.get_all_departments()

    if request.method == "POST":
        full_name = request.form["full_name"].strip()
        position = request.form["position"].strip()
        department = request.form["department"].strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()

        error = validate_form(full_name, position, department, email, phone)
        if error:
            flash(error, "error")
        else:
            try:
                database.update(employee_id, full_name, position, department, email, phone)
                flash(f"Данные сотрудника «{full_name}» обновлены.", "success")
                return redirect(url_for("index"))
            except sqlite3.IntegrityError:
                flash("Сотрудник с таким email уже существует.", "error")

    return render_template("form.html", action="edit", employee=employee,
                           positions=positions, departments=departments)


@app.route("/history/<int:employee_id>")
def history(employee_id):
    employee = database.get_by_id(employee_id)
    if employee is None:
        flash("Сотрудник не найден.", "error")
        return redirect(url_for("index"))
    records = database.get_history(employee_id)
    return render_template("history.html", employee=employee, records=records)


@app.route("/delete/<int:employee_id>", methods=["POST"])
def delete(employee_id):
    employee = database.get_by_id(employee_id)
    if employee:
        database.delete(employee_id)
        flash(f"Сотрудник «{employee['full_name']}» удалён.", "success")
    return redirect(url_for("index"))


@app.route("/positions")
def positions():
    items = database.get_all_positions()
    edit_id = request.args.get("edit", type=int)
    edit_item = database.get_position_by_id(edit_id) if edit_id else None
    return render_template(
        "reference.html",
        title="Должности",
        items=items,
        edit_item=edit_item,
        create_url=url_for("position_create"),
        edit_base_url="/positions",
        delete_base_url="/positions",
    )


@app.route("/positions/create", methods=["POST"])
def position_create():
    name = request.form.get("name", "").strip()
    error = validate_reference_name(name)
    if error:
        flash(error, "error")
    else:
        try:
            database.create_position(name)
            flash(f"Должность «{name}» добавлена.", "success")
        except sqlite3.IntegrityError:
            flash(f"Должность «{name}» уже существует.", "error")
    return redirect(url_for("positions"))


@app.route("/positions/<int:id>/edit", methods=["POST"])
def position_edit(id):
    name = request.form.get("name", "").strip()
    error = validate_reference_name(name)
    if error:
        flash(error, "error")
    else:
        try:
            database.update_position(id, name)
            flash(f"Должность обновлена.", "success")
        except sqlite3.IntegrityError:
            flash(f"Должность «{name}» уже существует.", "error")
    return redirect(url_for("positions"))


@app.route("/positions/<int:id>/delete", methods=["POST"])
def position_delete(id):
    database.delete_position(id)
    flash("Должность удалена.", "success")
    return redirect(url_for("positions"))


@app.route("/departments")
def departments():
    items = database.get_all_departments()
    edit_id = request.args.get("edit", type=int)
    edit_item = database.get_department_by_id(edit_id) if edit_id else None
    return render_template(
        "reference.html",
        title="Отделы",
        items=items,
        edit_item=edit_item,
        create_url=url_for("department_create"),
        edit_base_url="/departments",
        delete_base_url="/departments",
    )


@app.route("/departments/create", methods=["POST"])
def department_create():
    name = request.form.get("name", "").strip()
    error = validate_reference_name(name)
    if error:
        flash(error, "error")
    else:
        try:
            database.create_department(name)
            flash(f"Отдел «{name}» добавлен.", "success")
        except sqlite3.IntegrityError:
            flash(f"Отдел «{name}» уже существует.", "error")
    return redirect(url_for("departments"))


@app.route("/departments/<int:id>/edit", methods=["POST"])
def department_edit(id):
    name = request.form.get("name", "").strip()
    error = validate_reference_name(name)
    if error:
        flash(error, "error")
    else:
        try:
            database.update_department(id, name)
            flash(f"Отдел обновлён.", "success")
        except sqlite3.IntegrityError:
            flash(f"Отдел «{name}» уже существует.", "error")
    return redirect(url_for("departments"))


@app.route("/departments/<int:id>/delete", methods=["POST"])
def department_delete(id):
    database.delete_department(id)
    flash("Отдел удалён.", "success")
    return redirect(url_for("departments"))


if __name__ == "__main__":
    app.run(debug=True)
