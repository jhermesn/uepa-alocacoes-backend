import pytest
from app.models.solicitation import Solicitacao

def test_create_solicitation_success(client, db_session):
    from app.models.room import Sala
    from app.models.type_room import TipoSala
    
    # Create room type
    tipo = TipoSala(nome="Laboratório")
    db_session.add(tipo)
    db_session.commit()
    
    # Create room
    room = Sala(codigo_sala=101, fk_tipo_sala=tipo.id, sala_ativada=True, limite_usuarios=30, descricao_sala="Test Room")
    db_session.add(room)
    db_session.commit()
    db_session.refresh(room)

    solic_data = {
        "solicitante": "Test solicitante",
        "email": "solicitante@test.com",
        "matricula": "123456",
        "papel": "professor",
        "motivo": "Aula extra",
        "descricao": "Aula de algoritmos",
        "diaSemana": "Segunda",
        "horarioInicio": "10:00:00",
        "horarioFim": "12:00:00",
        "salaId": room.id
    }
    
    response = client.post("/solicitations/", json=solic_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["salaId"] == room.id
    assert data["email"] == "solicitante@test.com"
    assert data["status"] == "pendente"

def test_create_solicitation_invalid_room(client):
    solic_data = {
        "solicitante": "Test",
        "email": "test@test.com",
        "matricula": "123",
        "papel": "aluno",
        "motivo": "m",
        "descricao": "d",
        "diaSemana": "Segunda",
        "horarioInicio": "10:00:00",
        "horarioFim": "11:00:00",
        "salaId": 99999 # Non-existent
    }
    response = client.post("/solicitations/", json=solic_data)
    assert response.status_code == 404

def test_create_solicitation_missing_fields(client):
    solic_data = {"solicitante": "Incomplete"}
    response = client.post("/solicitations/", json=solic_data)
    assert response.status_code == 422

def test_get_solicitations(client, db_session):
    response = client.get("/solicitations/")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

def test_list_my_solicitations(client):
    response = client.get("/solicitations/mine?email=solicitante@test.com")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_update_solicitation_status(client, db_session):
    solic = db_session.query(Solicitacao).first()
    payload = {"status": "aprovado"}
    response = client.patch(f"/solicitations/{solic.id}/status", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "aprovado"
