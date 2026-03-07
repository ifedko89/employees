import os
import re

import grpc
from flask import Flask, render_template, request, redirect, url_for, flash

import employees_pb2
import employees_pb2_grpc

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[\d\s\-()]{7,20}$")


def validate_reference_name(name: str):
    if not name:
        return "Название не может быть пустым."
    if not (2 <= len(name) <= 50):
        return "Название должно содержать от 2 до 50 символов."
    return None


def validate_form(full_name, position_id, department_id, email, phone):
    errors = {}
    if not full_name:
        errors["full_name"] = "Обязательное поле."
    elif not (3 <= len(full_name) <= 50):
        errors["full_name"] = "От 3 до 50 символов."
    if not position_id:
        errors["position"] = "Обязательное поле."
    if not department_id:
        errors["department"] = "Обязательное поле."
    if not email:
        errors["email"] = "Обязательное поле."
    elif not EMAIL_RE.match(email):
        errors["email"] = "Некорректный адрес электронной почты."
    if phone and not PHONE_RE.match(phone):
        errors["phone"] = "Некорректный номер телефона."
    return errors


app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"

GRPC_HOST = os.environ.get("GRPC_HOST", "localhost:50051")
channel = grpc.insecure_channel(GRPC_HOST)
stub = employees_pb2_grpc.EmployeesServiceStub(channel)


def _emp_to_dict(emp):
    return {
        "id": emp.id,
        "full_name": emp.full_name,
        "position": emp.position,
        "position_id": emp.position_id,
        "department": emp.department,
        "department_id": emp.department_id,
        "email": emp.email,
        "phone": emp.phone,
        "created_at": emp.created_at,
        "updated_at": emp.updated_at,
    }


def _history_to_dict(rec):
    return {
        "id": rec.id,
        "employee_id": rec.employee_id,
        "changed_at": rec.changed_at,
        "change_type": rec.change_type,
        "field_name": rec.field_name,
        "old_value": rec.old_value,
        "new_value": rec.new_value,
    }


def _dept_to_dict(dept):
    return {"id": dept.id, "name": dept.name}


def _pos_to_dict(pos):
    return {"id": pos.id, "name": pos.name}


@app.route("/")
def index():
    query = request.args.get("q", "").strip()
    sort = request.args.get("sort", "full_name")
    order = request.args.get("order", "asc")
    dept = request.args.get("dept", "")
    resp = stub.ListEmployees(employees_pb2.ListEmployeesRequest(
        search=query, sort=sort, order=order, dept=dept,
    ))
    employees = [_emp_to_dict(e) for e in resp.employees]
    dept_resp = stub.ListDepartments(employees_pb2.ListDepartmentsRequest())
    departments = [d.name for d in dept_resp.departments]
    return render_template(
        "index.html",
        employees=employees, query=query,
        sort=sort, order=order, dept=dept,
        departments=departments,
    )


@app.route("/create", methods=["GET", "POST"])
def create():
    pos_resp = stub.ListPositions(employees_pb2.ListPositionsRequest())
    positions = [_pos_to_dict(p) for p in pos_resp.positions]
    dept_resp = stub.ListDepartments(employees_pb2.ListDepartmentsRequest())
    departments = [_dept_to_dict(d) for d in dept_resp.departments]

    form_data = {}
    errors = {}

    if request.method == "POST":
        full_name = request.form["full_name"].strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        try:
            position_id = int(request.form["position"])
            department_id = int(request.form["department"])
        except (ValueError, KeyError):
            position_id = 0
            department_id = 0

        form_data = dict(full_name=full_name, position_id=position_id,
                         department_id=department_id, email=email, phone=phone)
        errors = validate_form(full_name, position_id, department_id, email, phone)

        if not errors:
            result = stub.CreateEmployee(employees_pb2.CreateEmployeeRequest(
                full_name=full_name, position_id=position_id, department_id=department_id,
                email=email, phone=phone,
            ))
            if result.success:
                flash(f"Сотрудник «{full_name}» добавлен.", "success")
                return redirect(url_for("index"))
            elif result.error == "duplicate_email":
                errors["email"] = "Сотрудник с таким email уже существует."

    return render_template("form.html", action="create", employee=None,
                           positions=positions, departments=departments,
                           form_data=form_data, errors=errors)


@app.route("/edit/<int:employee_id>", methods=["GET", "POST"])
def edit(employee_id):
    emp_resp = stub.GetEmployee(employees_pb2.GetEmployeeRequest(id=employee_id))
    if not emp_resp.found:
        flash("Сотрудник не найден.", "error")
        return redirect(url_for("index"))
    employee = _emp_to_dict(emp_resp.employee)

    pos_resp = stub.ListPositions(employees_pb2.ListPositionsRequest())
    positions = [_pos_to_dict(p) for p in pos_resp.positions]
    dept_resp = stub.ListDepartments(employees_pb2.ListDepartmentsRequest())
    departments = [_dept_to_dict(d) for d in dept_resp.departments]

    form_data = employee
    errors = {}

    if request.method == "POST":
        full_name = request.form["full_name"].strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        try:
            position_id = int(request.form["position"])
            department_id = int(request.form["department"])
        except (ValueError, KeyError):
            position_id = 0
            department_id = 0

        form_data = dict(full_name=full_name, position_id=position_id,
                         department_id=department_id, email=email, phone=phone)
        errors = validate_form(full_name, position_id, department_id, email, phone)

        if not errors:
            result = stub.UpdateEmployee(employees_pb2.UpdateEmployeeRequest(
                id=employee_id, full_name=full_name, position_id=position_id,
                department_id=department_id, email=email, phone=phone,
            ))
            if result.success:
                flash(f"Данные сотрудника «{full_name}» обновлены.", "success")
                return redirect(url_for("index"))
            elif result.error == "duplicate_email":
                errors["email"] = "Сотрудник с таким email уже существует."

    return render_template("form.html", action="edit", employee=employee,
                           positions=positions, departments=departments,
                           form_data=form_data, errors=errors)


@app.route("/history/<int:employee_id>")
def history(employee_id):
    emp_resp = stub.GetEmployee(employees_pb2.GetEmployeeRequest(id=employee_id))
    if not emp_resp.found:
        flash("Сотрудник не найден.", "error")
        return redirect(url_for("index"))
    employee = _emp_to_dict(emp_resp.employee)
    hist_resp = stub.GetHistory(employees_pb2.GetHistoryRequest(employee_id=employee_id))
    records = [_history_to_dict(r) for r in hist_resp.records]
    return render_template("history.html", employee=employee, records=records)


@app.route("/delete/<int:employee_id>", methods=["POST"])
def delete(employee_id):
    emp_resp = stub.GetEmployee(employees_pb2.GetEmployeeRequest(id=employee_id))
    if emp_resp.found:
        employee = _emp_to_dict(emp_resp.employee)
        stub.DeleteEmployee(employees_pb2.DeleteEmployeeRequest(id=employee_id))
        flash(f"Сотрудник «{employee['full_name']}» удалён.", "success")
    return redirect(url_for("index"))


@app.route("/positions")
def positions():
    pos_resp = stub.ListPositions(employees_pb2.ListPositionsRequest())
    items = [_pos_to_dict(p) for p in pos_resp.positions]
    edit_id = request.args.get("edit", type=int)
    edit_item = None
    if edit_id:
        edit_resp = stub.GetPosition(employees_pb2.GetPositionRequest(id=edit_id))
        edit_item = _pos_to_dict(edit_resp.position) if edit_resp.found else None
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
        result = stub.CreatePosition(employees_pb2.CreatePositionRequest(name=name))
        if result.success:
            flash(f"Должность «{name}» добавлена.", "success")
        elif result.error == "duplicate_name":
            flash(f"Должность «{name}» уже существует.", "error")
    return redirect(url_for("positions"))


@app.route("/positions/<int:id>/edit", methods=["POST"])
def position_edit(id):
    name = request.form.get("name", "").strip()
    error = validate_reference_name(name)
    if error:
        flash(error, "error")
    else:
        result = stub.UpdatePosition(employees_pb2.UpdatePositionRequest(id=id, name=name))
        if result.success:
            flash(f"Должность обновлена.", "success")
        elif result.error == "duplicate_name":
            flash(f"Должность «{name}» уже существует.", "error")
    return redirect(url_for("positions"))


@app.route("/positions/<int:id>/delete", methods=["POST"])
def position_delete(id):
    result = stub.DeletePosition(employees_pb2.DeletePositionRequest(id=id))
    if result.success:
        flash("Должность удалена.", "success")
    elif result.error == "in_use":
        flash("Невозможно удалить должность: она используется сотрудниками.", "error")
    return redirect(url_for("positions"))


@app.route("/departments")
def departments():
    dept_resp = stub.ListDepartments(employees_pb2.ListDepartmentsRequest())
    items = [_dept_to_dict(d) for d in dept_resp.departments]
    edit_id = request.args.get("edit", type=int)
    edit_item = None
    if edit_id:
        edit_resp = stub.GetDepartment(employees_pb2.GetDepartmentRequest(id=edit_id))
        edit_item = _dept_to_dict(edit_resp.department) if edit_resp.found else None
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
        result = stub.CreateDepartment(employees_pb2.CreateDepartmentRequest(name=name))
        if result.success:
            flash(f"Отдел «{name}» добавлен.", "success")
        elif result.error == "duplicate_name":
            flash(f"Отдел «{name}» уже существует.", "error")
    return redirect(url_for("departments"))


@app.route("/departments/<int:id>/edit", methods=["POST"])
def department_edit(id):
    name = request.form.get("name", "").strip()
    error = validate_reference_name(name)
    if error:
        flash(error, "error")
    else:
        result = stub.UpdateDepartment(employees_pb2.UpdateDepartmentRequest(id=id, name=name))
        if result.success:
            flash(f"Отдел обновлён.", "success")
        elif result.error == "duplicate_name":
            flash(f"Отдел «{name}» уже существует.", "error")
    return redirect(url_for("departments"))


@app.route("/departments/<int:id>/delete", methods=["POST"])
def department_delete(id):
    result = stub.DeleteDepartment(employees_pb2.DeleteDepartmentRequest(id=id))
    if result.success:
        flash("Отдел удалён.", "success")
    elif result.error == "in_use":
        flash("Невозможно удалить отдел: он используется сотрудниками.", "error")
    return redirect(url_for("departments"))


if __name__ == "__main__":
    app.run(debug=True)
