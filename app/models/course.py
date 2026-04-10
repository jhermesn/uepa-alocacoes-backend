"""
Modelo SQLAlchemy para a entidade Curso.
"""

from sqlalchemy import Column, Integer, String, TIMESTAMP
from sqlalchemy.sql import func
from app.try_database import Base

class Curso(Base):
    """
    Representa um curso acadêmico.
    """
    __tablename__ = "cursos"

    id = Column(Integer, primary_key=True, index=True)
    
    # Nome completo do curso (ex: Bacharelado em Engenharia de Software)
    nome = Column(String(150), nullable=False)
    
    # Sigla abreviada (ex: BES, MAT, ENG)
    sigla = Column(String(20))
    
    # Código Hexadecimal da cor para representação visual no frontend
    cor = Column(String(7)) 
    
    # Auditoria
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
