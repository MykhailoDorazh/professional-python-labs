"""API integration tests: HTTP request -> FastAPI -> service -> SQLite test DB."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from employee_api.api import create_app
from employee_api.database import init_db, make_engine, make_session_factory


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(f"sqlite:///{tmp_path / 'api.db'}")
    with TestClient(app) as test_client:  # `with` runs the lifespan (engine, tables)
        yield test_client


@pytest.fixture
def seeded(client: TestClient) -> TestClient:
    """IT (id 1): E0001 = 90 000, E0002 = 60 000; HR (id 2): empty."""
    client.post("/departments", json={"code": "IT", "name": "Інформаційні технології"})
    client.post("/departments", json={"code": "hr", "name": "Персонал"})
    client.post("/employees", json={"personnel_number": "E0001", "full_name": "Олена Коваль",
                                    "position": "Тімлід", "salary": "90000",
                                    "department_id": 1, "hire_date": "2021-03-01"})
    client.post("/employees", json={"personnel_number": "E0002", "full_name": "Іван Петренко",
                                    "position": "Розробник", "salary": "60000",
                                    "department_id": 1})
    return client


def test_root_and_health(client: TestClient) -> None:
    assert client.get("/").status_code == 200
    assert client.get("/health").json() == {"status": "ok", "version": "0.8.0"}


def test_create_department(client: TestClient) -> None:
    response = client.post("/departments", json={"code": "sales", "name": "  Продажі "})
    assert response.status_code == 201
    assert response.json() == {"id": 1, "code": "SALES", "name": "Продажі"}
    assert client.post("/departments", json={"code": "SALES", "name": "Ще раз"}).status_code == 409


@pytest.mark.parametrize("payload", [
    {"code": "I", "name": "Інше"},                 # code too short
    {"code": "IT-1", "name": "Інше"},              # not letters
    {"code": "IT", "name": "   "},                 # only spaces
    {"name": "Без коду"},                          # missing field
])
def test_create_department_validation(client: TestClient, payload: dict[str, str]) -> None:
    assert client.post("/departments", json=payload).status_code == 422


def test_post_and_get_employee(seeded: TestClient) -> None:
    response = seeded.get("/employees/1")
    assert response.status_code == 200
    assert response.json() == {"id": 1, "personnel_number": "E0001", "full_name": "Олена Коваль",
                               "position": "Тімлід", "department_id": 1,
                               "hire_date": "2021-03-01", "salary": "90000.00"}


@pytest.mark.parametrize(("changes", "status"), [
    ({"personnel_number": "E0001"}, 409),                     # duplicate number
    ({"department_id": 9}, 404),                              # unknown department
    ({"personnel_number": "E1"}, 422),                        # wrong number format
    ({"salary": "-1"}, 422),                                  # negative salary
    ({"salary": "1000000.01"}, 422),                          # above maximum
    ({"salary": "1.001"}, 422),                               # three decimals
    ({"full_name": "  "}, 422),                               # empty name
], ids=["duplicate", "unknown-department", "bad-number", "negative-salary", "above-max",
        "three-decimals", "empty-name"])
def test_create_employee_errors(seeded: TestClient, changes: dict[str, object],
                                status: int) -> None:
    payload = {"personnel_number": "E0009", "full_name": "Тарас Новак", "position": "Логіст",
               "salary": "30000", "department_id": 2} | changes
    assert seeded.post("/employees", json=payload).status_code == status


def test_salary_boundaries(seeded: TestClient) -> None:
    for number, salary in (("E0010", "0"), ("E0011", "1000000")):
        response = seeded.post("/employees", json={
            "personnel_number": number, "full_name": "Граничний", "position": "Тест",
            "salary": salary, "department_id": 2})
        assert response.status_code == 201


def test_unknown_employee_returns_structured_404(client: TestClient) -> None:
    response = client.get("/employees/404")
    assert response.status_code == 404
    assert response.json() == {"error": "EmployeeNotFoundError",
                               "detail": "Працівника id=404 не знайдено"}


def test_patch_employee(seeded: TestClient) -> None:
    response = seeded.patch("/employees/2", json={"position": "Старший розробник",
                                                  "salary": "65000.50"})
    assert response.status_code == 200
    body = response.json()
    assert (body["position"], body["salary"], body["full_name"]) == (
        "Старший розробник", "65000.50", "Іван Петренко")  # unsent fields are unchanged


def test_patch_transfers_to_other_department(seeded: TestClient) -> None:
    assert seeded.patch("/employees/2", json={"department_id": 2}).json()["department_id"] == 2
    assert [e["personnel_number"] for e in seeded.get("/departments/2/employees").json()] == [
        "E0002"]
    assert seeded.patch("/employees/2", json={"department_id": 99}).status_code == 404
    assert seeded.patch("/employees/99", json={"position": "X Y"}).status_code == 404
    assert seeded.patch("/employees/2", json={"salary": "-5"}).status_code == 422


def test_delete_employee(seeded: TestClient) -> None:
    assert seeded.delete("/employees/2").status_code == 204
    assert seeded.get("/employees/2").status_code == 404
    assert seeded.delete("/employees/2").status_code == 404


def test_list_employees_query_parameters(seeded: TestClient) -> None:
    def numbers(**params: object) -> list[str]:
        return [e["personnel_number"] for e in seeded.get("/employees", params=params).json()]

    assert numbers() == ["E0001", "E0002"]
    assert numbers(department_id=2) == []
    assert numbers(min_salary=70000) == ["E0001"]
    assert numbers(max_salary=70000) == ["E0002"]
    assert numbers(position="Розробник") == ["E0002"]
    assert numbers(search="петр") == ["E0002"]          # Cyrillic, case-insensitive
    assert numbers(sort_by_salary=True, limit=1) == ["E0001"]
    assert numbers(offset=1) == ["E0002"]
    assert seeded.get("/employees", params={"limit": 0}).status_code == 422


def test_department_employees_and_404(seeded: TestClient) -> None:
    assert len(seeded.get("/departments/1/employees").json()) == 2
    assert seeded.get("/departments/2/employees").json() == []
    assert seeded.get("/departments/9/employees").status_code == 404
    assert [d["code"] for d in seeded.get("/departments").json()] == ["IT", "HR"]
    assert seeded.get("/departments/1").json()["name"] == "Інформаційні технології"


def test_department_statistics(seeded: TestClient) -> None:
    assert seeded.get("/departments/1/statistics").json() == {
        "department_id": 1, "code": "IT", "name": "Інформаційні технології", "employees": 2,
        "payroll": "150000.00", "average_salary": "75000.00", "min_salary": "60000.00",
        "max_salary": "90000.00", "highest_paid": "E0001"}


def test_statistics_of_empty_department(seeded: TestClient) -> None:
    body = seeded.get("/departments/2/statistics").json()
    assert (body["employees"], body["payroll"], body["average_salary"], body["highest_paid"]) == (
        0, "0.00", "0.00", None)
    assert seeded.get("/departments/9/statistics").status_code == 404


def test_mass_raise_commit_and_rollback(seeded: TestClient) -> None:
    response = seeded.post("/departments/1/raise", json={"percent": "10"})
    assert response.json() == {"department_id": 1, "updated": 2, "payroll": "165000.00"}
    response = seeded.post("/departments/1/raise", json={"percent": "1000"})
    assert response.status_code == 422
    assert response.json()["error"] == "InvalidSalaryError"
    assert seeded.get("/departments/1/statistics").json()["payroll"] == "165000.00"  # rollback


def test_summary(seeded: TestClient) -> None:
    assert seeded.get("/stats").json() == {"departments": 2, "employees": 2,
                                           "payroll": "150000.00", "average_salary": "75000.00"}


def test_statistics_batch_concurrent(seeded: TestClient) -> None:
    response = seeded.post("/departments/statistics", json={"department_ids": [1, 2, 99]})
    assert response.status_code == 200
    body = response.json()
    assert (body["requested"], body["succeeded"]) == (3, 2)
    assert [item["ok"] for item in body["items"]] == [True, True, False]   # order kept
    assert body["items"][0]["statistics"]["payroll"] == "150000.00"
    assert "id=99" in body["items"][2]["error"]
    assert seeded.post("/departments/statistics", json={"department_ids": []}).status_code == 422


def test_openapi_schema_lists_endpoints(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/employees", "/employees/{employee_id}", "/departments/{department_id}/employees",
            "/departments/{department_id}/statistics", "/departments/statistics"} <= set(paths)
    assert set(paths["/employees/{employee_id}"]) == {"get", "patch", "delete"}


@pytest.mark.asyncio
async def test_api_through_httpx_async_client(tmp_path: Path) -> None:
    """The same app tested with httpx.AsyncClient + ASGITransport (no network)."""
    url = f"sqlite:///{tmp_path / 'async.db'}"
    app = create_app(url)
    engine = make_engine(url)
    init_db(engine)
    app.state.session_factory = make_session_factory(engine)  # lifespan is not run here
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        created = await ac.post("/departments", json={"code": "LOG", "name": "Логістика"})
        assert created.status_code == 201
        employee = await ac.post("/employees", json={
            "personnel_number": "E0007", "full_name": "Петро Ткачук", "position": "Логіст",
            "salary": "33000", "department_id": 1})
        assert employee.json()["salary"] == "33000.00"
        stats = await ac.get("/departments/1/statistics")
        assert stats.json()["employees"] == 1
    engine.dispose()
