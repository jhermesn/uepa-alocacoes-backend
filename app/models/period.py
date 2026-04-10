"""
Modelo SQLAlchemy para a entidade Periodo (Período Acadêmico).
"""

from sqlalchemy import Column, Integer, String, Date, TIMESTAMP
from sqlalchemy.sql import func
from app.try_database import Base

class Periodo(Base):
    """
    Representa um período acadêmico ou semestre.
    """
    __tablename__ = "periodos"

    id = Column(Integer, primary_key=True, index=True)
    
    # Ex: 2025.1
    semestre = Column(String(20), nullable=False)
    
    # Texto descritivo
    descricao = Column(String(200))
    
    # Datas de início e fim do período
    data_inicio = Column(Date)
    data_fim = Column(Date)
    
    # Auditoria
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
