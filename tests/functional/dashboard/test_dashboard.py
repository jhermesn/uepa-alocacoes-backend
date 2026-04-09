import pytest
from app.services.security import create_access_token
from app.models.user import Usuario

def test_get_metrics_admin(client, admin_token_headers):
    response = client.get("/dashboard/metrics", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "status" in data
    assert "rooms" in data
    assert "types" in data

    response = client.get("/dashboard/metrics")
    assert response.status_code == 401

def test_get_metrics_invalid_token(client):
    response = client.get("/dashboard/metrics", headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401

def test_get_metrics_forbidden_for_student(client, db_session):
    # Create a student
    student = Usuario(
        email="student_dash@test.com",
        username="student_dash",
        senha="hashed_password",
        tipo_usuario=1, # aluno
        status="aprovado",
        nome="Student Test"
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    
    token = create_access_token(subject=student.email, user_id=student.id, role=student.tipo_usuario)
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/dashboard/metrics", headers=headers)
    assert response.status_code == 403
