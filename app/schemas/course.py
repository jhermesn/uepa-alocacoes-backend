from pydantic import BaseModel, Field, ConfigDict, computed_field, AliasChoices
from typing import Optional
from datetime import datetime

class CourseBase(BaseModel):
    nomeCurso: str = Field(..., validation_alias=AliasChoices("nomeCurso", "nome"), serialization_alias="nomeCurso")
    siglaCurso: Optional[str] = Field(None, validation_alias=AliasChoices("siglaCurso", "sigla"), serialization_alias="siglaCurso")
    corCurso: Optional[str] = Field(None, validation_alias=AliasChoices("corCurso", "cor"), serialization_alias="corCurso")

class CourseCreate(BaseModel):
    nomeCurso: str
    siglaCurso: Optional[str] = None
    corCurso: Optional[str] = None

class CourseUpdate(BaseModel):
    nomeCurso: Optional[str] = None
    siglaCurso: Optional[str] = None
    corCurso: Optional[str] = None

class CourseOut(CourseBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @computed_field
    @property
    def idCurso(self) -> int:
        return self.id
