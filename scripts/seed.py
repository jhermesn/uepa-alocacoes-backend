import os
import sys

# Adiciona o diretório raiz ao path para importar app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.try_database import SessionLocal
from app.models.user import Usuario
from app.models.type_room import TipoSala
from app.models.room import Sala
from app.services.security import hash_password

def seed_initial_data():
    db: Session = SessionLocal()
    try:
        # 1. Usuários
        admin_exists = db.query(Usuario).filter(Usuario.email == "admin@uepa.br").first()
        if not admin_exists:
            print("Criando usuário admin...")
            admin = Usuario(
                nome="Administrador Sistema",
                email="admin@uepa.br",
                username="admin",
                senha=hash_password("admin456"),
                tipo_usuario=3,
                status="aprovado"
            )
            db.add(admin)
            print("Admin 'admin@uepa.br' criado (Senha: admin456).")

        # 2. Tipos de Sala
        room_types = ['Laboratório', 'Auditório', 'Aula', 'Sala de Estudos']
        type_objs = {}
        for rt_name in room_types:
            rt = db.query(TipoSala).filter(TipoSala.nome == rt_name).first()
            if not rt:
                rt = TipoSala(nome=rt_name)
                db.add(rt)
                print(f"Tipo de sala '{rt_name}' criado.")
            type_objs[rt_name] = rt
        
        db.commit() # Commit para pegar os IDs dos tipos

        # 3. Salas
        salas_data = [
            (101, 'Laboratório', 'Laboratório de Informática 1', 30),
            (102, 'Laboratório', 'Laboratório de Física', 25),
            (201, 'Aula', 'Sala de Aula 201 - Bloco B', 40),
            (300, 'Auditório', 'Auditório Principal', 100),
        ]
        
        for codigo, t_name, desc, limite in salas_data:
            sala = db.query(Sala).filter(Sala.codigo_sala == codigo).first()
            if not sala:
                t_obj = db.query(TipoSala).filter(TipoSala.nome == t_name).first()
                sala = Sala(
                    codigo_sala=codigo,
                    fk_tipo_sala=t_obj.id,
                    descricao_sala=desc,
                    limite_usuarios=limite,
                    ativada=True
                )
                db.add(sala)
                print(f"Sala {codigo} ({desc}) criada.")

        db.commit()
        print("Seed finalizado com sucesso.")
            
    except Exception as e:
        print(f"Erro ao executar seed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_initial_data()
