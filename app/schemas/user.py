# app/schemas/user.py

from pydantic import BaseModel, EmailStr, ConfigDict, Field, computed_field, AliasChoices
from typing import Optional, Any, Union
from datetime import datetime

class UserLogin(BaseModel):
    username: str
    senha: str = Field(..., validation_alias="password")

    # Suporte para ambos no dump
    model_config = ConfigDict(populate_by_name=True)

class UserBase(BaseModel):
    nome: str
    email: EmailStr
    username: Optional[str] = None
    telefone: Optional[str] = None
    tipo_usuario: int = 1  # 1=aluno, 2=professor, 3=admin
    curso: Optional[str] = None
    cursoId: Optional[int] = Field(None, validation_alias=AliasChoices("cursoId", "fk_curso", "curso_id"), serialization_alias="cursoId")

class UserCreate(UserBase):
    senha: str
    matricula: Optional[str] = None
    siape: Optional[str] = None
    departamento: Optional[str] = None
    # Alias para frontend
    papel: Optional[str] = Field(None, validation_alias="papel")

class UserUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    telefone: Optional[str] = None
    tipo_usuario: Optional[int] = None
    senha: Optional[str] = None
    matricula: Optional[str] = None
    cursoId: Optional[int] = Field(None, alias="cursoId")
    siape: Optional[int] = None
    departamento: Optional[str] = None
    status: Optional[str] = None
    papel: Optional[str] = None

class UserOut(UserBase):
    id: int
    matricula: Optional[str] = None
    siape: Optional[str] = None
    departamento: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @computed_field
    @property
    def papel(self) -> str:
        roles = {1: "aluno", 2: "professor", 3: "admin"}
        return roles.get(self.tipo_usuario, "aluno")