import pytest
from app.models.period import Periodo

def test_create_period_admin(client, admin_token_headers, db_session):
    payload = {
        "semestre": "2024.1",
        "descricao": "Primeiro semestre de 2024",
        "dataInicio": "2024-01-01",
        "dataFim": "2024-06-30"
    }
    response = client.post("/periods/", json=payload, headers=admin_token_headers)
    assert response.status_code == 201
    assert response.json()["semestre"] == "2024.1"

def test_create_period_unauthorized(client):
    payload = {
        "semestre": "2024.1-NA",
        "descricao": "Unauthorized",
        "dataInicio": "2024-01-01",
        "dataFim": "2024-06-30"
    }
    response = client.post("/periods/", json=payload)
    assert response.status_code == 401

def test_list_periods(client, admin_token_headers):
    response = client.get("/periods/", headers=admin_token_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1

def test_list_periods_unauthorized(client):
    response = client.get("/periods/")
    assert response.status_code == 401

def test_update_period(client, admin_token_headers, db_session):
    # Model uses 'semestre'
    period = db_session.query(Periodo).filter(Periodo.semestre == "2024.1").first()
    payload = {"semestre": "2024.1-ALT"}
    response = client.put(f"/periods/{period.id}", json=payload, headers=admin_token_headers)
    assert response.status_code == 200
    assert response.json()["semestre"] == "2024.1-ALT"

def test_update_period_unauthorized(client, db_session):
    from datetime import date
    period = db_session.query(Periodo).first()
    if not period:
        period = Periodo(semestre="T-PER", data_inicio=date(2024, 1, 1), data_fim=date(2024, 6, 30))
        db_session.add(period)
        db_session.commit()
    response = client.put(f"/periods/{period.id}", json={"semestre": "HACKED"})
    assert response.status_code == 401

def test_update_non_existent_period(client, admin_token_headers):
    response = client.put("/periods/99999", json={"semestre": "Non-existent"}, headers=admin_token_headers)
    assert response.status_code == 404

def test_delete_period(client, admin_token_headers, db_session):
    period = db_session.query(Periodo).filter(Periodo.semestre == "2024.1-ALT").first()
    response = client.delete(f"/periods/{period.id}", headers=admin_token_headers)
    assert response.status_code == 204
    assert db_session.query(Periodo).filter(Periodo.id == period.id).first() is None

def test_delete_period_unauthorized(client, db_session):
    from datetime import date
    period = db_session.query(Periodo).first()
    if not period:
        period = Periodo(semestre="T-PER-D", data_inicio=date(2024, 1, 1), data_fim=date(2024, 6, 30))
        db_session.add(period)
        db_session.commit()
    response = client.delete(f"/periods/{period.id}")
    assert response.status_code == 401

def test_delete_non_existent_period(client, admin_token_headers):
    response = client.delete("/periods/99999", headers=admin_token_headers)
    assert response.status_code == 404
