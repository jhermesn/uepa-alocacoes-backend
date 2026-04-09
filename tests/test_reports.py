import pytest
from app.services.security import create_access_token
from app.models.user import Usuario

def test_get_base_report_admin(client, admin_token_headers):
    response = client.get("/reports/base", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "professors" in data
    assert "disciplines" in data
    assert "courses" in data
    assert "rooms" in data

def test_get_users_report_admin(client, admin_token_headers):
    response = client.get("/reports/users", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_get_history_report_admin(client, admin_token_headers):
    response = client.get("/reports/history", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_reports_unauthorized(client):
    endpoints = ["/reports/base", "/reports/users", "/reports/history"]
    for ep in endpoints:
        response = client.get(ep)
        assert response.status_code == 401

def test_reports_forbidden_for_student(client, db_session):
    # Create student
    student = Usuario(
        email="student_rep@test.com",
        username="student_rep",
        senha="pwd",
        tipo_usuario=1,
        status="aprovado",
        nome="Rep Student"
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    
    token = create_access_token(subject=student.email, user_id=student.id, role=student.tipo_usuario)
    headers = {"Authorization": f"Bearer {token}"}
    
    endpoints = ["/reports/base", "/reports/users", "/reports/history"]
    for ep in endpoints:
        response = client.get(ep, headers=headers)
        assert response.status_code == 403

def test_reports_invalid_token(client):
    headers = {"Authorization": "Bearer invalid"}
    endpoints = ["/reports/base", "/reports/users", "/reports/history"]
    for ep in endpoints:
        response = client.get(ep, headers=headers)
        assert response.status_code == 401
