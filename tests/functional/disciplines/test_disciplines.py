import pytest
from app.models.discipline import Disciplina

def test_create_discipline_admin(client, admin_token_headers, db_session):
    payload = {
        "nomeDisciplina": "Programação Orientada a Objetos",
        "matriculaDisciplina": "POO-001"
    }
    response = client.post("/disciplines/", json=payload, headers=admin_token_headers)
    assert response.status_code == 201
    assert response.json()["nomeDisciplina"] == "Programação Orientada a Objetos"

def test_create_discipline_unauthorized(client):
    payload = {
        "nomeDisciplina": "Unauthorized Discipline",
        "matriculaDisciplina": "UD-001"
    }
    response = client.post("/disciplines/", json=payload)
    assert response.status_code == 401

def test_create_discipline_missing_fields(client, admin_token_headers):
    payload = {"matriculaDisciplina": "POO-MISSING"} # missing nomeDisciplina
    response = client.post("/disciplines/", json=payload, headers=admin_token_headers)
    assert response.status_code == 422

def test_list_disciplines(client, admin_token_headers):
    response = client.get("/disciplines/", headers=admin_token_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1

def test_list_disciplines_unauthorized(client):
    response = client.get("/disciplines/")
    assert response.status_code == 401

def test_update_discipline(client, admin_token_headers, db_session):
    # Model uses 'codigo' for matriculaDisciplina
    disc = db_session.query(Disciplina).filter(Disciplina.codigo == "POO-001").first()
    payload = {"nomeDisciplina": "POO Avançado"}
    response = client.put(f"/disciplines/{disc.id}", json=payload, headers=admin_token_headers)
    assert response.status_code == 200
    assert response.json()["nomeDisciplina"] == "POO Avançado"

def test_update_discipline_unauthorized(client, db_session):
    disc = db_session.query(Disciplina).first()
    if not disc:
        disc = Disciplina(nome="Temp Disc", codigo="TMP-001")
        db_session.add(disc)
        db_session.commit()
    
    response = client.put(f"/disciplines/{disc.id}", json={"nomeDisciplina": "Hacked"})
    assert response.status_code == 401

def test_update_non_existent_discipline(client, admin_token_headers):
    response = client.put("/disciplines/99999", json={"nomeDisciplina": "Non-existent"}, headers=admin_token_headers)
    assert response.status_code == 404

def test_delete_discipline(client, admin_token_headers, db_session):
    disc = db_session.query(Disciplina).filter(Disciplina.codigo == "POO-001").first()
    response = client.delete(f"/disciplines/{disc.id}", headers=admin_token_headers)
    assert db_session.query(Disciplina).filter(Disciplina.id == disc.id).first() is None

def test_delete_discipline_unauthorized(client, db_session):
    disc = db_session.query(Disciplina).first()
    if not disc:
        disc = Disciplina(nome="Temp Delete Disc", codigo="TMPD-001")
        db_session.add(disc)
        db_session.commit()
        db_session.refresh(disc)

    response = client.delete(f"/disciplines/{disc.id}")
    assert response.status_code == 401

def test_delete_non_existent_discipline(client, admin_token_headers):
    response = client.delete("/disciplines/99999", headers=admin_token_headers)
    assert response.status_code == 404
