from pydantic import BaseModel, Field, ConfigDict, computed_field, AliasChoices
from typing import Optional

class DisciplineBase(BaseModel):
    nomeDisciplina: str = Field(..., validation_alias=AliasChoices("nomeDisciplina", "nome"), serialization_alias="nomeDisciplina")
    matriculaDisciplina: Optional[str] = Field(None, validation_alias=AliasChoices("matriculaDisciplina", "codigo"), serialization_alias="matriculaDisciplina")

class DisciplineCreate(BaseModel):
    nomeDisciplina: str
    matriculaDisciplina: Optional[str] = None

class DisciplineUpdate(BaseModel):
    nomeDisciplina: Optional[str] = None
    matriculaDisciplina: Optional[str] = None

class DisciplineOut(DisciplineBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @computed_field
    @property
    def idDisciplina(self) -> int:
        return self.id
