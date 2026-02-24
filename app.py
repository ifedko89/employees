import re
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash
import database

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[\d\s\-()]{7,20}$")


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

    return render_template("form.html", action="create", employee=None)


@app.route("/edit/<int:employee_id>", methods=["GET", "POST"])
def edit(employee_id):
    employee = database.get_by_id(employee_id)
    if employee is None:
        flash("Сотрудник не найден.", "error")
        return redirect(url_for("index"))

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

    return render_template("form.html", action="edit", employee=employee)


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


if __name__ == "__main__":
    app.run(debug=True)
