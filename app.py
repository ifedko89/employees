import os
import re
import time

import grpc
from flask import Flask, request, jsonify, send_from_directory, Response
from prometheus_client import (
    Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST,
)

import employees_pb2
import employees_pb2_grpc

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[\d\s\-()]{7,20}$")

# ── Prometheus metrics ───────────────────────────────────────────────────────

REQUEST_COUNT = Counter(
    "flask_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "flask_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
)
REQUESTS_IN_PROGRESS = Gauge(
    "flask_http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method", "endpoint"],
)


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


STATIC_DIR = os.path.join(os.path.dirname(__file__), "static", "dist")

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")
app.secret_key = "dev-secret-key-change-in-production"

GRPC_HOST = os.environ.get("GRPC_HOST", "localhost:50051")
channel = grpc.insecure_channel(GRPC_HOST)
stub = employees_pb2_grpc.EmployeesServiceStub(channel)


@app.before_request
def _start_timer():
    request._prom_start = time.perf_counter()
    endpoint = request.endpoint or "unknown"
    REQUESTS_IN_PROGRESS.labels(method=request.method, endpoint=endpoint).inc()


@app.after_request
def _record_metrics(response):
    endpoint = request.endpoint or "unknown"
    if endpoint == "metrics":
        return response
    elapsed = time.perf_counter() - getattr(request, "_prom_start", time.perf_counter())
    REQUEST_LATENCY.labels(method=request.method, endpoint=endpoint).observe(elapsed)
    REQUEST_COUNT.labels(
        method=request.method, endpoint=endpoint, status=response.status_code,
    ).inc()
    REQUESTS_IN_PROGRESS.labels(method=request.method, endpoint=endpoint).dec()
    return response


@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


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


# ── Employee API ─────────────────────────────────────────────────────────────


@app.route("/api/employees", methods=["GET"])
def api_list_employees():
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
    return jsonify(employees=employees, departments=departments)


@app.route("/api/employees", methods=["POST"])
def api_create_employee():
    data = request.get_json(silent=True) or {}
    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip()
    phone = data.get("phone", "").strip()
    try:
        position_id = int(data.get("position_id", 0))
        department_id = int(data.get("department_id", 0))
    except (ValueError, TypeError):
        position_id = 0
        department_id = 0

    errors = validate_form(full_name, position_id, department_id, email, phone)
    if errors:
        return jsonify(errors=errors), 400

    result = stub.CreateEmployee(employees_pb2.CreateEmployeeRequest(
        full_name=full_name, position_id=position_id,
        department_id=department_id, email=email, phone=phone,
    ))
    if result.success:
        return jsonify(success=True, message=f"Сотрудник «{full_name}» добавлен."), 201
    if result.error == "duplicate_email":
        return jsonify(errors={"email": "Сотрудник с таким email уже существует."}), 400
    return jsonify(error="Unexpected error"), 500


@app.route("/api/employees/<int:employee_id>", methods=["GET"])
def api_get_employee(employee_id):
    emp_resp = stub.GetEmployee(employees_pb2.GetEmployeeRequest(id=employee_id))
    if not emp_resp.found:
        return jsonify(error="Сотрудник не найден."), 404
    employee = _emp_to_dict(emp_resp.employee)
    pos_resp = stub.ListPositions(employees_pb2.ListPositionsRequest())
    positions = [_pos_to_dict(p) for p in pos_resp.positions]
    dept_resp = stub.ListDepartments(employees_pb2.ListDepartmentsRequest())
    departments = [_dept_to_dict(d) for d in dept_resp.departments]
    return jsonify(employee=employee, positions=positions, departments=departments)


@app.route("/api/employees/<int:employee_id>", methods=["PUT"])
def api_update_employee(employee_id):
    emp_resp = stub.GetEmployee(employees_pb2.GetEmployeeRequest(id=employee_id))
    if not emp_resp.found:
        return jsonify(error="Сотрудник не найден."), 404

    data = request.get_json(silent=True) or {}
    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip()
    phone = data.get("phone", "").strip()
    try:
        position_id = int(data.get("position_id", 0))
        department_id = int(data.get("department_id", 0))
    except (ValueError, TypeError):
        position_id = 0
        department_id = 0

    errors = validate_form(full_name, position_id, department_id, email, phone)
    if errors:
        return jsonify(errors=errors), 400

    result = stub.UpdateEmployee(employees_pb2.UpdateEmployeeRequest(
        id=employee_id, full_name=full_name, position_id=position_id,
        department_id=department_id, email=email, phone=phone,
    ))
    if result.success:
        return jsonify(success=True, message=f"Данные сотрудника «{full_name}» обновлены.")
    if result.error == "duplicate_email":
        return jsonify(errors={"email": "Сотрудник с таким email уже существует."}), 400
    return jsonify(error="Unexpected error"), 500


@app.route("/api/employees/<int:employee_id>", methods=["DELETE"])
def api_delete_employee(employee_id):
    emp_resp = stub.GetEmployee(employees_pb2.GetEmployeeRequest(id=employee_id))
    message = ""
    if emp_resp.found:
        employee = _emp_to_dict(emp_resp.employee)
        stub.DeleteEmployee(employees_pb2.DeleteEmployeeRequest(id=employee_id))
        message = f"Сотрудник «{employee['full_name']}» удалён."
    return jsonify(success=True, message=message)


@app.route("/api/employees/<int:employee_id>/history", methods=["GET"])
def api_employee_history(employee_id):
    emp_resp = stub.GetEmployee(employees_pb2.GetEmployeeRequest(id=employee_id))
    if not emp_resp.found:
        return jsonify(error="Сотрудник не найден."), 404
    employee = _emp_to_dict(emp_resp.employee)
    hist_resp = stub.GetHistory(employees_pb2.GetHistoryRequest(employee_id=employee_id))
    records = [_history_to_dict(r) for r in hist_resp.records]
    return jsonify(employee=employee, records=records)


# ── Positions API ────────────────────────────────────────────────────────────


@app.route("/api/positions", methods=["GET"])
def api_list_positions():
    pos_resp = stub.ListPositions(employees_pb2.ListPositionsRequest())
    positions = [_pos_to_dict(p) for p in pos_resp.positions]
    return jsonify(positions=positions)


@app.route("/api/positions", methods=["POST"])
def api_create_position():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    error = validate_reference_name(name)
    if error:
        return jsonify(error=error), 400
    result = stub.CreatePosition(employees_pb2.CreatePositionRequest(name=name))
    if result.success:
        return jsonify(success=True, message=f"Должность «{name}» добавлена."), 201
    if result.error == "duplicate_name":
        return jsonify(error=f"Должность «{name}» уже существует."), 400
    return jsonify(error="Unexpected error"), 500


@app.route("/api/positions/<int:id>", methods=["PUT"])
def api_update_position(id):
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    error = validate_reference_name(name)
    if error:
        return jsonify(error=error), 400
    result = stub.UpdatePosition(employees_pb2.UpdatePositionRequest(id=id, name=name))
    if result.success:
        return jsonify(success=True, message="Должность обновлена.")
    if result.error == "duplicate_name":
        return jsonify(error=f"Должность «{name}» уже существует."), 400
    return jsonify(error="Unexpected error"), 500


@app.route("/api/positions/<int:id>", methods=["DELETE"])
def api_delete_position(id):
    result = stub.DeletePosition(employees_pb2.DeletePositionRequest(id=id))
    if result.success:
        return jsonify(success=True, message="Должность удалена.")
    if result.error == "in_use":
        return jsonify(error="Невозможно удалить должность: она используется сотрудниками."), 400
    return jsonify(error="Unexpected error"), 500


# ── Departments API ──────────────────────────────────────────────────────────


@app.route("/api/departments", methods=["GET"])
def api_list_departments():
    dept_resp = stub.ListDepartments(employees_pb2.ListDepartmentsRequest())
    departments = [_dept_to_dict(d) for d in dept_resp.departments]
    return jsonify(departments=departments)


@app.route("/api/departments", methods=["POST"])
def api_create_department():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    error = validate_reference_name(name)
    if error:
        return jsonify(error=error), 400
    result = stub.CreateDepartment(employees_pb2.CreateDepartmentRequest(name=name))
    if result.success:
        return jsonify(success=True, message=f"Отдел «{name}» добавлен."), 201
    if result.error == "duplicate_name":
        return jsonify(error=f"Отдел «{name}» уже существует."), 400
    return jsonify(error="Unexpected error"), 500


@app.route("/api/departments/<int:id>", methods=["PUT"])
def api_update_department(id):
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    error = validate_reference_name(name)
    if error:
        return jsonify(error=error), 400
    result = stub.UpdateDepartment(employees_pb2.UpdateDepartmentRequest(id=id, name=name))
    if result.success:
        return jsonify(success=True, message="Отдел обновлён.")
    if result.error == "duplicate_name":
        return jsonify(error=f"Отдел «{name}» уже существует."), 400
    return jsonify(error="Unexpected error"), 500


@app.route("/api/departments/<int:id>", methods=["DELETE"])
def api_delete_department(id):
    result = stub.DeleteDepartment(employees_pb2.DeleteDepartmentRequest(id=id))
    if result.success:
        return jsonify(success=True, message="Отдел удалён.")
    if result.error == "in_use":
        return jsonify(error="Невозможно удалить отдел: он используется сотрудниками."), 400
    return jsonify(error="Unexpected error"), 500


# ── SPA serving ──────────────────────────────────────────────────────────────


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_spa(path):
    if path and os.path.exists(os.path.join(STATIC_DIR, path)):
        return send_from_directory(STATIC_DIR, path)
    return send_from_directory(STATIC_DIR, "index.html")


if __name__ == "__main__":
    app.run(debug=True)
