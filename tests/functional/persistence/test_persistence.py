import pytest
from app.models.type_room import TipoSala
from app.models.course import Curso
from app.models.room import Sala
from app.models.user import Usuario

def test_room_type_persistence(client, admin_token_headers, db_session):
    # 1. Ensure we have a room type
    room_type = db_session.query(TipoSala).first()
    if not room_type:
        room_type = TipoSala(nome="Laboratório de Teste")
        db_session.add(room_type)
        db_session.commit()
        db_session.refresh(room_type)
    
    # 2. Create room with that type ID
    payload = {
        "nomeSala": 2001,
        "tipoSalaId": room_type.id,
        "descricao_sala": "Saves Persistence Test",
        "capacidade": 50
    }
    response = client.post("/rooms/", json=payload, headers=admin_token_headers)
    assert response.status_code == 201
    data = response.json()
    
    # 3. VERIFY PERSISTENCE
    # Check JSON response
    assert data["tipoSalaId"] == room_type.id
    assert data["tipoSala"] == room_type.nome
    
    # Check Database
    db_room = db_session.query(Sala).filter(Sala.codigo_sala == 2001).first()
    assert db_room is not None
    assert db_room.fk_tipo_sala == room_type.id
    
    # 4. Update and Verify
    new_type = TipoSala(nome="Outro Tipo")
    db_session.add(new_type)
    db_session.commit()
    db_session.refresh(new_type)
    
    update_payload = {"tipoSalaId": new_type.id}
    update_response = client.put(f"/rooms/{db_room.id}", json=update_payload, headers=admin_token_headers)
    assert update_response.status_code == 200
    assert update_response.json()["tipoSalaId"] == new_type.id
    
    db_session.refresh(db_room)
    assert db_room.fk_tipo_sala == new_type.id

def test_course_persistence(client, admin_token_headers, db_session):
    # 1. Ensure we have a course
    course = db_session.query(Curso).first()
    if not course:
        course = Curso(nome="Engenharia de Software", sigla="BES", cor="#FF0000")
        db_session.add(course)
        db_session.commit()
        db_session.refresh(course)
    
    # 2. Create user with that course ID
    payload = {
        "nome": "User Persistence Test",
        "email": "persist@test.com",
        "username": "persist_user",
        "senha": "password123",
        "cursoId": course.id,
        "papel": "aluno"
    }
    response = client.post("/users/", json=payload, headers=admin_token_headers)
    assert response.status_code == 201
    data = response.json()
    
    # 3. VERIFY PERSISTENCE
    assert data["cursoId"] == course.id
    assert data["curso"] == course.nome
    
    # Check Database
    db_user = db_session.query(Usuario).filter(Usuario.email == "persist@test.com").first()
    assert db_user is not None
    assert db_user.fk_curso == course.id
    
    # 4. Update and Verify
    new_course = Curso(nome="Matemática", sigla="MAT", cor="#00FF00")
    db_session.add(new_course)
    db_session.commit()
    db_session.refresh(new_course)
    
    update_payload = {"cursoId": new_course.id}
    update_response = client.put(f"/users/{db_user.id}", json=update_payload, headers=admin_token_headers)
    assert update_response.status_code == 200
    assert update_response.json()["cursoId"] == new_course.id
    
    db_session.refresh(db_user)
    assert db_user.fk_curso == new_course.id
