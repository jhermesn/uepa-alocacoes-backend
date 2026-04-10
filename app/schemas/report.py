"""
Conjunto de Schemas Pydantic para padronização dos Payloads de Relatório.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from .professor import ProfessorOut
from .discipline import DisciplineOut
from .course import CourseOut
from .room import RoomOut

class BaseDataReportOut(BaseModel):
    """
    Schema de resposta para a agregação de todos os cadastros base do sistema.
    Utilizado na exportação de planilhas de gestão inicial.
    """
    professors: List[ProfessorOut]
    disciplines: List[DisciplineOut]
    courses: List[CourseOut]
    rooms: List[RoomOut]

class UserReportOut(BaseModel):
    """
    Schema simplificado para o relatório de usuários, 
    seguindo a nomenclatura esperada pelo componente de exportação frontend.
    """
    Nome: str
    Email: str
    Papel: str
    Curso: Optional[str] = None
    Status: str

class HistoryReportOut(BaseModel):
    """
    Schema detalhado para o relatório de histórico de alocações.
    Contém dados formatados como strings para facilitar a renderização em PDF/Excel.
    """
    data: str = Field(..., validation_alias="Data", serialization_alias="data")
    periodo: str = Field(..., validation_alias="Horário", serialization_alias="periodo")
    professor: str = Field(..., validation_alias="Professor", serialization_alias="professor")
    disciplina: str = Field(..., validation_alias="Disciplina", serialization_alias="disciplina")
    curso: Optional[str] = Field(None, validation_alias="Curso", serialization_alias="curso")
    sala: str = Field(..., validation_alias="Sala", serialization_alias="sala")

    model_config = ConfigDict(populate_by_name=True)
