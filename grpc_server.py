import concurrent.futures
import time

import psycopg2
import grpc
from prometheus_client import Counter, Histogram, start_http_server

import database
import employees_pb2
import employees_pb2_grpc

# ── Prometheus metrics ───────────────────────────────────────────────────────

GRPC_REQUEST_COUNT = Counter(
    "grpc_server_requests_total",
    "Total gRPC requests",
    ["method", "status"],
)
GRPC_REQUEST_LATENCY = Histogram(
    "grpc_server_request_duration_seconds",
    "gRPC request latency in seconds",
    ["method"],
)


class MetricsInterceptor(grpc.ServerInterceptor):
    def intercept_service(self, continuation, handler_call_details):
        method = handler_call_details.method.split("/")[-1]
        start = time.perf_counter()

        handler = continuation(handler_call_details)
        if handler is None:
            GRPC_REQUEST_COUNT.labels(method=method, status="UNIMPLEMENTED").inc()
            return handler

        original_unary = handler.unary_unary

        def instrumented(request, context):
            try:
                response = original_unary(request, context)
                elapsed = time.perf_counter() - start
                GRPC_REQUEST_LATENCY.labels(method=method).observe(elapsed)
                GRPC_REQUEST_COUNT.labels(method=method, status="OK").inc()
                return response
            except Exception as e:
                elapsed = time.perf_counter() - start
                GRPC_REQUEST_LATENCY.labels(method=method).observe(elapsed)
                GRPC_REQUEST_COUNT.labels(method=method, status="ERROR").inc()
                raise

        return grpc.unary_unary_rpc_method_handler(
            instrumented,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )


def _row_to_employee(row) -> employees_pb2.Employee:
    return employees_pb2.Employee(
        id=row["id"],
        full_name=row["full_name"],
        position=row["position"],
        position_id=row["position_id"],
        department=row["department"],
        department_id=row["department_id"],
        email=row["email"],
        phone=row["phone"] or "",
        created_at=row["created_at"] or "",
        updated_at=row["updated_at"] or "",
    )


def _row_to_history(row) -> employees_pb2.HistoryRecord:
    return employees_pb2.HistoryRecord(
        id=row["id"],
        employee_id=row["employee_id"],
        changed_at=row["changed_at"] or "",
        change_type=row["change_type"] or "",
        field_name=row["field_name"] or "",
        old_value=row["old_value"] or "",
        new_value=row["new_value"] or "",
    )


def _row_to_department(row) -> employees_pb2.Department:
    return employees_pb2.Department(id=row["id"], name=row["name"])


def _row_to_position(row) -> employees_pb2.Position:
    return employees_pb2.Position(id=row["id"], name=row["name"])


class EmployeesServicer(employees_pb2_grpc.EmployeesServiceServicer):

    def ListEmployees(self, request, context):
        rows = database.get_all(
            search=request.search,
            sort=request.sort or "full_name",
            order=request.order or "asc",
            dept=request.dept,
        )
        return employees_pb2.ListEmployeesResponse(
            employees=[_row_to_employee(r) for r in rows]
        )

    def GetEmployee(self, request, context):
        row = database.get_by_id(request.id)
        if row is None:
            return employees_pb2.GetEmployeeResponse(found=False)
        return employees_pb2.GetEmployeeResponse(
            employee=_row_to_employee(row), found=True
        )

    def CreateEmployee(self, request, context):
        if not request.position_id or not request.department_id:
            return employees_pb2.OperationResponse(success=False, error="invalid_reference")
        try:
            database.create(
                request.full_name, request.position_id, request.department_id,
                request.email, request.phone,
            )
            return employees_pb2.OperationResponse(success=True)
        except psycopg2.IntegrityError:
            return employees_pb2.OperationResponse(success=False, error="duplicate_email")

    def UpdateEmployee(self, request, context):
        if not request.position_id or not request.department_id:
            return employees_pb2.OperationResponse(success=False, error="invalid_reference")
        try:
            database.update(
                request.id, request.full_name, request.position_id,
                request.department_id, request.email, request.phone,
            )
            return employees_pb2.OperationResponse(success=True)
        except psycopg2.IntegrityError:
            return employees_pb2.OperationResponse(success=False, error="duplicate_email")

    def DeleteEmployee(self, request, context):
        database.delete(request.id)
        return employees_pb2.OperationResponse(success=True)

    def GetHistory(self, request, context):
        rows = database.get_history(request.employee_id)
        return employees_pb2.GetHistoryResponse(
            records=[_row_to_history(r) for r in rows]
        )

    # --- Departments ---

    def ListDepartments(self, request, context):
        rows = database.get_all_departments()
        return employees_pb2.ListDepartmentsResponse(
            departments=[_row_to_department(r) for r in rows]
        )

    def GetDepartment(self, request, context):
        row = database.get_department_by_id(request.id)
        if row is None:
            return employees_pb2.GetDepartmentResponse(found=False)
        return employees_pb2.GetDepartmentResponse(
            department=_row_to_department(row), found=True
        )

    def CreateDepartment(self, request, context):
        try:
            database.create_department(request.name)
            return employees_pb2.OperationResponse(success=True)
        except psycopg2.IntegrityError:
            return employees_pb2.OperationResponse(success=False, error="duplicate_name")

    def UpdateDepartment(self, request, context):
        try:
            database.update_department(request.id, request.name)
            return employees_pb2.OperationResponse(success=True)
        except psycopg2.IntegrityError:
            return employees_pb2.OperationResponse(success=False, error="duplicate_name")

    def DeleteDepartment(self, request, context):
        try:
            database.delete_department(request.id)
            return employees_pb2.OperationResponse(success=True)
        except psycopg2.IntegrityError:
            return employees_pb2.OperationResponse(success=False, error="in_use")

    # --- Positions ---

    def ListPositions(self, request, context):
        rows = database.get_all_positions()
        return employees_pb2.ListPositionsResponse(
            positions=[_row_to_position(r) for r in rows]
        )

    def GetPosition(self, request, context):
        row = database.get_position_by_id(request.id)
        if row is None:
            return employees_pb2.GetPositionResponse(found=False)
        return employees_pb2.GetPositionResponse(
            position=_row_to_position(row), found=True
        )

    def CreatePosition(self, request, context):
        try:
            database.create_position(request.name)
            return employees_pb2.OperationResponse(success=True)
        except psycopg2.IntegrityError:
            return employees_pb2.OperationResponse(success=False, error="duplicate_name")

    def UpdatePosition(self, request, context):
        try:
            database.update_position(request.id, request.name)
            return employees_pb2.OperationResponse(success=True)
        except psycopg2.IntegrityError:
            return employees_pb2.OperationResponse(success=False, error="duplicate_name")

    def DeletePosition(self, request, context):
        try:
            database.delete_position(request.id)
            return employees_pb2.OperationResponse(success=True)
        except psycopg2.IntegrityError:
            return employees_pb2.OperationResponse(success=False, error="in_use")


def serve():
    database.init_db()
    start_http_server(9091)
    print("Prometheus metrics server started on port 9091")
    server = grpc.server(
        concurrent.futures.ThreadPoolExecutor(max_workers=10),
        interceptors=[MetricsInterceptor()],
    )
    employees_pb2_grpc.add_EmployeesServiceServicer_to_server(EmployeesServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("gRPC server started on port 50051")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
