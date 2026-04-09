"""Seed de dados iniciais (admin, salas, etc)

Revision ID: 8e9a7ae084c1
Revises: 
Create Date: 2025-11-17 21:35:14.835643

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from app.services.security import hash_password 
import os

# revision identifiers, used by Alembic.
revision: str = '8e9a7ae084c1'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    if os.getenv("ENV") != "development":
        print("Pulando seeding em ambiente não-dev.")
        return

    admin_hash = hash_password("password")
    user_hash = hash_password("123456")

    # Users
    op.execute(
        f"""
        INSERT INTO usuarios (nome, email, senha, tipo_usuario)
        VALUES 
        ('Admin Padrão', 'admin@admin.com', '{admin_hash}', 3),
        ('Professor Teste', 'prof@uepa.br', '{user_hash}', 2),
        ('Aluno Teste', 'aluno@uepa.br', '{user_hash}', 1)
        ON CONFLICT (email) DO UPDATE SET nome = EXCLUDED.nome;
        """
    ) 

    # Room Types
    room_types = ['Laboratório', 'Auditório', 'Aula', 'Sala de Estudos']
    for rt in room_types:
        op.execute(f"""
            INSERT INTO tipos_sala (nome) VALUES ('{rt}') ON CONFLICT (id) DO NOTHING;
        """)

    # Rooms
    # Laboratórios
    op.execute("""
        INSERT INTO salas (codigo_sala, fk_tipo_sala, descricao_sala, limite_usuarios)
        SELECT 101, id, 'Laboratório de Informática 1', 30 FROM tipos_sala WHERE nome='Laboratório'
        ON CONFLICT (codigo_sala) DO UPDATE SET descricao_sala = EXCLUDED.descricao_sala;
    """)
    op.execute("""
        INSERT INTO salas (codigo_sala, fk_tipo_sala, descricao_sala, limite_usuarios)
        SELECT 102, id, 'Laboratório de Física', 25 FROM tipos_sala WHERE nome='Laboratório'
        ON CONFLICT (codigo_sala) DO UPDATE SET descricao_sala = EXCLUDED.descricao_sala;
    """)

    # Aulas
    op.execute("""
        INSERT INTO salas (codigo_sala, fk_tipo_sala, descricao_sala, limite_usuarios)
        SELECT 201, id, 'Sala de Aula 201 - Bloco B', 40 FROM tipos_sala WHERE nome='Aula'
        ON CONFLICT (codigo_sala) DO UPDATE SET descricao_sala = EXCLUDED.descricao_sala;
    """)
    op.execute("""
        INSERT INTO salas (codigo_sala, fk_tipo_sala, descricao_sala, limite_usuarios)
        SELECT 202, id, 'Sala de Aula 202 - Bloco B', 40 FROM tipos_sala WHERE nome='Aula'
        ON CONFLICT (codigo_sala) DO UPDATE SET descricao_sala = EXCLUDED.descricao_sala;
    """)
    
    # Auditório
    op.execute("""
        INSERT INTO salas (codigo_sala, fk_tipo_sala, descricao_sala, limite_usuarios)
        SELECT 300, id, 'Auditório Principal', 100 FROM tipos_sala WHERE nome='Auditório'
        ON CONFLICT (codigo_sala) DO UPDATE SET descricao_sala = EXCLUDED.descricao_sala;
    """)

    # Sala de Estudos
    op.execute("""
        INSERT INTO salas (codigo_sala, fk_tipo_sala, descricao_sala, limite_usuarios)
        SELECT 401, id, 'Sala de Estudos 1', 10 FROM tipos_sala WHERE nome='Sala de Estudos'
        ON CONFLICT (codigo_sala) DO UPDATE SET descricao_sala = EXCLUDED.descricao_sala;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM salas WHERE codigo_sala IN (101, 102, 201, 202, 300, 401)")
    op.execute("DELETE FROM tipos_sala WHERE nome IN ('Sala de Estudos')") 
    op.execute("DELETE FROM usuarios WHERE email IN ('admin@admin.com', 'prof@uepa.br', 'aluno@uepa.br')")
    pass
