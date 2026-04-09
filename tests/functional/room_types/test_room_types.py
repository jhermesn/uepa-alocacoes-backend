import pytest
from app.models.type_room import TipoSala

def test_create_room_type_admin(client, admin_token_headers, db_session):
    payload = {"nome": "Laboratório de Química"}
    response = client.post("/room-types/", json=payload, headers=admin_token_headers)
    assert response.status_code == 201
    assert response.json()["nome"] == "Laboratório de Química"

def test_create_room_type_unauthorized(client):
    payload = {"nome": "Unauthorized Type"}
    response = client.post("/room-types/", json=payload)
    assert response.status_code == 401

def test_create_room_type_invalid_payload(client, admin_token_headers):
    payload = {} 
    response = client.post("/room-types/", json=payload, headers=admin_token_headers)
    assert response.status_code == 422

def test_create_room_type_duplicate(client, admin_token_headers):
    payload = {"nome": "Laboratório de Química"}
    response = client.post("/room-types/", json=payload, headers=admin_token_headers)
    assert response.status_code == 409

def test_list_room_types(client, admin_token_headers):
    response = client.get("/room-types/", headers=admin_token_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1

def test_list_room_types_unauthorized(client):
    response = client.get("/room-types/")
    assert response.status_code == 401

def test_get_room_type(client, admin_token_headers, db_session):
    tipo = db_session.query(TipoSala).filter(TipoSala.nome == "Laboratório de Química").first()
    response = client.get(f"/room-types/{tipo.id}", headers=admin_token_headers)
    assert response.status_code == 200
    assert response.json()["nome"] == "Laboratório de Química"

def test_get_non_existent_room_type(client, admin_token_headers):
    response = client.get("/room-types/99999", headers=admin_token_headers)
    assert response.status_code == 404

def test_update_room_type(client, admin_token_headers, db_session):
    tipo = db_session.query(TipoSala).filter(TipoSala.nome == "Laboratório de Química").first()
    payload = {"nome": "Laboratório de Química Atualizado"}
    response = client.put(f"/room-types/{tipo.id}", json=payload, headers=admin_token_headers)
    assert response.status_code == 200
    assert response.json()["nome"] == "Laboratório de Química Atualizado"

def test_update_room_type_unauthorized(client, db_session):
    tipo = db_session.query(TipoSala).first()
    response = client.put(f"/room-types/{tipo.id}", json={"nome": "Hacked"})
    assert response.status_code == 401

def test_update_non_existent_room_type(client, admin_token_headers):
    response = client.put("/room-types/99999", json={"nome": "Non-existent"}, headers=admin_token_headers)
    assert response.status_code == 404

def test_delete_room_type(client, admin_token_headers, db_session):
    tipo = db_session.query(TipoSala).filter(TipoSala.nome == "Laboratório de Química Atualizado").first()
    response = client.delete(f"/room-types/{tipo.id}", headers=admin_token_headers)
    assert response.status_code == 204
    
    assert db_session.query(TipoSala).filter(TipoSala.id == tipo.id).first() is None

def test_delete_room_type_unauthorized(client, db_session):
    tipo = db_session.query(TipoSala).first()
    if not tipo:
        tipo = TipoSala(nome="Temp Delete")
        db_session.add(tipo)
        db_session.commit()
        db_session.refresh(tipo)
    response = client.delete(f"/room-types/{tipo.id}")
    assert response.status_code == 401

def test_delete_room_type_in_use(client, admin_token_headers, db_session):
    from app.models.room import Sala
    # Create type
    tipo = TipoSala(nome="In Use Type")
    db_session.add(tipo)
    db_session.commit()
    db_session.refresh(tipo)
    
    # Create room using it
    room = Sala(codigo_sala=999, fk_tipo_sala=tipo.id, descricao_sala="Test Room Usage")
    db_session.add(room)
    db_session.commit()
    
    response = client.delete(f"/room-types/{tipo.id}", headers=admin_token_headers)
    assert response.status_code == 409
    assert "sendo usado" in response.json()["detail"].lower()
